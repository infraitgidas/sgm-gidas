# Registro de despliegue — v1.1.0-beta.1 (ejecución real)

Ejecución del runbook `docs/despliegue_v1_1_0_beta_1_rollback.md` sobre la VM de producción
**192.168.1.111** (`/home/infra/gidas`). Este documento deja constancia de lo hecho, de las
desviaciones respecto del plan y de las tareas pendientes.

| Campo | Valor |
|---|---|
| Fecha de ventana | 2026-10-08, 06:55 – 10:14 (UTC en la VM) |
| Operador | Emanuel Rodriguez Rodriguez (coord. infraestructura) |
| Versión anterior | `ceee87d` — alembic `9823db81d6d2` |
| Versión desplegada | `v1.1.0-beta.1` (`b8c1a81`) + merge local `af7dd1f` |
| HEAD de la VM | `94d62cb` |
| Alembic resultante | `a7c9e2f4b6d8` — **22 migraciones aplicadas** |
| Resultado | **Verde**: preflight, build, migrate exit 0, smoke, portal y LAN |

---

## 1. Punto de restauración creado (Fase 1)

| Artefacto | Ruta | Detalle |
|---|---|---|
| Dump lógico | `/home/infra/gidas-backups/pre-upgrade-v1.1.0-20261008-065505.dump` | 391 K, `pg_dump -Fc`, **896 objetos TOC** (verificado con `pg_restore --list`) |
| Snapshot del volumen | `/home/infra/gidas-backups/vol-pre-upgrade-v1.1.0-20261008-065505.tar.gz` | 7,8 M, 1658 archivos, tomado con `db` detenida |
| Copia externa | `~/gidas-backups-externos/` (estación de trabajo) | dump + snapshot por `scp` |

Escritores detenidos durante el dump: `backend`, `migrate`, `frontend`, `frontend_sgm`,
`nginx`. `db` y `redis` se mantuvieron arriba.

## 2. Imágenes anteriores preservadas (pedido explícito)

```text
gidas-backend:pre-v1.1.0-beta.1        6da17533436b
gidas-frontend:pre-v1.1.0-beta.1       f1fcb7ffb697
gidas-frontend_sgm:pre-v1.1.0-beta.1   f4ca2b280880
gidas-migrate:pre-v1.1.0-beta.1        7d3540836d48
```

Quedaron además las bases usadas: `postgres:16.15`, `redis:7.4.9-alpine`,
`nginxinc/nginx-unprivileged:1.27-alpine` (versión anterior del proxy) y
`nginxinc/nginx-unprivileged:1.31-alpine3.24` (la nueva).

Imágenes nuevas construidas en la ventana:

```text
gidas-backend:latest        bc19c40d0e49
gidas-frontend:latest       a2b650270446
gidas-frontend_sgm:latest   99b649fdf470
gidas-migrate:latest        fa37816f2dc6
```

## 3. Sincronización de código

La Fase 0 se ejecutó **en la VM** (no en la estación de trabajo) y **sin push** al remoto, para
no modificar el `main` de BrionesBenjamin22 durante la ventana.

| Commit | Descripción |
|---|---|
| `7fb60dc` | `chore(infra): tuning de VM, fix apt https y arquitectura de dos frontends` — commitea los 7 archivos modificados + `Dockerfile.portal` + `nginx.portal.conf` (antes untracked) |
| `af7dd1f` | Merge de `origin/main` (`b8c1a81`) |
| `94d62cb` | `fix(infra): excepcion de binding LAN y proxy_pass por variable en el Portal` |

### Conflictos resueltos (3 de 6 archivos con conflicto)

| Archivo | Resolución |
|---|---|
| `backend/Dockerfile` | builder de upstream (sin `apt`, `pip wheel --only-binary=:all:`) + runtime de upstream **con el `sed` https** (fix del 403); se descartó `gcc`/`libpq-dev`/`libpq5` porque `psycopg2-binary==2.9.11` trae rueda propia |
| `docker-compose.yml` | base upstream + tuning de la VM: `backend 768m/0.5 cpus/stop_grace 45s`, `redis cpus 0.25`, `nginx cpus 0.25` + healthcheck propio; se conservaron `stop_grace_period` e imágenes fijadas de upstream y el servicio `frontend_sgm` |
| `frontend/src/main.tsx` | ambos: limpieza de `localStorage` de upstream **y** `basename: VITE_BASE_PATH` (necesario para el subpath del Portal) |
| `frontend/Dockerfile`, `frontend/nginx.conf`, `nginx/default.conf` | auto-fusionados; se deduplicó `gzip_static` en `frontend/nginx.conf` |

Verificado tras la resolución: **0 marcadores de conflicto, 0 claves YAML duplicadas,
`docker compose config --quiet` OK**.

## 4. Desviaciones respecto del runbook

