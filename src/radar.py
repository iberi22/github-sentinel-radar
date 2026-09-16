#!/usr/bin/env python3
"""
GitHub Radar - On-Demand Technical Intelligence & News Feed
Scans user starred repositories, extracts technical DNA (topics, languages),
tracks recent releases, and discovers rising projects matching interests.
Features an automatic hibernation mechanism to avoid API quota waste when inactive.
"""

import os
import sys
import json
import re
import math
from datetime import datetime, timezone, timedelta
from collections import Counter

from common import load_config, github_request

DEFAULTS = {
    "discovery_min_stars": 20,
    "discovery_max_stars": 20000,
    "discovery_pushed_within_days": 365,
    "discovery_created_within_days": 1095,
    "discovery_topics": 3,
    "exclude_starred": True,
    "exclude_seen": True,
    "seen_history_cap": 500,
}

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "GitHub-Radar-Engine/1.0"
    }

def check_hibernation(cfg, base_dir, force=False):
    if force:
        return False
    state_path = os.path.join(base_dir, "data", "radar.json")
    if not os.path.exists(state_path):
        return True
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            last_active = data.get("last_dispatched_at")
            if not last_active:
                return True
            dt = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
            hibernation_days = cfg["radar"].get("hibernation_days", 7)
            if datetime.now(timezone.utc) - dt >= timedelta(days=hibernation_days):
                return True
    except (ValueError, TypeError, OSError):
        return True
    return False

def cfg_value(cfg, key):
    env_map = {
        "discovery_min_stars": "RADAR_MIN_STARS",
        "discovery_max_stars": "RADAR_MAX_STARS",
        "discovery_pushed_within_days": "RADAR_PUSHED_WITHIN_DAYS",
        "discovery_created_within_days": "RADAR_CREATED_WITHIN_DAYS",
        "discovery_topics": "RADAR_TOPICS",
        "seen_history_cap": "RADAR_SEEN_CAP",
    }
    if key in ("exclude_starred", "exclude_seen"):
        env_map[key] = "RADAR_EXCLUDE_STARRED" if key == "exclude_starred" else "RADAR_EXCLUDE_SEEN"
        raw = os.environ.get(env_map[key], "").strip().lower()
        if raw in ("1", "true", "yes"):
            return True
        if raw in ("0", "false", "no"):
            return False
        return cfg["radar"].get(key, DEFAULTS[key])
    if key in env_map:
        raw = os.environ.get(env_map[key], "").strip()
        if raw:
            try:
                return max(int(raw), 0)
            except ValueError:
                pass
    return cfg["radar"].get(key, DEFAULTS[key])


def parse_dt(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError, AttributeError):
        return None


def load_previous_state(base_dir):
    """Return (seen_map, previous_discovery_names). Never raises."""
    state_path = os.path.join(base_dir, "data", "radar.json")
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}, set()
    seen = data.get("seen_discoveries") or {}
    if not isinstance(seen, dict):
        seen = {}
    prev = {str(d.get("full_name", "")).lower() for d in data.get("discoveries", []) if isinstance(d, dict) and d.get("full_name")}
    return seen, prev


def novelty_reason(item, matched_topics, now):
    bits = []
    if matched_topics:
        bits.append(f"topic {matched_topics[0]} afín a tu stack")
    created = parse_dt(item.get("created_at"))
    pushed = parse_dt(item.get("pushed_at") or item.get("updated_at"))
    if created and (now - created) <= timedelta(days=365):
        bits.append(f"creado {created.date().isoformat()}")
    if pushed and (now - pushed) <= timedelta(days=90):
        bits.append(f"activo {pushed.date().isoformat()}")
    stars = item.get("stargazers_count", 0) or 0
    if stars < 2000:
        bits.append(f"emergente ★{stars}")
    return " · ".join(bits) if bits else "nuevo para ti"


def score_candidate(item, topic_set, lang_set, now):
    topics = [str(t).lower() for t in (item.get("topics") or [])]
    overlap = len(set(topics) & topic_set)
    lang_bonus = 2 if (item.get("language") or "") in lang_set else 0
    stars = item.get("stargazers_count", 0) or 0
    fame_penalty = math.log10(max(stars, 10)) / 2  # mega-famous sinks
    freshness = 0
    pushed = parse_dt(item.get("pushed_at") or item.get("updated_at"))
    created = parse_dt(item.get("created_at"))
    if pushed and (now - pushed) <= timedelta(days=180):
        freshness += 2
    if created and (now - created) <= timedelta(days=730):
        freshness += 2
    return overlap * 3 + lang_bonus + freshness - fame_penalty


