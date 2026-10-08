# Comunicación con desarrollo: release v1.1.0-beta.1

**Para:** Benjamín Briones
**Asunto:** Respuesta a tu release v1.1.0-beta.1 y verificación en producción
**De:** Emanuel Rodriguez Rodriguez, coordinación de infraestructura
**Fecha:** 2026-10-08

Mensaje listo para enviar, más el respaldo técnico. La tabla completa de los 11 ajustes está
al final, como anexo.

---

## Mensaje

Benjamín, tu release **ya está desplegada en producción y quedó verde**: build, 22 migraciones
(aplicadas sin errores), smoke test, portal y LAN respondiendo 200, 6 contenedores sanos y los
8 usuarios con la contraseña idéntica a la del backup previo. Buen trabajo.

### Nuestra estrategia de despliegue (información, no una acción para vos)

Esto es responsabilidad del grupo de infraestructura GIDAS: lo armamos y lo mantenemos nosotros,
y no tenés que hacer nada con esto.

- Acceso desde la LAN del laboratorio con el Portal en el subpath `/sgm-gidas/`, servido por el
  servicio `frontend_sgm` (build con `frontend/Dockerfile.portal` y
  `VITE_BASE_PATH=/sgm-gidas/`).
- Proxy nginx con upstreams por variable (`$frontend_upstream`, `$frontend_sgm_upstream`,
  `$backend_upstream`) y `resolver 127.0.0.11`, porque el preflight valida con `nginx -t` en un
  contenedor aislado y un hostname literal lo hace fallar.
- `NGINX_BIND_ADDRESS=0.0.0.0` vive en el `.env.production` (ignorado por git), nunca en el
  código.
- Nuestro preflight corre la validación de topología con `GIDAS_ALLOW_LAN_BIND=1`: es un parche
  nuestro en `backend/tools/validate_production_topology.py` y, sin la bandera, el validador
  sigue exigiendo loopback.
- Antes de cada upgrade armamos punto de restauración (`pg_dump -Fc` + snapshot de volúmenes) y
  dejamos las imágenes previas con el tag `:pre-v1.1.0-beta.1`; nunca ejecutamos
  `flask db downgrade` ni `docker compose down -v`.

El detalle de todo esto está en `docs/estrategia_despliegue_portal_lan.md`.

Ahora, **2 puntos de lo que te habíamos marcado no llegaron en la release** y los tuvimos que
preservar a mano durante la ventana:

1. **Fix de https en las fuentes de Debian.** Sin ese `sed` antes de cada `apt-get update`,
   el build vuelve a romperse con error 403 si el espejo deja de servir por http. Vos ya lo
   tenías resuelto en tu commit `58c929f`, pero no está en GitHub.
2. **Healthcheck del proxy nginx en compose.** El de tu release, en `frontend/Dockerfile`,
   vigila al frontend y está bien; falta el del proxy (puerta 8080) en `docker-compose.yml`.
   Son dos sondas distintas.

El detalle punto por punto de los 11 ajustes está en `docs/verificacion_release_v1_1_0_beta_1.md`
(sección 6).

### Lo que funcionó de lo tuyo

- **Build sin compilador** (`pip wheel --only-binary=:all:`): lo probamos en producción y
  funcionó. `psycopg2-binary==2.9.11` trae rueda propia, así que no hizo falta `gcc` ni
  `libpq-dev`. Es más rápido y más liviano, y ya quedó validado en una VM real.
- **22 migraciones** aplicadas de punta a punta, `alembic` de `9823db81d6d2` a `a7c9e2f4b6d8`,
  `migrate` con exit 0. La cadena lineal se ejecutó limpia.
- **Versionado de imágenes** (`python:3.11.16-slim`, `postgres:16.15`, etc.) y
  **`stop_grace_period`** en todos los servicios: adoptados tal cual, sin tocar. La idea de
  fijar versiones exactas es mejor que nuestra, quedó incorporada.

### Qué te pedimos / decisiones

- [ ] Adoptar los 2 puntos que faltan (https en fuentes Debian y healthcheck del proxy en
      compose). Te los podemos mandar como PR o rama desde nuestro repo, como te quede más
      cómodo.
- [ ] Decidir si instalamos ahora el cron de BCRA (`scripts/run-bcra-sync.sh`, 18:00 AR). Hoy
      no está instalado; las variables `BCRA_*` tienen defaults razonables en el código, así que
      nada se rompe esperando.

