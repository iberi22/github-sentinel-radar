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
   - Bloqueo preventivo automático (`PUT /user/blocks/{username}`).
   - Doble almacenamiento: `data/blocklist.json` (máquinas/UI) y `BLOCKED_ACCOUNTS.md` (lectura humana).

2. **Capa 2: Radar de Inteligencia Técnica (Feed Bajo Demanda)**
   - Extracción del ADN técnico del usuario analizando repositorios con estrella (`GET /user/starred`).
   - Radar de lanzamientos: Detección de nuevos releases y notas de versión en bibliotecas seguidas.
   - Motor de descubrimiento: Búsqueda de proyectos emergentes en los mismos tópicos y lenguajes.
   - Activación **100% bajo demanda**: Disparado desde la web mediante token local en el navegador o workflow manual, con modo hibernación automático tras inactividad.

3. **Capa 3: Directorio de Nodos y Red de Confianza (*Web of Trust*)**
   - Registro distribuido descentralizado sobre Git (`data/verified_projects.json` y `VERIFIED_PROJECTS.md`).
   - Permite a desarrolladores reales registrar sus perfiles y proyectos mediante Pull Requests validados.

4. **Capa 4: Interfaz de Usuario Borderless & Multilingüe (GitHub Pages)**
   - SPA estática ultra-liviana sin dependencias de compilación (`docs/index.html`).
   - Estilo moderno *borderless* (sin bordes duros, elevación suave por superficie, tipografía Geist/Inter).
   - Soporte nativo para modo claro y oscuro con persistencia.
   - Internacionalización (i18n) completa en los 10 idiomas más hablados del mundo.
   - Persistencia opcional del token de disparo en `localStorage`, accesible a scripts del mismo origen. Token limitado a Actions: write; campos vacíos eliminan credenciales guardadas.

---

## 🛠️ Stack Tecnológico y Restricciones
- **Backend / Workers:** Python 3.11+ estándar (`requests`, `datetime`, `json`).
- **Orquestación:** GitHub Actions (100% gratuito en repositorios públicos, cron ligero del centinela y `workflow_dispatch` exclusivo del radar).
- **Frontend:** HTML5 semántico, Tailwind CSS (vía CDN), Vanilla JavaScript ES6+.
- **Almacenamiento:** Git Flat-File Database (`.json` + `.md`).
- **Internacionalización:** JSON Locales (EN, ZH, HI, ES, FR, AR, BN, PT, RU, UR).