def discover_novel_projects(headers, top_topics, top_languages, excluded, seen_names, cfg, username):
    now = datetime.now(timezone.utc)
    min_stars = cfg_value(cfg, "discovery_min_stars")
    max_stars = cfg_value(cfg, "discovery_max_stars")
    pushed_days = cfg_value(cfg, "discovery_pushed_within_days")
    created_days = cfg_value(cfg, "discovery_created_within_days")
    max_discoveries = cfg["radar"]["max_discoveries"]
    topic_set = {t.lower() for t in top_topics}
    lang_set = set(top_languages)
    pushed_cutoff = (now - timedelta(days=pushed_days)).date().isoformat() if pushed_days else None
    per_topic = min(max(max_discoveries * 3, 10), 100)

    pool = {}
    for topic in top_topics[:max(cfg_value(cfg, "discovery_topics"), 1)]:
        query = f"topic:{topic} stars:>{min_stars}"
        if pushed_cutoff:
            query += f" pushed:>{pushed_cutoff}"
        url = (f"https://api.github.com/search/repositories?q={query}"
               f"&sort=stars&order=desc&per_page={per_topic}")
        s_resp = github_request("GET", url, headers=headers)
        if s_resp.status_code != 200:
            continue
        for item in s_resp.json().get("items", []):
            name = str(item.get("full_name", ""))
            if not name or name.lower() in pool:
                continue
            pool[name.lower()] = item

    candidates = []
    for key, item in pool.items():
        if item.get("private", False):
            continue
        if key in excluded:
            continue
        if username and item.get("owner", {}).get("login", "").lower() == username.lower():
            continue
        if key in seen_names:
            continue
        stars = item.get("stargazers_count", 0) or 0
        if stars < min_stars or stars > max_stars:
            continue
        if pushed_days:
            pushed = parse_dt(item.get("pushed_at") or item.get("updated_at"))
            # Missing push date (incl. test doubles): don't punish, let score decide.
            if pushed and (now - pushed) > timedelta(days=pushed_days):
                continue
        if created_days:
            created = parse_dt(item.get("created_at"))
            if created and (now - created) > timedelta(days=created_days):
                continue
        topics = [str(t).lower() for t in (item.get("topics") or [])]
        matched = sorted(set(topics) & topic_set)
        # Items without topic metadata (older API payloads / test doubles)
        # still pass: the search query already matched the topic.
        candidates.append((score_candidate(item, topic_set, lang_set, now), item, matched))

    candidates.sort(key=lambda c: c[0], reverse=True)
    discoveries = []
    for _, item, matched in candidates[:max_discoveries]:
        discoveries.append({
            "full_name": item["full_name"],
            "html_url": item.get("html_url", f"https://github.com/{item['full_name']}"),
            "stars": item.get("stargazers_count", 0) or 0,
            "description": item.get("description") or "Sin descripción.",
            "language": item.get("language") or "General",
            "topics": item.get("topics", []),
            "matched_topics": matched,
            "novelty_reason": novelty_reason(item, matched, now),
            "first_seen": now.isoformat(),
            "pushed_at": item.get("pushed_at") or item.get("updated_at"),
            "created_at": item.get("created_at"),
        })
    return discoveries


def update_radar_files(radar_data):
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    json_path = os.path.join(base_dir, "data", "radar.json")
    md_path = os.path.join(base_dir, "RADAR.md")

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(radar_data, f, indent=2, ensure_ascii=False)

    md_lines = [
        "# 📡 GitHub Tech Radar & Developer Feed",
        f"_Última actualización: {radar_data['last_updated'][:19]} UTC_",
        "",
        "## 🚀 Últimos Lanzamientos y Releases (Tus Herramientas)",
        ""
    ]
    for r in radar_data.get("releases", []):
        md_lines.append(f"### [{r['repo']}]({r['html_url']}) - `{r['tag_name']}`")
        md_lines.append(f"**Publicado:** {r['published_at'][:10]}")
        md_lines.append(f"> {r['body_snippet']}")
        md_lines.append("")

    md_lines.append("## 💡 Proyectos Descubiertos Afines a tu Stack")
    md_lines.append("")
    for d in radar_data.get("discoveries", []):
        md_lines.append(f"- **[{d['full_name']}]({d['html_url']})** (★ {d['stars']}) - {d['description']}")
        md_lines.append(f"  *Lenguaje:* `{d['language']}` | *Topics:* {', '.join(d['topics'][:4])}")
        if d.get("novelty_reason"):
            md_lines.append(f"  *Por qué es nuevo:* {d['novelty_reason']}")
        md_lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

