# Puesta en marcha sin token web

## Usar este dashboard

1. Abre [la web](https://iberi22.github.io/github-sentinel-radar/). Leer el feed no requiere iniciar sesión.
2. Pulsa **Actualizar Feed ⚡**. Se abre el workflow en GitHub, usando tu sesión habitual.
3. Pulsa **Run workflow** y confirma. Vuelve a la web: recogerá el feed nuevo cuando terminen Radar y Pages.

GitHub exige permiso de escritura en el repositorio para ejecutar el workflow.
Si no lo tienes, crea tu propia copia. El dashboard incluye **Primeros pasos**,
con botones Siguiente/Atrás y enlaces al repositorio correcto.

La web nunca recibe credenciales. Los PAT guardados por versiones anteriores se
eliminan al cargarla. Tema e idioma permanecen en localStorage; la espera de un
feed nuevo sólo se conserva durante la sesión. La comprobación consulta un JSON
cada 20 segundos, únicamente con la pestaña visible, y termina al recibir datos
nuevos o al pasar cinco minutos. No dispara escaneos automáticamente ni considera
que abrir GitHub sea prueba de que el workflow se ejecutó.

## Crear tu copia

1. Usa **Use this template → Create a new repository** y crea un repositorio público.
2. Abre Actions y habilita los workflows si GitHub lo solicita. En Settings → Pages,
   selecciona **GitHub Actions** como origen. Ejecuta **Deploy GitHub Pages** una vez.
3. Abre la web de tu copia y pulsa Actualizar Feed. No hace falta crear ni pegar tokens.

GitHub no permite habilitar Pages inicialmente con el GITHUB_TOKEN automático;
por eso el paso de Settings → Pages se hace una vez desde tu sesión de GitHub.
El despliegue genera `site.json` con repositorio y rama, por lo que la web funciona
en copias y dominios personalizados sin editar JavaScript. Para la plantilla,
conserva `main`: los triggers de Pages todavía filtran esa rama.

## Radar

El workflow usa el **GITHUB_TOKEN automático de Actions**, con `contents: write`
para guardar el feed. Consulta las estrellas **públicas del propietario** mediante
`GET /users/{username}/starred`. No usa GH_BLOCKER_TOKEN y no exporta metadatos
privados. Para una organización o un perfil distinto, configura la variable de
Actions **RADAR_USERNAME** con el usuario deseado. Un perfil privado puede dar un
feed vacío; no es un error de autenticación del navegador.

No tiene cron ni servidor residente. Cada ejecución termina al acabar, con límite
de 10 minutos. La ejecución manual fuerza el despertar de forma predeterminada.
`force: false` respeta la hibernación de 7 días y no renueva actividad manual.
Pages se ejecuta después del workflow mediante `workflow_run`; los commits hechos
con GITHUB_TOKEN por sí solos no disparan otro workflow.

## Sentinel

El bloqueo personal es **opcional** y requiere autorización del usuario protegido.
Configura una sola vez el secreto de Actions **GH_BLOCKER_TOKEN**, con un PAT de
usuario fine-grained y permiso **Block another user: write**. No se pega en esta
web. GITHUB_TOKEN representa al repositorio y no permite bloquear en tu nombre.
La presencia del secreto no demuestra que sus permisos sean correctos.

En `iberi22/github-sentinel-radar` se confirmó que ese secreto ya existe. Esta
entrega prueba el radar real, pero no ejecuta bloqueos para probar la interfaz.
Las heurísticas usan antigüedad y ratio de seguidores; no detectan commits
retrofechados. Revisa los umbrales y la lista upstream antes de activar bloqueos.

## Por qué queda una confirmación en GitHub

GitHub Pages sólo sirve archivos estáticos. Un clic que ejecute un workflow dentro
del dashboard necesitaría credenciales en el navegador o un servicio de
GitHub App/OAuth que autentique al usuario y guarde las credenciales. En esta
arquitectura, GitHub gestiona esa sesión y confirmación. No hay un endpoint público
que permita a cualquier visitante gastar la cuota de Actions del propietario.
Una GitHub App con backend es una posible ampliación si se prioriza ese clic sobre
el coste y mantenimiento de otra capa; no forma parte de esta implementación.

## Validación reproducible

Python 3.11+, requests `>=2.32.4,<3`; Node 22+ y Chromium sólo para pruebas.

```sh
uv venv --python python .venv
uv pip install --python .venv/bin/python -r requirements.txt
xavier exec '.venv/bin/python -m unittest discover -s tests -v'
xavier exec 'node tests/browser.mjs'
SENTINEL_URL=https://iberi22.github.io/github-sentinel-radar/ xavier exec 'node tests/browser.mjs'
```

La prueba de navegador verifica 10 idiomas/RTL, guía, migración de credenciales,
repositorios alternativos, navegación sin llamadas a la API GitHub, carga del feed,
pausa y límite de espera, y XSS. No envía solicitudes de escaneo reales.

## Referencias oficiales

- [Ejecutar workflows manualmente](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow).
- [Estrellas públicas por usuario](https://docs.github.com/en/rest/activity/starring#list-repositories-starred-by-a-user).
- [Bloqueo personal](https://docs.github.com/en/rest/users/blocking#block-a-user).
- [GITHUB_TOKEN y triggers](https://docs.github.com/en/actions/concepts/security/github_token).
- [Restricción de nombres GITHUB_ en secretos](https://docs.github.com/en/actions/reference/security/secrets).
- [Habilitación de Pages y permisos](https://github.com/actions/configure-pages/blob/main/action.yml).
