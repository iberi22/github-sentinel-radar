# 🛡️ GitHub Sentinel & Radar

<div align="center">

[![English](https://img.shields.io/badge/Language-English-blue.svg)](README.md)
[![Español](https://img.shields.io/badge/Idioma-Espa%C3%B1ol-green.svg)](README_es.md)
[![中文](https://img.shields.io/badge/%E8%AF%AD%E8%A8%80-%E4%B8%AD%E6%96%87-red.svg)](README_zh.md)
[![हिन्दी](https://img.shields.io/badge/%E0%A4%AD%E0%A4%BE%E0%A4%B7%E0%A4%BE-%E0%A4%B9%E0%A4%BF%E0%A4%A8%E0%A5%8D%E0%A4%A6%E0%A5%80-orange.svg)](README_hi.md)
[![Français](https://img.shields.io/badge/Langue-Fran%C3%A7ais-yellow.svg)](README_fr.md)
[![العربية](https://img.shields.io/badge/%D8%A7%D9%84%D9%84%D8%BA%D8%A9-%D8%A7%D9%84%D8%B9%D8%B1%D8%A8%D9%8A%D8%A9-emerald.svg)](README_ar.md)
[![বাংলা](https://img.shields.io/badge/%E0%A6%AD%E0%A6%BE%E0%A6%B7%E0%A6%BE-%E0%A6%AC%E0%A6%BE%E0%A6%82%E0%A6%B2%E0%A6%BE-purple.svg)](README_bn.md)
[![Português](https://img.shields.io/badge/Idioma-Portugu%C3%AAs-teal.svg)](README_pt.md)
[![Русский](https://img.shields.io/badge/%D0%AF%D0%B7%D1%8B%D0%BA-%D0%A0%D1%83%D1%81%D1%81%D0%BA%D0%B8%D0%B9-cyan.svg)](README_ru.md)
[![اردو](https://img.shields.io/badge/%D8%B2%D8%A8%D8%A7%D9%86-%D8%A7%D8%B1%D8%AF%D9%88-pink.svg)](README_ur.md)

</div>

---


> **On-demand technical intelligence feed, anti-bot shield, and verified open-source developer network.**  
> Built with simple, decoupled layers forming a robust distributed system running on 100% free GitHub Actions and GitHub Pages.

---

## 🌟 Key Features

1. **🛡️ Anti-Bot Sentinel Shield**: Flags and blocks suspected mass-following accounts using account age and follower ratios. Heuristics can produce false positives; commit backdating is not analyzed.
2. **📡 On-Demand Tech Radar**: Analyzes your starred repositories, tracks latest tool releases, and discovers rising open-source projects tailored to your technical DNA.
3. **⚡ Zero API Abuse & Hibernation**: Heavy scraping runs strictly **on-demand** with a single click from the web UI. Automatically pauses if unused for more than 7 days.
4. **🌐 Borderless & Multilingual UI**: Modern, clean, borderless web interface with Light/Dark mode and native localization in the 10 most spoken languages.
5. **🤝 Web of Trust Directory**: Flat-file Git-backed database to showcase verified real developers and open-source projects.

---

## 🚀 Quick Setup (Fork & Run in 2 Minutes)

1. **Fork this repository** (or click **"Use this template"**).
2. Go to **Settings > Secrets and variables > Actions**.
3. Add a **Repository Secret** named `GH_BLOCKER_TOKEN` with your GitHub Personal Access Token (Permissions: user **Block another user: write**; browser token: repository **Actions: write**).
4. Enable **GitHub Pages** under **Settings > Pages** (Source: `GitHub Actions`).
5. Your custom dashboard will be live at `https://<your-username>.github.io/<repo-name>/`!

---

## 📂 Project Architecture

```text
├── .github/workflows/
│   ├── anti_bot.yml       # Periodic lightweight bot blocker (every 2h)
│   ├── radar.yml          # On-demand tech feed scanner
│   └── pages.yml          # Automated GitHub Pages deployer
├── data/
│   ├── blocklist.json     # Machine-readable bot blacklist
│   ├── radar.json         # Technical DNA, releases & discoveries
│   └── verified_projects.json # Community developer registry
├── docs/                  # Static borderless Web UI
│   ├── index.html         # Responsive, borderless web application
│   ├── app.js             # Reactive client & GitHub dispatch handler
│   └── locales/           # i18n JSON files for 10 world languages
├── src/
│   ├── blocker.py         # Bot detection engine
│   └── radar.py           # Technical intelligence & release scanner
├── PLANNING.md            # Vision, constraints & architectural roadmap
├── TASK.md                # Task tracking & milestones
└── config.json            # Customizable thresholds & hibernation settings
```

## 📜 License
MIT License © 2026 Sandra Lorena Santacruz & Community Contributors.

> Deployment / permisos / validation: [DEPLOYMENT.md](DEPLOYMENT.md) is the audited setup reference (2026-09-07).