def main():
    force_run = "--force" in sys.argv
    cfg = load_config()
    if not cfg["radar"]["enabled"]:
        return
    username = os.environ.get("RADAR_USERNAME", "").strip()
    if username and not re.fullmatch(r"[A-Za-z0-9-]+", username):
        raise ValueError("RADAR_USERNAME must be a GitHub username")
    token = os.environ.get("GH_TOKEN") or os.environ.get("GH_BLOCKER_TOKEN")
    if not token:
        print("[ERROR] GH_TOKEN requerido.")
        raise SystemExit(1)

    base_dir = os.path.join(os.path.dirname(__file__), "..")

    if check_hibernation(cfg, base_dir, force=force_run):
        print("[HIBERNACIÓN] El Radar está en reposo por inactividad (> 7 días). Para activarlo, ejecuta un dispatch bajo demanda.")
        return

    headers = get_headers(token)

    # 1. Obtener starred repos
    starred_url = f"https://api.github.com/users/{username}/starred" if username else "https://api.github.com/user/starred"
    starred_repos = []
    limit = cfg["radar"]["max_starred_to_analyze"]
    page = 1
    while len(starred_repos) < limit:
        response = github_request("GET", starred_url, headers=headers,
                                  params={"per_page": min(limit, 100), "page": page})
        batch = response.json()
        starred_repos.extend(batch[:limit - len(starred_repos)])
        if len(batch) < min(limit, 100):
            break
        page += 1
    topics_counter = Counter()
    languages_counter = Counter()
    releases = []

    # A public dashboard must never publish private repository metadata.
    starred_repos = [repo for repo in starred_repos if not repo.get("private", False)]
    for index, repo in enumerate(starred_repos):
        lang = repo.get("language")
        if lang:
            languages_counter[lang] += 1
        for t in repo.get("topics", []):
            topics_counter[t] += 1

        # Consultar latest release de los primeros 10 repos
        if index < cfg["radar"]["max_releases_to_track"]:
            owner = repo["owner"]["login"]
            name = repo["name"]
            rel_resp = github_request("GET", f"https://api.github.com/repos/{owner}/{name}/releases/latest", headers=headers)
            if rel_resp.status_code == 200:
                rel = rel_resp.json()
                body = (rel.get("body") or "").strip()
                releases.append({
                    "repo": f"{owner}/{name}",
                    "tag_name": rel.get("tag_name", ""),
                    "published_at": rel.get("published_at", ""),
                    "html_url": rel.get("html_url", ""),
                    "body_snippet": body[:200] + "..." if len(body) > 200 else body
                })

    # 2. Descubrir proyectos NUEVOS (nunca tus stars, nunca ya mostrados,
    #    multi-topic, con frescura y sin mega-famosos que ya conoces).
    top_topics = [t for t, _ in topics_counter.most_common(cfg_value(cfg, "discovery_topics"))]
    top_languages = [l for l, _ in languages_counter.most_common(2)]
    discoveries = []
    excluded = set()

    if top_topics and cfg["radar"]["max_discoveries"]:
        excluded = set()
        if cfg_value(cfg, "exclude_starred"):
            for repo in starred_repos:
                full = repo.get("full_name")
                if not full and repo.get("owner") and repo.get("name"):
                    full = f"{repo['owner'].get('login', '')}/{repo['name']}"
                if full:
                    excluded.add(str(full).lower())
        seen_map, prev_names = load_previous_state(base_dir)
        seen_names = set(seen_map) if cfg_value(cfg, "exclude_seen") else set()
        seen_names |= prev_names if cfg_value(cfg, "exclude_seen") else set()
        discoveries = discover_novel_projects(
            headers, top_topics, top_languages, excluded, seen_names, cfg, username)

    last_dispatched = datetime.now(timezone.utc).isoformat() if force_run else None
    if not force_run:
        with open(os.path.join(base_dir, "data", "radar.json"), encoding="utf-8") as stream:
            last_dispatched = json.load(stream).get("last_dispatched_at")

    now_iso = datetime.now(timezone.utc).isoformat()
    seen_map, _ = load_previous_state(base_dir)
    for d in discoveries:
        seen_map.setdefault(str(d["full_name"]).lower(), d.get("first_seen", now_iso))
    cap = cfg_value(cfg, "seen_history_cap")
    if len(seen_map) > cap:
        seen_map = dict(list(seen_map.items())[-cap:])

    radar_payload = {
        "profile_user": username or None,
        "last_updated": now_iso,
        "last_dispatched_at": last_dispatched,
        "profile_dna": {
            "top_languages": [l for l, _ in languages_counter.most_common(5)],
            "top_topics": [t for t, _ in topics_counter.most_common(5)]
        },
        "releases": releases,
        "discoveries": discoveries,
        "seen_discoveries": seen_map,
        "discovery_filters": {
            "excluded_starred": len(excluded),
            "min_stars": cfg_value(cfg, "discovery_min_stars"),
            "max_stars": cfg_value(cfg, "discovery_max_stars"),
            "pushed_within_days": cfg_value(cfg, "discovery_pushed_within_days"),
            "created_within_days": cfg_value(cfg, "discovery_created_within_days"),
            "topics": cfg_value(cfg, "discovery_topics"),
        },
    }

    update_radar_files(radar_payload)
    print(f"[ÉXITO] Radar actualizado: {len(releases)} releases y {len(discoveries)} proyectos nuevos descubiertos.")

if __name__ == "__main__":
    main()