### 4.1 El preflight de upstream rechazó el binding de la LAN

`backend/tools/validate_production_topology.py` exige
`NGINX_BIND_ADDRESS` loopback y no tenía flag de omisión. La VM necesita `0.0.0.0` para
atender `sgm.gidas.local:8080` desde el laboratorio.

**Resolución:** excepción explícita del operador vía `GIDAS_ALLOW_LAN_BIND=1`, implementada
en el propio validador (6 líneas, sin tocar la lógica de las demás reglas). La bandera no está
en ningún archivo: hay que pasarla al invocar:

```bash
GIDAS_ALLOW_LAN_BIND=1 bash scripts/validate-vm-deployment.sh .env.production
```

Sin la bandera, el validador sigue exigiendo loopback (comportamiento por defecto intacto).
**Pendiente:** proponer el cambio a Benjamín o decidir si el laboratorio migra a loopback +
tunnel.

### 4.2 `nginx -t` fallaba por resolución de DNS

El preflight hace `nginx -t` en un contenedor aislado (sin red compose) y la config del Portal
tenía `proxy_pass http://frontend_sgm:8080;` — host literal que nginx resuelve al cargar.

**Resolución:** `set $frontend_sgm_upstream http://frontend_sgm:8080;` + `proxy_pass
$frontend_sgm_upstream;`, igual que ya se hacía con `$frontend_upstream` y `$backend_upstream`.
Con variable, el `resolver` resuelve en tiempo de request. Aproveché para unificar las dos
locations del Portal que seguían usando `X-Forwarded-Proto $scheme` y pasarlas a
`$gidas_forwarded_proto` (el `map` de upstream).

### 4.3 Fase 0 sin push

El runbook proponía pushear desde la estación de trabajo. No se hizo: los 3 commits viven solo
en la VM y los 2 commits de infra de la estación de trabajo (`58c929f`, `f0b85d4`) siguen sin
pushear. Ver pendientes.

## 5. Evidencia de la verificación

```text
$ docker inspect --format "{{.State.ExitCode}}" gidas_prod_migrate
0

$ psql -tAc "select version_num from alembic_version"
a7c9e2f4b6d8

$ bash scripts/validate-vm-deployment.sh .env.production   (con GIDAS_ALLOW_LAN_BIND=1)
Preflight correcto: Compose, topologia, secretos y Nginx interno validados.

$ bash scripts/smoke-vm-deployment.sh .env.production
Smoke test correcto: migrate=0, liveness, readiness y frontend disponibles.

$ curl -w "%{http_code}"
200  http://127.0.0.1:8080/api/v1/health/live
200  http://127.0.0.1:8080/
200  http://127.0.0.1:8080/sgm-gidas/      <- Portal
200  http://192.168.1.111:8080/            <- LAN
```

Estado final de contenedores:

```text
gidas_prod_backend        Up (healthy)
gidas_prod_db             Up (healthy)
gidas_prod_frontend       Up (healthy)
gidas_prod_frontend_sgm   Up            <- sin healthcheck definido
gidas_prod_proxy          Up (healthy)
gidas_prod_redis          Up (healthy)
```

Además se corrigió `APP_VERSION` en `backend/.env.production`: decía `ceee87d` y quedó en
`v1.1.0-beta.1`.

## 6. Rollback disponible si hace falta

Toda la ruta de recuperación está en `docs/despliegue_v1_1_0_beta_1_rollback.md` (Fase 5).

- **Dump:** `/home/infra/gidas-backups/pre-upgrade-v1.1.0-20261008-065505.dump` (+ copia en la
  estación de trabajo y en `~/gidas-backups-externos/`)
- **Snapshot:** `vol-pre-upgrade-v1.1.0-20261008-065505.tar.gz` (+ copia externa)
- **Imágenes anteriores:** tags `:pre-v1.1.0-beta.1`
- **Código anterior:** `ceee87d`
- **`flask db downgrade`: sigue prohibido.** `docker compose down -v`: prohibido.

---

## 7. Pendientes

- [ ] **Pushear** los 3 commits de la VM y los 2 de la estación de trabajo a `origin/main`
      (coordenar con Benjamín; ahora la VM tiene historial divergente).
- [ ] **Cron de BCRA** (`scripts/run-bcra-sync.sh`, 18:00 AR) — no instalado; las variables
      `BCRA_*` no están en `.env` porque los defaults del código coinciden con
      `backend/.env.example`.
- [ ] **Decidir con Benjamín** el destino de la excepción `GIDAS_ALLOW_LAN_BIND`.
- [ ] Prueba funcional con usuarios reales: login, memorias institucionales y export a Excel.
- [ ] Verificar el ciclo de backup del sábado 03:00 con el stack ya actualizado.
- [ ] Responder el mail a Briones con los puntos que no estaban en la release
      (fix https, arquitectura de dos frontends, healthcheck del proxy).