### Nota (información / sugerencia): el frontend no reporta qué release está corriendo

Lo verificamos en producción el 2026-10-08 y hoy no hay forma de saber desde el navegador qué
versión está servida:

- Ni el código del frontend ni `frontend/vite.config.ts` definen `VITE_*VERSION` ni
  `__APP_VERSION__`.
- El `index.html` servido no tiene meta de versión y el bundle construido no contiene el string
  `v1.1.0`.
- La API no expone `/version` ni `/info`: `/api/v1/health/ready` devuelve solo `status` y
  `dependencies`, y el header `API-Version: v1` es el de contrato de la API (una constante), no
  la release.
- `APP_VERSION` existe en la configuración del backend, pero solo se pasa a `configure_logging()`
  en `backend/app.py:33`, así que llega al log y a ninguna respuesta HTTP.

Sugerencia, sin apuro: inyectar la tag o el commit en el build como `VITE_APP_VERSION` y
exponerla en `/api/v1/health/ready` o en un endpoint `/version`. Así el operador confirma qué
versión está corriendo desde el navegador, sin entrar por SSH a la VM.

### Sincronización de repos

Creamos nuestro propio repo, `https://github.com/infraitgidas/sgm-gidas.git`, y pasamos el
tuyo (`https://github.com/BrionesBenjamin22/SGM-GIDAS`) a **solo lectura**: lo leemos, no
pusheamos. Tu `main` no se tocó en toda la ventana.

¿Cómo querés recibir nuestros cambios de infraestructura? Tenés dos caminos: que te abramos un
PR contra tu repo, o que vos hagas cherry-pick desde nuestra rama. Decinos cuál preferís y lo
dejamos como flujo fijo.

Ojo con un detalle: los commits locales de la sesión anterior de la estación de trabajo quedaron
preservados en la rama `infra-estacion` (`f0b85d4`), porque `main` de nuestro repo quedó con el
código de producción (`2c011a8`, que ya incluye la release + nuestros ajustes + documentación).
La VM, además, tiene 3 commits propios de la ventana (`7fb60dc`, `af7dd1f`, `94d62cb`). O sea:
hay historial divergente en tres lugares y coordinar el push es el primer pendiente.

---

## Anexo: tabla de los 11 ajustes con lo que pasó en producción

Adaptada de `docs/verificacion_release_v1_1_0_beta_1.md` §6, actualizada con el resultado real
de la ventana del 2026-10-08. Las filas marcadas como responsabilidad de infraestructura no son
un pedido para desarrollo.

| # | Ajuste | ¿En la release? | Acción / qué pasó en producción |
|---|---|---|---|
| 1 | Fix https en fuentes Debian | **No** | Re-aplicado en la ventana (commit `7fb60dc`); falta subirlo a tu repo |
| 2 | Arquitectura dos frontends / Portal | **No** | **responsabilidad de infra (no aplica a desarrollo)**: la mantenemos y quedó mergeada de nuestro lado (VM y repo `infraitgidas`) |
| 3 | Límites de recursos | Sí, valores distintos | **responsabilidad de infra (no aplica a desarrollo)**: conservamos nuestro tuning en la VM (768m / 0.5 cpus) y lo gestionamos nosotros |
| 4 | Versionado de imágenes | Sí, mejor que el nuestro | Adoptado tal cual |
| 5 | `stop_grace_period` | Sí, más completo | Adoptado tal cual |
| 6 | Healthcheck del proxy nginx | **No** (solo el del frontend) | Mantenido el nuestro en compose; falta sumarlo en tu repo |
| 7 | gzip: `gzip_static` + build `.gz` | Sí | Adoptado, sumando el gzip dinámico para las respuestas de la API |
| 8 | `X-Forwarded-Proto` + timeouts | Sí, mejor que el nuestro | Adoptado; además unificamos las locations del Portal a `$gidas_forwarded_proto` |
| 9 | `no-cache` en `index.html` | Sí | Adoptado |
| 10 | `NGINX_BIND_ADDRESS` | Default distinto | **responsabilidad de infra (no aplica a desarrollo)**: `.env.production` (ignorado por git) con `0.0.0.0`, más nuestra bandera `GIDAS_ALLOW_LAN_BIND=1` en el preflight |
| 11 | Build backend sin compilador | Sí (distinto) | **Verificado funcionando en producción**, sin `gcc` |
