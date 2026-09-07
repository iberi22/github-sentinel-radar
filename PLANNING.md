# PLANNING.md – GitHub Sentinel & Radar

## 👁️ Visión General y Filosofía de Diseño
GitHub Sentinel & Radar es una plataforma distribuida, modular y ejecutada bajo demanda (*on-demand*) diseñada para proteger las cuentas de desarrolladores en GitHub contra bots de spam / *follow-farming* y proporcionar un feed de inteligencia técnica y radar de novedades personalizado.

### 🏛️ Principio Arquitectónico Rector
> **Desarrollo por capas simples, no complejas, para que formen sistemas robustos y estos sistemas formen redes mayores.**
> Cada componente debe ser autosuficiente, de bajo acoplamiento y con ejecución eficiente. La complejidad innecesaria multiplica los puntos de falla. Todo proceso pesado opera **bajo demanda** para evitar consumo abusivo de recursos.

---

## 🏗️ Arquitectura por Capas

1. **Capa 1: Centinela Defensivo (Seguridad & Anti-Bot)**
   - Monitoreo periódico ligero de nuevos seguidores (`GET /user/followers`).
   - Motor de análisis heurístico (antigüedad y ratio seguidos/seguidores; análisis temporal de follows y commits aún no implementado).
   - **Modo revisión por defecto (`anti_bot.review_mode=true`): nada se bloquea solo.** Los sospechosos van a `data/review_queue.json` para decisión humana en la web. Poner `review_mode=false` restaura el auto-bloqueo.
   - Doble almacenamiento: `data/blocklist.json` (máquinas/UI) y `BLOCKED_ACCOUNTS.md` (lectura humana).

1b. **Auditoría bajo demanda (Cola de Revisión)**
   - `src/audit.py` escanea seguidos + seguidores (`GET /user/following`, `GET /user/followers`, detalle por `GET /users/{login}`) y calcula % de confianza por usuario con motivos trazables (`src/review.py`).
   - Dos listas: confiables (≥ `review.trust_threshold`, defecto 60) y posibles bots. Cada fila: vínculo (seguidor/seguido/mutuo), % con barra, tooltip con motivos y stats, enlace al perfil.
   - Bloqueo sólo por decisión explícita con compuerta de PR: selección en la web → copiar lista → workflow `audit.yml` en modo `block` abre un PR con la lista marcada `approved` → el humano pulsa Merge → `block-on-merge.yml` ejecuta los PUT y registra en la cola, `blocklist.json` y `BLOCKED_ACCOUNTS.md`. Cerrar sin merge no bloquea a nadie. También vale el bloqueo nativo en el perfil de GitHub.

2. **Capa 2: Radar de Inteligencia Técnica (Feed Bajo Demanda)**
   - Extracción del ADN técnico del usuario analizando repositorios con estrella (`GET /users/{username}/starred`, sólo datos públicos).
   - Radar de lanzamientos: Detección de nuevos releases y notas de versión en bibliotecas seguidas.
   - Motor de descubrimiento: Búsqueda de proyectos emergentes en los mismos tópicos y lenguajes.
   - Activación **100% bajo demanda**: Disparado mediante enlace desde la web y confirmación con la sesión de GitHub, con modo hibernación automático tras inactividad.

3. **Capa 3: Directorio de Nodos y Red de Confianza (*Web of Trust*)**
   - Registro distribuido descentralizado sobre Git (`data/verified_projects.json` y `VERIFIED_PROJECTS.md`).
   - Permite a desarrolladores reales registrar sus perfiles y proyectos mediante Pull Requests validados.

4. **Capa 4: Interfaz de Usuario Borderless & Multilingüe (GitHub Pages)**
   - SPA estática ultra-liviana sin dependencias de compilación (`docs/index.html`).
   - Pestaña Cola de Revisión: tabla de confiables/sospechosos con % de confianza, tooltip de motivos, enlace al perfil, checkboxes, copiar lista y apertura del workflow de bloqueo. Cero llamadas a `api.github.com` desde el navegador (sólo enlaces).
   - Estilo moderno *borderless* (sin bordes duros, elevación suave por superficie, tipografía Geist/Inter).
   - Soporte nativo para modo claro y oscuro con persistencia.
   - Internacionalización (i18n) completa en los 10 idiomas más hablados del mundo.
   - Sin credenciales en el navegador. Guía de tres pasos, contexto público de despliegue y actualización del feed al volver de GitHub, acotada a cinco minutos y pausada en pestañas ocultas.

---

## 🛠️ Stack Tecnológico y Restricciones
- **Backend / Workers:** Python 3.11+ estándar (`requests`, `datetime`, `json`).
- **Orquestación:** GitHub Actions (100% gratuito en repositorios públicos, cron ligero del centinela y `workflow_dispatch` exclusivo del radar).
- **Frontend:** HTML5 semántico, Tailwind CSS (vía CDN), Vanilla JavaScript ES6+.
- **Almacenamiento:** Git Flat-File Database (`.json` + `.md`).
- **Internacionalización:** JSON Locales (EN, ZH, HI, ES, FR, AR, BN, PT, RU, UR).
