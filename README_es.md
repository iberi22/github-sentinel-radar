# 🛡️ GitHub Sentinel & Radar (Español)

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


> **Feed de inteligencia técnica bajo demanda, escudo anti-bots y red comunitaria de desarrolladores verificados.**
> Diseñado bajo una filosofía de capas simples y desacopladas que forman un sistema robusto, ejecutándose 100% gratis en GitHub Actions y GitHub Pages.

---

## 🌟 Características Principales

1. **🛡️ Escudo Centinela Anti-Bot**: Detecta y bloquea posibles cuentas de seguimiento masivo por antigüedad y proporción de seguidores. Las heurísticas pueden producir falsos positivos; no analiza fechas de commits.
2. **📡 Radar Técnico Bajo Demanda**: Examina tus repositorios favoritos (con estrella), detecta las últimas versiones/releases de tus herramientas y descubre proyectos emergentes alineados a tu stack.
3. **⚡ Cero Abuso de Recursos e Hibernación**: El rastreo pesado se ejecuta **bajo demanda** con un solo clic desde la web. Entra en reposo automáticamente si no se consulta en más de 7 días.
4. **🌐 Interfaz Borderless y Multilingüe**: Diseño limpio sin bordes duros (*borderless*), soporte para modo claro/oscuro e internacionalización en los 10 idiomas más hablados del mundo.
5. **🤝 Red de Confianza (*Web of Trust*)**: Base de datos descentralizada basada en Git (*Flat-File DB*) para conectar creadores de código abierto y proyectos legítimos.
6. **🔍 Cola de Revisión (decisión humana)**: Analiza a tus seguidores y seguidos en listas de confiables / posibles bots con % de confianza, motivos, tooltips y enlaces al perfil. Nada se bloquea solo: marca, copia y bloquea vía workflow de auditoría, o bloquea en GitHub. Los bloqueos solo se ejecutan al hacer Merge a un PR de solicitud auto-creado.

---

## 🚀 Puesta en Marcha Rápida (Fork en 2 Minutos)

1. Crea tu repositorio público con **Use this template**.
2. Habilita Actions si GitHub lo solicita. En Settings → Pages elige **GitHub Actions** y ejecuta **Deploy GitHub Pages** una vez.
3. Abre el dashboard, pulsa **Actualizar Feed ⚡**, confirma **Run workflow** en GitHub y vuelve. El feed se refresca automáticamente. **Sin token web ni secreto adicional para el radar.**
4. El bloqueo personal es opcional: consulta [configuración de Sentinel](DEPLOYMENT.md#sentinel).

---

## 📂 Arquitectura del Proyecto

```text
├── .github/workflows/     # Workflows automatizados de Actions
├── data/                  # Base de datos distribuida en JSON
├── docs/                  # Frontend estático desplegado en GitHub Pages
│   ├── locales/           # Archivos de traducción en 10 idiomas
├── src/
│   ├── blocker.py         # Motor de bloqueo y detección heurística (modo revisión)
│   ├── audit.py           # Auditoría de seguidores y bloqueo aprobado
│   ├── review.py          # Puntuación de confianza y cola
│   └── radar.py           # Motor de análisis técnico y lanzamientos
├── PLANNING.md            # Planificación y visión arquitectónica
├── TASK.md                # Control de tareas y fases
└── config.json            # Configuración de umbrales y tiempos
```

## 📜 Licencia
Licencia MIT © 2026 Sandra Lorena Santacruz y Colaboradores de la Comunidad.

> Deployment / permisos / validation: [DEPLOYMENT.md](DEPLOYMENT.md) is the audited setup reference (2026-09-07).
