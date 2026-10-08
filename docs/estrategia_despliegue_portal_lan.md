# Estrategia de despliegue y acceso (Portal / LAN): Grupo de Infraestructura GIDAS

Este documento define quién es responsable de qué cuando el sistema SGM-GIDAS está desplegado.
En una frase: el desarrollo (Benjamín Briones, repo `BrionesBenjamin22/SGM-GIDAS`) es dueño del
código de la aplicación y de las releases, mientras que el grupo de infraestructura GIDAS es
dueño de la estrategia de despliegue, la VM, el acceso, las imágenes, los backups y los datos.
Nada de lo que sigue es un pedido para desarrollo: es nuestra operación y nuestra
responsabilidad. La comunicación de la release (`docs/comunicacion_dev_v1_1_0_beta_1.md`)
separa explícitamente lo que es nuestro de lo que es suyo.

## Ruta rápida

1. Antes de desplegar: preflight con `GIDAS_ALLOW_LAN_BIND=1` y `docker compose config --quiet`.
2. Después de migrar: `migrate` en exit 0 y `alembic_version` verificado.
3. Después de desplegar: smoke test y HTTP 200 en `/api/v1/health/live`, `/`, `/sgm-gidas/` y la
   dirección de la LAN.
4. Antes de cada upgrade: dump `pg_dump -Fc`, snapshot de volúmenes, copia externa y tag
   `:pre-<versión>` en las imágenes previas.
5. Nunca: `flask db downgrade` ni `docker compose down -v`.

## Arquitectura de acceso

| Elemento | Valor | Detalle |
|---|---|---|
| Entrada por la LAN | `http://sgm.gidas.local:8080` y `http://192.168.1.111:8080` | Proxy nginx publicado en el puerto 8080, para las máquinas del laboratorio |
| Aplicación principal | `/` | Servicio `frontend` |
| Portal GIDAS | `/sgm-gidas/` | Servicio `frontend_sgm`, build con `frontend/Dockerfile.portal` y `VITE_BASE_PATH=/sgm-gidas/` |
| Upstreams del proxy | `$frontend_upstream`, `$frontend_sgm_upstream`, `$backend_upstream` | Siempre por variable, con `resolver 127.0.0.11`. El preflight corre `nginx -t` en un contenedor aislado, sin la red de compose, y un hostname literal en `proxy_pass` lo hace fallar |
| Bind address | `NGINX_BIND_ADDRESS=0.0.0.0` | Vive en el `.env.production`, que está ignorado por git. El valor nunca se commitea en el código |

## Gates de validación

| Momento | Gate | Qué acredita |
|---|---|---|
| Antes | `GIDAS_ALLOW_LAN_BIND=1 bash scripts/validate-vm-deployment.sh .env.production` | Compose, topología, secretos y `nginx -t` interno |
| Antes | `docker compose config --quiet` | El compose y las variables de entorno cierran sin errores |
| Después de migrar | Contenedor `migrate` con exit 0 | Todas las migraciones de la release se aplicaron sin errores |
| Después de migrar | `SELECT version_num FROM alembic_version` | El esquema coincide con el esperado para la release desplegada |
| Después | `bash scripts/smoke-vm-deployment.sh .env.production` | migrate en cero, liveness, readiness y frontend |
| Después | HTTP 200 en `/api/v1/health/live`, `/`, `/sgm-gidas/` y `http://192.168.1.111:8080/` | API, aplicación principal, Portal y acceso por la LAN |

Sobre la bandera del preflight: `GIDAS_ALLOW_LAN_BIND=1` es un parche nuestro sobre
`backend/tools/validate_production_topology.py`. El validador de upstream exige
`NGINX_BIND_ADDRESS` en loopback y no trae flag de omisión, lo que dejaría al laboratorio sin
acceso por LAN. La bandera no está escrita en ningún archivo, se pasa al invocar; sin ella el
validador sigue exigiendo loopback, así que el comportamiento por defecto no cambia.

## Release y rollback

Punto de restauración antes de cada upgrade:

| Artefacto | Cómo se arma | Dónde queda |
|---|---|---|
| Dump lógico | `pg_dump -Fc` con los escritores detenidos | `/home/infra/gidas-backups/` y copia externa en la estación de trabajo (`~/gidas-backups-externos/`) |
| Snapshot de volúmenes | Archivo comprimido del volumen de datos con la base detenida | Mismo directorio y copia externa |
| Imágenes previas | Tag `:pre-v1.1.0-beta.1` en backend, frontend, frontend_sgm y migrate | Registro local de la VM |

Reglas duras:

- Nunca ejecutar `flask db downgrade`: cuatro de las migraciones de la release tienen
  `DELETE`/`DROP` en su rama inversa, así que el downgrade no devuelve los datos originales.
- Nunca ejecutar `docker compose down -v`: borra el volumen de la base de datos.
- Rollback real = restore del dump más las imágenes con tag `:pre-<versión>`.

Referencias: runbook de actualización con rollback
`docs/despliegue_v1_1_0_beta_1_rollback.md` y registro de ejecución
`docs/despliegue_v1_1_0_beta_1_ejecucion.md`.

## Política de repositorios

| Repo | URL | Uso |
|---|---|---|
| `origin` (nuestro) | `https://github.com/infraitgidas/sgm-gidas.git` | Código que está en producción, documentación y tareas. La rama `infra-estacion` preserva el historial de la estación de trabajo |
| `dev` (de desarrollo) | `https://github.com/BrionesBenjamin22/SGM-GIDAS` | Solo lectura: lo leemos, nunca pusheamos. Los cambios van por PR o cherry-pick, según lo acordado con desarrollo |

## Reparto de responsabilidades

| Área | Desarrollo | Infraestructura |
|---|---|---|
| Código y releases | Escribe el código, corrige errores y arma la release | Despliega y verifica en la VM |
| Arquitectura del Portal | Conoce y opina; no la implementa | Construye `frontend_sgm`, `frontend/Dockerfile.portal`, `VITE_BASE_PATH` y las locations del proxy |
| Acceso LAN y bind address | No aplica | `.env.production`, `NGINX_BIND_ADDRESS`, puerto 8080 y alcance desde el laboratorio |
| Preflight y validación de topología | Puede proponer mejoras al validador de upstream | Mantiene el parche `GIDAS_ALLOW_LAN_BIND` y ejecuta el gate antes de cada ventana |
| Imágenes y tags | Fija versiones de imagen en el compose | Construye, taggea y conserva las imágenes previas |
| Backups y restauración | No aplica | Dump, snapshot, copia externa y restore |
| Esquema de base de datos y migraciones | Escribe las migraciones (código) | Las ejecuta en producción y verifica `alembic_version` |
| Cron de BCRA | Su feature (`scripts/run-bcra-sync.sh`, 18:00 AR) | Programa y valida el cron en la VM |

## Brechas operativas conocidas

- El frontend no reporta qué release está corriendo, verificado el 2026-10-08. Hasta que eso
  cambie, la versión se confirma con `docker images` (tags de las imágenes) y con el log de
  arranque del backend, donde `APP_VERSION` llega a través de `configure_logging()`. Hay una
  nota al respecto dirigida a desarrollo en `docs/comunicacion_dev_v1_1_0_beta_1.md`.

## Checklist

- [ ] Preflight en verde con `GIDAS_ALLOW_LAN_BIND=1`
- [ ] `docker compose config --quiet` sin errores
- [ ] `migrate` en exit 0 y `alembic_version` coincide con la release
- [ ] Dump + snapshot + copia externa antes de la ventana
- [ ] Imágenes previas con tag `:pre-<versión>`
- [ ] Smoke test correcto y HTTP 200 en `/api/v1/health/live`, `/`, `/sgm-gidas/` y la LAN
- [ ] Sin `flask db downgrade` ni `docker compose down -v` en ningún momento

## Próximo paso

- [ ] Instalar el cron de BCRA, hoy no instalado en la VM.
- [ ] Verificar el backup automático del próximo sábado con el stack ya actualizado.
- [ ] Re-correr la batería de verificación completa después de cada release futura.
