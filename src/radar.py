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
from datetime import datetime, timezone, timedelta
from collections import Counter

from common import load_config, github_request

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

    # 2. Descubrir proyectos afines usando los top topics
    top_topics = [t for t, _ in topics_counter.most_common(3)]
    top_languages = [l for l, _ in languages_counter.most_common(2)]
    discoveries = []

    if top_topics and cfg["radar"]["max_discoveries"]:
        query_topic = top_topics[0]
        search_query = f"topic:{query_topic}+stars:>30"
        s_resp = github_request("GET", f"https://api.github.com/search/repositories?q={search_query}&sort=stars&order=desc&per_page={min(cfg['radar']['max_discoveries'], 100)}", headers=headers)
        if s_resp.status_code == 200:
            for item in s_resp.json().get("items", [])[:cfg["radar"]["max_discoveries"]]:
                if item.get("private", False):
                    continue
                discoveries.append({
                    "full_name": item["full_name"],
                    "html_url": item["html_url"],
                    "stars": item["stargazers_count"],
                    "description": item.get("description") or "Sin descripción.",
                    "language": item.get("language") or "General",
                    "topics": item.get("topics", [])
                })

    last_dispatched = datetime.now(timezone.utc).isoformat() if force_run else None
    if not force_run:
        with open(os.path.join(base_dir, "data", "radar.json"), encoding="utf-8") as stream:
            last_dispatched = json.load(stream).get("last_dispatched_at")

    radar_payload = {
        "profile_user": username or None,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "last_dispatched_at": last_dispatched,
        "profile_dna": {
            "top_languages": [l for l, _ in languages_counter.most_common(5)],
            "top_topics": [t for t, _ in topics_counter.most_common(5)]
        },
        "releases": releases,
        "discoveries": discoveries
    }

    update_radar_files(radar_payload)
    print(f"[ÉXITO] Radar actualizado: {len(releases)} releases y {len(discoveries)} proyectos descubiertos.")

if __name__ == "__main__":
    main()
