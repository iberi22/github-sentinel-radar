#!/usr/bin/env python3
"""
GitHub Sentinel - Anti-Bot Blocker Module
Monitors new followers, evaluates heuristic spam rules, blocks confirmed bot accounts,
and updates both data/blocklist.json and BLOCKED_ACCOUNTS.md.
"""

import os
import json
import requests
from datetime import datetime, timezone

from common import load_config, github_request

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "GitHub-Sentinel-Bot/1.0"
    }

def fetch_upstream_blocklist(url):
    try:
        if not url:
            return set()
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            return {b["username"] for b in data.get("bots", [])}
    except Exception as e:
        print(f"[WARN] No se pudo descargar la lista upstream: {e}")
    return set()

def evaluate_bot_heuristics(user_data, cfg):
    following = user_data.get("following", 0)
    followers = user_data.get("followers", 0)
    created_at_str = user_data.get("created_at")
    
    if not created_at_str:
        return False, "Datos de cuenta incompletos"

    created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
    account_age_days = (datetime.now(timezone.utc) - created_at).days

    rules = cfg["anti_bot"]
    max_age = rules["max_account_age_days"]
    min_following = rules["min_following_for_suspicion"]
    max_followers = rules["max_followers_for_suspicion"]
    ratio_threshold = rules["following_to_followers_ratio"]

    # Heurística 1: Cuenta muy joven (< 10 días) con seguimiento masivo (> 400 seguidos) y pocos seguidores
    if account_age_days <= max_age and following >= min_following and followers <= max_followers:
        return True, f"Cuenta joven ({account_age_days}d) con follow masivo ({following} seguidos, {followers} seguidores)"

    # Heurística 2: Desbalance extremo (following / followers > 30 y más de 1000 seguidos)
    ratio = (following / max(followers, 1))
    if following > 1000 and ratio >= ratio_threshold:
        return True, f"Ratio de follow-farming extremo ({ratio:.1f}:1, {following} seguidos)"

    return False, "Perfil normal"

def update_blocklist_files(blocked_list):
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    json_path = os.path.join(base_dir, "data", "blocklist.json")
    md_path = os.path.join(base_dir, "BLOCKED_ACCOUNTS.md")

    # Guardar JSON
    output_data = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_blocked": len(blocked_list),
        "bots": blocked_list
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)

    # Guardar Markdown
    md_lines = [
        "# 🛡️ Cuentas Bloqueadas por GitHub Sentinel",
        f"_Última actualización: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}_",
        f"**Total de cuentas neutralizadas:** {len(blocked_list)}",
        "",
        "| Usuario | Perfil | Fecha Bloqueo | Motivo / Heurística |",
        "| :--- | :--- | :--- | :--- |"
    ]
    for b in blocked_list:
        md_lines.append(f"| `{b['username']}` | [{b['username']}](https://github.com/{b['username']}) | {b['blocked_at'][:10]} | {b['reason']} |")

    md_lines.append("")
    md_lines.append("> *Este archivo es generado automáticamente por el workflow de GitHub Actions.*")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

def main():
    cfg = load_config()
    if not cfg["anti_bot"]["enabled"]:
        return
    token = os.environ.get("GH_BLOCKER_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        print("[ERROR] No se encontró GH_TOKEN en las variables de entorno.")
        raise SystemExit(1)

    headers = get_headers(token)

    # Cargar lista actual
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    json_path = os.path.join(base_dir, "data", "blocklist.json")
    current_bots = []
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                current_bots = json.load(f).get("bots", [])
        except (ValueError, OSError) as exc:
            raise RuntimeError("Invalid blocklist; refusing to overwrite history") from exc

    blocked_usernames = {b["username"] for b in current_bots}

    # 1. Bloquear según lista comunitaria upstream
    upstream_bots = fetch_upstream_blocklist(cfg["anti_bot"].get("upstream_blocklist_url"))
    for bot_user in upstream_bots:
        if bot_user not in blocked_usernames:
            resp = github_request("PUT", f"https://api.github.com/user/blocks/{bot_user}", headers=headers)
            if resp.status_code in (204, 201):
                print(f"[COMUNIDAD] Bloqueado bot upstream: {bot_user}")
                blocked_usernames.add(bot_user)
                current_bots.append({
                    "username": bot_user,
                    "blocked_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "Lista de reputación comunitaria upstream"
                })

    # 2. Analizar seguidores recientes
    followers = []
    page = 1
    while True:
        resp = github_request("GET", "https://api.github.com/user/followers", headers=headers,
                              params={"per_page": 100, "page": page})
        batch = resp.json()
        followers.extend(batch)
        if len(batch) < 100:
            break
        page += 1

    new_blocks = 0
    for f in followers:
        username = f["login"]
        if username in blocked_usernames:
            continue

        u_resp = github_request("GET", f"https://api.github.com/users/{username}", headers=headers)
        if u_resp.status_code != 200:
            continue

        u_data = u_resp.json()
        is_bot, reason = evaluate_bot_heuristics(u_data, cfg)
        if is_bot:
            b_resp = github_request("PUT", f"https://api.github.com/user/blocks/{username}", headers=headers)
            if b_resp.status_code in (204, 201):
                print(f"[AUTODETECT] Bot bloqueado con éxito: {username} - {reason}")
                blocked_usernames.add(username)
                current_bots.append({
                    "username": username,
                    "blocked_at": datetime.now(timezone.utc).isoformat(),
                    "reason": reason
                })
                new_blocks += 1

    print(f"[COMPLETADO] Proceso finalizado. Nuevos bots bloqueados: {new_blocks}. Total: {len(current_bots)}")
    update_blocklist_files(current_bots)

if __name__ == "__main__":
    main()
