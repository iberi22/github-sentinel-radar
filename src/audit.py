#!/usr/bin/env python3
"""GitHub Sentinel - On-demand follower/following audit.

Scan mode (default) builds a per-user trust report over the accounts
you follow and the ones following you. Nothing is ever blocked here:
suspicious accounts land in data/review_queue.json so you decide.

Block mode (--block login1,login2) blocks an explicit list given by a
human (web UI selection or workflow input) and records the decision in
the queue, data/blocklist.json and BLOCKED_ACCOUNTS.md.

Needs GH_BLOCKER_TOKEN to be a user PAT with Followers read access
(fine-grained PAT: Account permissions -> Followers -> Read-only) plus
blocking permission for --block mode.
"""

import argparse
import json
import os
import sys

from common import load_config, github_request
from blocker import get_headers, update_blocklist_files
import review


def paginate(url, headers):
    items = []
    page = 1
    while True:
        try:
            resp = github_request("GET", url, headers=headers,
                                  params={"per_page": 100, "page": page})
        except Exception as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status == 403:
                print("[ERROR] GitHub devolvió 403 en " + url + ". "
                      "El PAT de GH_BLOCKER_TOKEN necesita permiso de lectura de "
                      "seguidores (fine-grained PAT: Account permissions -> "
                      "Followers -> Read-only). Edita el token y repite el scan.")
            raise
        batch = resp.json()
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items


def scan(token, cfg):
    headers = get_headers(token)
    followers = {f["login"].lower() for f in paginate("https://api.github.com/user/followers", headers)}
    following = {f["login"].lower() for f in paginate("https://api.github.com/user/following", headers)}

    ordered = sorted(followers) + sorted(following - followers)
    cap = cfg["review"]["max_users_to_scan"]
    if cap > 0:
        ordered = ordered[:cap]

    fresh, skipped = [], 0
    for login in ordered:
        if login in followers and login in following:
            direction = "mutual"
        elif login in followers:
            direction = "follower"
        else:
            direction = "following"
        u_resp = github_request("GET", f"https://api.github.com/users/{login}", headers=headers)
        if u_resp.status_code != 200:
            skipped += 1
            continue
        u_data = u_resp.json()
        trust, reasons, stats = review.score_user(u_data, direction, cfg)
        fresh.append({"login": u_data.get("login", login),
                      "profile_url": f"https://github.com/{u_data.get('login', login)}",
                      "direction": direction, "trust": trust,
                      "verdict": "trusted" if trust >= cfg["review"]["trust_threshold"] else "suspicious",
                      "status": "pending", "blocked_at": None,
                      "reasons": reasons, "stats": stats})

    stored = review.load_queue()["users"]
    payload = review.save_queue(review.merge_users(stored, fresh), cfg["review"]["trust_threshold"])
    totals = payload["totals"]
    print(f"[AUDIT] Escaneados: {totals['scanned']} "
          f"(confiables {totals['trusted']}, sospechosos {totals['suspicious']}, omitidos {skipped}). "
          f"Nada bloqueado: revisa la cola web para decidir.")


def block(token, cfg, targets):
    headers = get_headers(token)
    queue = review.load_queue()
    by_login = {u["login"].lower(): u for u in queue.get("users", [])}

    json_path = review.ROOT / "data" / "blocklist.json"
    current_bots = []
    if json_path.exists():
        with json_path.open(encoding="utf-8") as stream:
            current_bots = json.load(stream).get("bots", [])
    blocked_usernames = {b["username"].lower() for b in current_bots}

    failures, done = [], 0
    for login in targets:
        try:
            resp = github_request("PUT", f"https://api.github.com/user/blocks/{login}", headers=headers)
        except Exception as exc:  # noqa: BLE001 - one bad login must not abort the rest
            failures.append(f"{login} ({exc})")
            continue
        if resp.status_code not in (204, 201):
            failures.append(f"{login} (HTTP {resp.status_code})")
            continue
        entry = by_login.get(login)
        if entry is None:
            entry = {"login": login, "profile_url": f"https://github.com/{login}",
                     "direction": "unknown", "trust": 0, "verdict": "suspicious",
                     "reasons": [{"code": "manual", "detail": "", "tone": "bad"}],
                     "stats": {"followers": 0, "following": 0, "public_repos": 0, "age_days": None}}
            queue["users"].append(entry)
            by_login[login] = entry
        from datetime import datetime, timezone
        entry["status"] = "blocked"
        entry["blocked_at"] = datetime.now(timezone.utc).isoformat()
        if login not in blocked_usernames:
            blocked_usernames.add(login)
            current_bots.append({"username": login, "blocked_at": entry["blocked_at"],
                                 "reason": f"Decisión manual en revisión (confianza {entry.get('trust', 0)}%)"})
        done += 1
        print(f"[BLOCK] Bloqueado por decisión del usuario: {login}")

    update_blocklist_files(current_bots)
    review.save_queue(queue["users"], cfg["review"]["trust_threshold"])
    print(f"[COMPLETADO] Bloqueados: {done}. Fallos: {len(failures)}.")
    for failure in failures:
        print(f"[FALLO] {failure}")
    if failures:
        raise SystemExit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="On-demand follower audit (never auto-blocks).")
    parser.add_argument("--block", metavar="login1,login2",
                        help="Comma separated logins to block by explicit human decision.")
    args = parser.parse_args(argv)

    cfg = load_config()
    if not cfg["review"]["enabled"]:
        print("[AUDIT] Motor de revisión deshabilitado en config.json.")
        return
    token = os.environ.get("GH_BLOCKER_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("[ERROR] No se encontró GH_TOKEN en las variables de entorno.")
        raise SystemExit(1)

    if args.block is not None:
        try:
            targets = review.parse_targets(args.block)
        except ValueError as exc:
            print(f"[ERROR] {exc}")
            raise SystemExit(1)
        block(token, cfg, targets)
    else:
        scan(token, cfg)


if __name__ == "__main__":
    main(sys.argv[1:])
