# 🛡️ GitHub 哨兵与雷达 (GitHub Sentinel & Radar)

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


> **按需技术情报动态、反机器人防护盾与经过验证的开源开发者信任网络。**
> 采用简单解耦的分层设计，构建在 100% 免费的 GitHub Actions 与 GitHub Pages 之上。

---

## 🌟 核心功能

1. **🛡️ 反垃圾机器人防御盾**：利用精准启发式规则自动拦截刷粉机器人、伪造提交日期和虚假账户。
2. **📡 按需技术雷达**：深度分析您加星标的开源项目，追踪核心工具最新版本，发现匹配您技术栈的高潜项目。
3. **⚡ 零配额滥用与休眠机制**：重度抓取仅在点击网页按钮时**按需运行**。连续 7 天未激活将自动休眠。
4. **🌐 无边框多语言极简界面**：现代无边框（Borderless）卡片式设计，支持明暗主题切换，内置全球使用人口排名前十的语言本地化。
5. **🤝 开发者信任网络**：基于 Git 平面文件的去中心化数据库，展示真实开发者与优秀项目。

---

## 🚀 两分钟极速上手

1. **Fork 本仓库**（或点击 **"Use this template"**）。
2. 进入仓库设置 **Settings > Secrets and variables > Actions**。
3. 添加名为 `GH_BLOCKER_TOKEN` 的密钥（具有 用户 **Block another user: write**；浏览器令牌：仓库 **Actions: write** 权限）。
4. 在 **Settings > Pages** 中将部署源选为 **GitHub Actions**。
5. 您的专属面板即可通过 `https://<您的用户名>.github.io/<仓库名>/` 访问！

## 📜 许可证
MIT License © 2026 Sandra Lorena Santacruz 与社区贡献者。

> Deployment / permisos / validation: [DEPLOYMENT.md](DEPLOYMENT.md) is the audited setup reference (2026-09-07).
