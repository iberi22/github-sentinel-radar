"""Review queue: per-user trust scoring and queue persistence.

Shared by the on-demand audit engine (src/audit.py) and the
review-mode branch of the blocker (src/blocker.py).

A queue entry looks like:
    {"login": "octocat", "profile_url": "https://github.com/octocat",
     "direction": "follower|following|mutual",
     "trust": 0-100, "verdict": "trusted|suspicious",
     "status": "pending|blocked", "blocked_at": iso|None,
     "reasons": [{"code": str, "detail": str, "tone": "good|bad"}],
     "stats": {"followers": int, "following": int,
               "public_repos": int, "age_days": int|None}}
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUE_JSON = ROOT / "data" / "review_queue.json"
QUEUE_MD = ROOT / "REVIEW_QUEUE.md"

USERNAME_RE = re.compile(r"^(?!.*--)[A-Za-z0-9]([A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
MAX_TARGETS = 100


def account_age_days(created_at):
    if not created_at:
        return None
    try:
        created = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (datetime.now(timezone.utc) - created).days


def score_user(user, direction, cfg):
    """Return (trust 0-100, reasons, stats).

    Reasons carry a stable code plus a short factual detail so the
    web UI can render them in any locale. Positive signals are
    included too, so the tooltip explains both sides.
    """
    anti = cfg["anti_bot"]
    threshold = cfg["review"]["trust_threshold"]
    following = user.get("following") or 0
    followers = user.get("followers") or 0
    repos = user.get("public_repos") or 0
    age = account_age_days(user.get("created_at"))

    trust = 55
    reasons = []

    def add(code, detail, tone, delta):
        nonlocal trust
        trust += delta
        reasons.append({"code": code, "detail": str(detail), "tone": tone})

    if age is None:
        add("unknown_age", "", "bad", -10)
    elif (age <= anti["max_account_age_days"]
            and following >= anti["min_following_for_suspicion"]
            and followers <= anti["max_followers_for_suspicion"]):
        add("young_mass_follow", f"{age}d - {following}/{followers}", "bad", -45)
    elif age <= 30:
        add("new_account", f"{age}d", "bad", -15)
    elif age <= 90:
        add("new_account", f"{age}d", "bad", -8)
    if age is not None and age >= 365:
        add("veteran", f"{age // 365}y", "good", 15)

    ratio = following / max(followers, 1)
    if following > 1000 and ratio >= anti["following_to_followers_ratio"]:
        add("extreme_ratio", f"{ratio:.0f}:1", "bad", -40)
    elif (following >= anti["min_following_for_suspicion"]
            and followers <= anti["max_followers_for_suspicion"]):
        add("mass_follow", f"{following}/{followers}", "bad", -20)
    if followers == 0 and following >= 100:
        add("lonely_hunter", f"{following}", "bad", -15)
    if repos == 0:
        add("empty_profile", "", "bad", -10)

    if direction == "mutual":
        add("mutual", "", "good", 25)
    if followers >= 100:
        add("established", f"{followers}", "good", 10)
    if repos >= 10:
        add("active_creator", f"{repos}", "good", 5)

    trust = max(0, min(100, trust))
    verdict = "trusted" if trust >= threshold else "suspicious"
    stats = {"followers": followers, "following": following,
             "public_repos": repos, "age_days": age}
    return trust, reasons, stats


def empty_queue():
    return {"last_updated": None,
            "totals": {"scanned": 0, "trusted": 0, "suspicious": 0, "blocked": 0},
            "threshold": None, "users": []}


def load_queue():
    if not QUEUE_JSON.exists():
        return empty_queue()
    try:
        with QUEUE_JSON.open(encoding="utf-8") as stream:
            data = json.load(stream)
        if not isinstance(data.get("users"), list):
            raise ValueError("users must be a list")
        return data
    except (ValueError, OSError) as exc:
        raise RuntimeError("Invalid review queue; refusing to overwrite history") from exc


def merge_users(existing, fresh):
    """Merge fresh scan entries over stored ones.

    A user already marked blocked keeps that status (and its date);
    everything else is refreshed with the latest stats.
    """
    stored = {u["login"].lower(): u for u in existing}
    merged = []
    for entry in fresh:
        previous = stored.get(entry["login"].lower())
        if previous and previous.get("status") == "blocked":
            entry["status"] = "blocked"
            entry["blocked_at"] = previous.get("blocked_at")
        merged.append(entry)
    return merged


def save_queue(users, threshold):
    trusted = sum(1 for u in users if u["verdict"] == "trusted")
    suspicious = sum(1 for u in users if u["verdict"] == "suspicious")
    blocked = sum(1 for u in users if u.get("status") == "blocked")
    payload = {"last_updated": datetime.now(timezone.utc).isoformat(),
               "totals": {"scanned": len(users), "trusted": trusted,
                          "suspicious": suspicious, "blocked": blocked},
               "threshold": threshold, "users": users}
    with QUEUE_JSON.open("w", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, ensure_ascii=False)
    write_markdown(payload)
    return payload


def _reason_text(reason):
    code = reason.get("code", "?")
    detail = reason.get("detail", "")
    mark = "+" if reason.get("tone") == "good" else "-"
    return f"{mark}{code} {detail}".strip()


def write_markdown(payload):
    lines = ["# 🔍 Cola de Revisión — Sentinel",
             f"_Última actualización: {payload['last_updated']}_",
             f"**Escaneados:** {payload['totals']['scanned']} · "
             f"**Confiables:** {payload['totals']['trusted']} · "
             f"**Sospechosos:** {payload['totals']['suspicious']} · "
             f"**Bloqueados:** {payload['totals']['blocked']} · "
             f"**Umbral:** {payload['threshold']}%",
             ""]
    for title, verdict in (("🚨 Posibles bots", "suspicious"),
                           ("✅ Confiables", "trusted")):
        lines.append(f"## {title}")
        lines.append("")
        lines.append("| Usuario | Perfil | Vínculo | Confianza | Motivos | Estado |")
        lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
        rows = [u for u in payload["users"] if u["verdict"] == verdict]
        if not rows:
            lines.append("| _—_ | _—_ | _—_ | _—_ | Sin registros todavía | _—_ |")
        for user in sorted(rows, key=lambda u: u["trust"]):
            why = "; ".join(_reason_text(r) for r in user.get("reasons", [])) or "—"
            lines.append(f"| `{user['login']}` | [{user['login']}]({user['profile_url']}) "
                         f"| {user['direction']} | {user['trust']}% | {why} "
                         f"| {user.get('status', 'pending')} |")
        lines.append("")
    lines.append("> *Este archivo es generado automáticamente por el workflow de revisión.*")
    with QUEUE_MD.open("w", encoding="utf-8") as stream:
        stream.write("\n".join(lines) + "\n")


def parse_targets(raw):
    """Parse a comma/space/newline separated login list for --block.

    Raises ValueError listing every invalid login. GitHub usernames
    allow alphanumerics and single hyphens, max 39 chars.
    """
    if not raw or not raw.strip():
        raise ValueError("targets must not be empty in block mode")
    seen = []
    for chunk in re.split(r"[\s,;]+", raw.strip()):
        if not chunk or chunk.lower() in seen:
            continue
        if not USERNAME_RE.match(chunk):
            raise ValueError(f"invalid GitHub login: {chunk!r}")
        seen.append(chunk.lower())
    if not seen:
        raise ValueError("targets must not be empty in block mode")
    if len(seen) > MAX_TARGETS:
        raise ValueError(f"at most {MAX_TARGETS} logins per block run")
    return seen
