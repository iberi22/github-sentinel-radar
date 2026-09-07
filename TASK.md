# TASK.md
Gestión de Tareas: GitHub Sentinel & Radar
_Última actualización: 2026-09-06_

## 🎯 Resumen Ejecutivo y Estado Actual
**Estado General:** Código publicado y GitHub Pages desplegado y verificado. Activación de motores pendiente de GH_BLOCKER_TOKEN. Las afirmaciones originales de 100% no estaban respaldadas por pruebas incluidas.

---

## 🚀 Fase Actual: Distribución y Despliegue de la Plantilla
**Objetivo:** Publicar la suite completa con soporte multi-idioma nativo y arquitectura bajo demanda para adopción comunitaria.

| ID    | Tarea                                                  | Prioridad | Estado        | Responsable |
|-------|--------------------------------------------------------|-----------|---------------|-------------|
| F1-01 | Diseñar arquitectura y capas simples en PLANNING.md    | ALTA      | ✅ Completado | Cascade     |
| F1-02 | Implementar motor de detección y bloqueo (blocker.py)  | ALTA      | ✅ Completado | Cascade     |
| F1-03 | Implementar radar técnico bajo demanda (radar.py)      | ALTA      | ✅ Completado | Cascade     |
| F1-04 | Crear workflows de GitHub Actions (anti_bot/radar/page)| ALTA      | ✅ Completado | Cascade     |
| F1-05 | Desarrollar UI estática borderless con Dark/Light mode | ALTA      | ✅ Completado | Cascade     |
| F1-06 | Configurar diccionarios i18n para los 10 idiomas       | ALTA      | ✅ Completado | Cascade     |
| F1-07 | Redactar README completo en los 10 idiomas del mundo   | ALTA      | ✅ Completado | Cascade     |
| F1-08 | Empaquetar y sincronizar proyecto en Google Drive      | ALTA      | ✅ Completado | Cascade     |

**Leyenda de Estado:**
- `⬜ Pendiente`
- `⚙️ En Progreso`
- `✅ Completado`
- `❌ Bloqueado`

---

## ✅ Hitos Principales Completados
- Hito 1: Creación del núcleo heurístico contra granjas de bots y manipulación de commits.
- Hito 2: Implementación de la ejecución bajo demanda (*on-demand*) para evitar consumo abusivo de recursos.
- Hito 3: Creación de la interfaz sin bordes (*borderless*) con integración de token en `localStorage`.
- Hito 4: Soporte nativo de internacionalización en 10 idiomas para interfaz y documentación.

---

## 👾 Deuda Técnica y Mejoras Pendientes
| ID    | Tarea                                                  | Prioridad | Estado        | Responsable |
|-------|--------------------------------------------------------|-----------|---------------|-------------|
| TD-01 | Soporte para Webhooks en organizaciones de GitHub       | MEDIA     | ⬜ Pendiente | Comunidad   |
| TD-02 | Filtro adicional de análisis semántico con LLM local   | BAJA      | ⬜ Pendiente | Comunidad   |

---

## 📝 Tareas Descubiertas Durante el Desarrollo
| ID    | Tarea                                                  | Prioridad | Estado        | Responsable |
|-------|--------------------------------------------------------|-----------|---------------|-------------|
| AD-01 | Incorporar botón de disparo directo con `localStorage`  | ALTA      | ✅ Completado | Cascade     |
| AD-02 | Modo de hibernación por inactividad tras 7 días        | ALTA      | ✅ Completado | Cascade     |

## Plan de deuda técnica (antes de modificar código)

### TD-01 — pendiente, ampliación opcional

1. Definir eventos de organización y permisos mínimos de una GitHub App; separar bloqueo personal y organizacional.
2. Diseñar receptor opcional con validación HMAC SHA-256, deduplicación y rechazo de replays.
3. Encolar únicamente eventos relevantes y ejecutar workers bajo demanda con apagado tras inactividad.
4. Probar firmas inválidas, duplicados, rate limits y aislamiento entre organizaciones antes del despliegue.

### TD-02 — pendiente, ampliación opcional

1. Definir contrato opcional de clasificación semántica; heurísticas actuales como fallback.
2. Conectar a un LLM local existente mediante adaptador con timeout y límites de entrada; sin descargas automáticas.
3. Activar sólo bajo demanda, limitar concurrencia y liberar recursos tras inactividad; nunca bloquear cuentas sólo por salida del LLM.
4. Evaluar falsos positivos con fixtures, probar indisponibilidad y medir consumo antes de habilitar.

## Auditoría AD-03

1. Respetar flags/límites de configuración, errores HTTP y hibernación sin renovar actividad automática.
2. Validar los 10 idiomas, RTL, temas, token local y renderizado de contenido externo.
3. Limitar permisos, quitar fallback de token personal y enlazar generación de datos con Pages.
4. Ejecutar pruebas offline, inicializar Git y preparar origin; documentar requisitos del despliegue remoto.

## Resultado de auditoría local — 2026-09-07 UTC

- AD-03 completado: 11 pruebas Python y regresión real en Chromium (10 idiomas/RTL, tema, dispatch simulado, token, XSS).
- Workflows YAML parseados y permisos/triggers revisados con documentación oficial de GitHub. Pages finalizó correctamente (run 34078083746); regresión Chromium pasada sobre la URL pública.
- Dependencias instaladas y compatibles en Python 3.12.12; Python 3.11 se validará en Actions al activar los motores.
- Datos de ejemplo no verificados retirados de la plantilla pública; ZIP original conservado.
- TD-01 y TD-02 permanecen pendientes con plan, sin procesos adicionales residentes.

## Publicación — 2026-09-07 UTC

- Repositorio: https://github.com/iberi22/github-sentinel-radar
- Web: https://iberi22.github.io/github-sentinel-radar/
- Despliegue verificado: https://github.com/iberi22/github-sentinel-radar/actions/runs/34078083746
- Pendiente operativo: configurar GH_BLOCKER_TOKEN (Block another user: write y Starring: read). La web requiere un PAT independiente con Actions: write para el disparo manual. No se ejecutaron motores con credenciales reales.
