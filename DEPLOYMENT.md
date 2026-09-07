# Deployment and validation / Despliegue y validación

## Estado de esta entrega

Extraído de `apps/github-sentinel-radar.zip` el 2026-09-07 UTC. Publicación autorizada por el mantenedor mediante gh CLI. La consulta inicial
como `iberi22` confirmó que era necesario crear el repositorio.
Repositorio creado y main subido con gh/git. Pages desplegado correctamente:
https://github.com/iberi22/github-sentinel-radar/actions/runs/34078083746

Web verificada con Chromium: https://iberi22.github.io/github-sentinel-radar/
No se ejecutaron bloqueos reales. GH_BLOCKER_TOKEN aún no está configurado.

La plantilla se publica con datos vacíos. Los ejemplos heredados del ZIP no
acreditaban bloqueos, releases o verificaciones reales y siguen conservados
en el ZIP local original. Revisa la URL upstream antes de activar Sentinel.
Las heurísticas actuales sólo usan antigüedad y ratio de seguidores; no analizan
commits retrofechados ni la velocidad de seguimiento.

## Tokens y permisos

- `GH_BLOCKER_TOKEN`: secreto de Actions con un PAT **del usuario protegido**.
  Para bloqueo personal, permiso de usuario fine-grained **Block another user:
  write**. El radar requiere también permiso de usuario **Starring: read** para leer sus repositorios con estrella. No se sustituye
  por `GITHUB_TOKEN`: éste representa al repositorio y no al usuario protegido.
- Token de la web: PAT independiente limitado al repositorio destino con
  **Actions: write**. No necesita permiso para bloquear usuarios.
- `GITHUB_TOKEN`: sólo `contents: write` en los jobs que guardan datos. Pages
  tiene `contents: read`, `pages: write`, `id-token: write`.
- El token web persiste en `localStorage`, accesible a scripts del mismo origen
  (incluido Tailwind CDN). Usa un token de alcance mínimo y vencimiento corto;
  guardar el campo vacío lo elimina. Nunca se copia a los archivos del repo.

Referencias oficiales:
[Block a user](https://docs.github.com/en/rest/users/blocking#block-a-user),
[Workflow dispatch](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event),
[GITHUB_TOKEN y triggers](https://docs.github.com/en/actions/concepts/security/github_token).

## Sincronización y publicación

1. Crear o habilitar acceso a `iberi22/github-sentinel-radar` en GitHub. El repo
   local contiene `main` y `origin` preparado. No crear otro README remoto si se
   va a subir este historial inicial.
2. `git push -u origin main` desde este directorio. Si hay historial remoto,
   revisarlo e integrarlo; no forzar el push.
3. Configurar `GH_BLOCKER_TOKEN` con los permisos anteriores.
4. Settings → Pages → Source: **GitHub Actions**. Ejecutar `pages.yml` manualmente
   si el push inicial ocurrió antes de habilitar Pages.
5. Abrir `https://iberi22.github.io/github-sentinel-radar/`, guardar el PAT web y
   `iberi22/github-sentinel-radar`. Pulsar Actualizar Feed y comprobar `radar.yml`.
6. Pages se ejecuta al completarse correctamente Radar o Sentinel mediante
   `workflow_run`. Los pushes hechos con `GITHUB_TOKEN` no bastan para disparar
   otro workflow. Recargar la web cuando terminen ambos jobs; el dispatch sólo
   confirma la solicitud, no la publicación terminada.

Los workflows de escritura comparten exclusión mutua y tienen un límite de
10 minutos. La plantilla usa `main` para dispatch/Pages. Si cambias la rama por
defecto, ajusta ambos. El radar no tiene cron ni servicio residente: consume sólo
cuando se solicita y termina al acabar. `--force` registra actividad manual;
una ejecución sin ese argumento hiberna tras 7 días (configurable), y no renueva
la fecha de actividad. El input manual `force: false` respeta esa hibernación.

## Validación local reproducible

Python 3.11+; validado aquí con Python 3.12.12 y requests 2.33.0. La única
dependencia de ejecución es requests (`>=2.32.4,<3`). Node 22+ y Chromium se usan
sólo para las pruebas de navegador. No se necesita npm ni descargar navegadores.

```sh
uv venv --python python .venv
uv pip install --python .venv/bin/python -r requirements.txt
uv pip check --python .venv/bin/python
xavier exec '.venv/bin/python -m unittest discover -s tests -v'
xavier exec 'node tests/browser.mjs'
python -m http.server 8080 --bind 127.0.0.1
# Abrir http://127.0.0.1:8080/docs/index.html
```

Las pruebas de backend sustituyen la API y la escritura de datos. Las de Chromium
sirven la web real y sustituyen exclusivamente las llamadas a la API GitHub;
no usan un PAT real. La interfaz conserva Tailwind y fuentes por CDN, por lo que
la revisión visual requiere red. Los diccionarios y datos son locales.

TD-01 (webhooks organizacionales) y TD-02 (LLM local) siguen pendientes, con planes
paso a paso sincronizados en `TASK.md` y `.gitcore/planning/tasks.json`.

Prueba sobre el despliegue público (API GitHub simulada):

```sh
SENTINEL_URL=https://iberi22.github.io/github-sentinel-radar/ xavier exec 'node tests/browser.mjs'
```
