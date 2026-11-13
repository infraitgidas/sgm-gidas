# Registro de despliegue — v1.1.0-beta.2 (ejecución real)

Ejecución del plan `docs/despliegue_v1_1_0_beta_2_analisis.md` sobre la VM de
producción **192.168.1.111** (`/home/infra/gidas`). Este documento registra lo
hecho, la evidencia y los pendientes.

| Campo | Valor |
|---|---|
| Ventana | 2026-11-13 16:50 – 16:56 (UTC−3) / 19:50 – 19:56 UTC |
| Operador | Emanuel Rodriguez Rodriguez (coord. infraestructura) |
| Versión anterior | `f800778` (`v1.1.0-beta.1` + merge local) — alembic `a7c9e2f4b6d8` |
| Versión desplegada | tag `v1.1.0-beta.2-infra.1` (`013ba97`) |
| Alembic resultante | `e8c2a4f6b0d1` — **8 migraciones aplicadas** |
| Resultado | **Verde**: preflight, build, migrate exit 0, smoke, healthchecks, SMTP y Portal |
| Rollback | R0/R1/R2/R3 documentados y punto de restauración verificado |

---

## 1. Integración de código

| Elemento | Valor |
|---|---|
| Rama | `release/v1.1.0-beta.2` |
| Merge | `f4f3a1c` — 56 commits del dev (`09e4e10`) |
| Docs | `013ba97` — análisis y runbook de rollback |
| Tag desplegado | `v1.1.0-beta.2-infra.1` |
| Push | `origin` (infraitgidas/sgm-gidas) — rama y tag |

Conflictos resueltos:

| Archivo | Resolución |
|---|---|
| `.gitignore` | Se conservó el nuestro: ignora `secrets*.yml`/`secrets*.yaml`; no ignora `/tasks` |
| `backend/tools/validate_production_topology.py` | Se tomó el del dev; conserva `GIDAS_ALLOW_LAN_BIND=1` y el mensaje que la prueba verifica literal |
| `scripts/send_mail.py` | Se tomó el del dev (destinatarios con `infrait@frlp.utn.edu.ar`) |

`docker compose config` renderizó los 8 servicios, incluidos `frontend_sgm` y
`email-worker`.

---

## 2. Punto de restauración (Fase 1)

| Artefacto | Ruta | Verificación |
|---|---|---|
| Dump lógico | `/home/infra/gidas-backups/pre-upgrade-v1.1.0-beta.2-20261113-165006.dump` | 481 K, `pg_dump -Fc`, **1104 objetos TOC** |
| Snapshot de volumen | `/home/infra/gidas-backups/vol-pre-upgrade-v1.1.0-beta.2-20261113-165006.tar.gz` | 9,1 M, **1754 archivos**, tomado con `db` detenida |
| Copia externa | `~/gidas-backups-externos/` (estación de trabajo) | dump + snapshot por `scp` |
| Drill de restore | base `gidas_drill` | **88 tablas** restauradas (igual que producción) |

Escritores detenidos durante el dump: `backend`, `migrate`, `frontend`,
`frontend_sgm`, `nginx`. `db` y `redis` permanecieron arriba.

### Imágenes anteriores preservadas

```text
gidas-backend:pre-v1.1.0-beta.2        bc19c40d0e49
gidas-frontend:pre-v1.1.0-beta.2       a2b650270446
gidas-frontend_sgm:pre-v1.1.0-beta.2   99b649fdf470
gidas-migrate:pre-v1.1.0-beta.2        fa37816f2dc6
```

Imágenes nuevas desplegadas:

```text
gidas-backend:latest        e9f53a99bf00
gidas-frontend:latest       ab40a36654c8
gidas-frontend_sgm:latest   a5c00e14201a
gidas-migrate:latest        b2d7ccabf8b2
gidas-email-worker:latest   06645641af70
```

---

## 3. Configuración aplicada (sin secretos)

Copia previa: `backend/.env.production.bak-beta2-20261113-165006` (permisos `600`).

Claves agregadas/actualizadas en `backend/.env.production`:

```env
APP_VERSION=v1.1.0-beta.2
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_DEFAULT_SENDER=GIDAS <infrait@frlp.utn.edu.ar>
MAIL_USERNAME=infrait@frlp.utn.edu.ar
MAIL_PASSWORD=<desde .env.backup>
SMTP_TLS_MODE=starttls
SMTP_TIMEOUT_SECONDS=20
EMAIL_WORKER_POLL_SECONDS=5
EMAIL_OUTBOX_ENCRYPTION_KEY=<Fernet generada>
PASSWORD_RESET_HMAC_KEY=<aleatoria de 64 caracteres>
PASSWORD_RESET_PUBLIC_URL=https://sgm.gidas.local/restablecer-password
FRONTEND_URLS=http://192.168.1.111:8080,http://localhost:8080,http://sgm.gidas.local,https://sgm.gidas.local
```

`EMAIL_OUTBOX_ENCRYPTION_KEY` y `PASSWORD_RESET_HMAC_KEY` son distintas entre sí
y de `SECRET_KEY`, `JWT_SECRET` y `REFRESH_SECRET`. El archivo conservó permisos
`600`.

---

## 4. Migraciones

Se usó upgrade escalonado para evitar el aborto de `d3f5a7c9e1b2`:

1. `flask db upgrade c2e4a6b8d0f1` — agrega `nombre`/`apellido` nullable.
2. Carga de 17 registros de prueba con el mapa aprobado (15 valores distintos).
3. Verificación: **0 filas** con `nombre`/`apellido` nulos o vacíos.
4. `flask db upgrade` — 7 migraciones restantes.

Salida:

```text
c2e4a6b8d0f1 -> d3f5a7c9e1b2  Normaliza exclusivamente el conjunto ficticio revisado de ISS-34.
d3f5a7c9e1b2 -> e4a6c8f0b2d3  Vincula fotos de personal a su identidad estable, conservando su contenido.
e4a6c8f0b2d3 -> f6b8d0e2a4c6  Conserva moneda original en equipamiento, transferencias y sus versiones.
f6b8d0e2a4c6 -> c3e5a7b9d1f2  Permite actividades de docencia en curso y sus fotos sin fecha de fin.
c3e5a7b9d1f2 -> e5a7c9d1f3b6  Recuperacion por correo y unicidad normalizada de cuentas.
e5a7c9d1f3b6 -> a6c8e0f2b4d6  Pertenencia de distinciones independiente de su proyecto opcional.
a6c8e0f2b4d6 -> e8c2a4f6b0d1  Referato y alcance de trabajos, preservando históricos sin informar.
```

`alembic_version = e8c2a4f6b0d1`.

---

## 5. Verificación

### 5.1 Preflight

```text
Topologia productiva valida (GIDAS_ALLOW_LAN_BIND=1): proxy publicado en la LAN
por decision del operador y roles separados.
Escaneo basico de secretos: sin hallazgos.
Preflight correcto: Compose, topologia, secretos y Nginx interno validados.
```

### 5.2 Migrate

```text
ExitCode: 0
Roles y cargos iniciales verificados/cargados correctamente
Migraciones y permisos completados
```

### 5.3 Smoke

```text
Smoke test correcto: migrate=0, liveness, readiness y frontend disponibles.
```

### 5.4 Endpoints

```text
200  http://127.0.0.1:8080/api/v1/health/live
200  http://127.0.0.1:8080/api/v1/health/ready
200  http://127.0.0.1:8080/
200  http://127.0.0.1:8080/sgm-gidas/      <- Portal
200  http://192.168.1.111:8080/            <- LAN
200  /login
200  /recuperar-password
200  /restablecer-password
200  assets/index-U3aDObAd.js
```

### 5.5 Seguridad y nuevos servicios

```text
current_user del backend: gidas_app
tablas nuevas: email_outbox, password_reset_request
email-worker: Up (healthy), heartbeat /tmp/gidas-email-worker-heartbeat vigente
SMTP login (smtp.office365.com:587 STARTTLS): código 235
POST /api/v1/auth/password-reset/request (correo inexistente): 202, sin encolar
email_outbox: 0 filas
```

Estado final:

```text
gidas_prod_backend        Up (healthy)
gidas_prod_db             Up (healthy)
gidas_prod_email_worker   Up (healthy)
gidas_prod_frontend       Up (healthy)
gidas_prod_frontend_sgm   Up
gidas_prod_proxy          Up (healthy)
gidas_prod_redis          Up (healthy)
gidas_prod_migrate        Exited (0)
```

---

## 6. Desviaciones respecto del plan

| Punto | Plan | Ejecución |
|---|---|---|
| Orden de fases | Fase 3 (migraciones) antes de construir | Se construyó la imagen nueva primero, porque el upgrade escalonado necesita el código beta.2 para validar correo y ejecutar Alembic |
| `DROP/CREATE DATABASE` del drill | Un solo `psql -c` | Se separaron en dos comandos: PostgreSQL no permite `DROP DATABASE` en bloque de transacción |
| Restore del drill | — | Primer intento falló por el punto anterior; se repitió y quedó en 88 tablas |

No hubo desviaciones de seguridad ni cambios de alcance.

---

## 7. Rollback disponible

Runbook: `docs/despliegue_v1_1_0_beta_2_rollback.md`.

- **R0** (sin migraciones aplicadas): `git checkout f800778` + `up --build -d`.
  No aplica ya: las migraciones están aplicadas.
- **R1** (datos corruptos): código anterior + `DROP SCHEMA public CASCADE` +
  restore del dump `pre-upgrade-v1.1.0-beta.2-20261113-165006.dump`.
- **R2**: snapshot `vol-pre-upgrade-v1.1.0-beta.2-20261113-165006.tar.gz`.
- **R3**: copia externa en `~/gidas-backups-externos/`.

**Prohibido:** `flask db downgrade`, `docker compose down -v`, restaurar sobre la
base activa con escritores conectados.

---

## 8. Pendientes

- [ ] **Habilitar TLS** para que `https://sgm.gidas.local/restablecer-password`
      sea alcanzable. Hoy el enlace de recuperación se genera pero no se sirve.
      Alternativa evaluada: Cloudflare Tunnel directo a `127.0.0.1:8080`
      (mencionado por el preflight de la release).
- [ ] Probar la recuperación de contraseña de punta a punta con un usuario real
      y una casilla controlada.
- [ ] Validación visual y funcional del usuario: login, memorias (reapertura y
      Excel), Personal con Nombre/Apellido, distinciones con proyecto opcional,
      referato/alcance de trabajos y Portal `/sgm-gidas/`.
- [ ] Confirmar con GIDAS si algún importe existente de equipamiento o
      transferencias estaba en USD: la migración `f6b8d0e2a4c6` los marcó como
      `ARS` por defecto.
- [ ] Actualizar documentación técnica y `CHANGELOG.md` **después** de la
      aceptación visual del usuario.
- [ ] Proponer al dev la excepción de datos para `d3f5a7c9e1b2` (migración que
      hoy solo acepta el dataset ficticio) y la política de recuperación por
      HTTP en staging.

---

## 9. Incidente post-despliegue: sesión del Portal

**Síntoma.** El Portal `/sgm-gidas/` mostraba "Lo sentimos, no pudimos recuperar
su sesión" con un botón `Reintentar` que volvía al mismo estado.

**Causa 1 — path de la cookie.** La cookie `gidas_refresh` se emite con
`Path=/api/v1/auth`, pero el Portal llama a `/sgm-gidas/api/v1/auth/refresh`.
El navegador no envía una cookie cuyo `Path` no prefija la URL: el refresh
llegaba sin cookie y el backend respondía `401`.

**Causa 2 — origen no confiable.** La validación se hizo por el túnel de
Cloudflare `https://inns-officials-singles-green.trycloudflare.com/sgm-gidas/`.
Ese origen no estaba en `FRONTEND_URLS`, por lo que `_is_trusted_cookie_request`
devolvía `403` antes de leer la cookie.

**Fix aplicado.**
- `nginx/default.conf`, bloque `location /sgm-gidas/api/`:
  `proxy_cookie_path /api/v1/auth /sgm-gidas/api/v1/auth;` para que la cookie
  quede acotada a la API del Portal y el navegador la envíe en cada refresh.
- `FRONTEND_URLS` de la VM: se agregó el origen del túnel. Backup del entorno:
  `backend/.env.production.bak-tunnel-<fecha>`.
- Se mantuvo el API base del Portal en `/sgm-gidas/api/v1`: el túnel solo expone
  ese subpath; la raíz `/api/` pertenece a otra aplicación.
- Se descartó el primer intento de mover el API base del Portal a `/api/v1`
  (commit `8067d58`), porque rompía el acceso por túnel. El fix final es
  `4c83047`.

**Evidencia.**
- `POST /sgm-gidas/api/v1/auth/logout` vía túnel y LAN devuelve
  `Set-Cookie: ... Path=/sgm-gidas/api/v1/auth`.
- Login con usuario inexistente vía túnel: `401` (antes `403`).
- Refresh sin cookie vía túnel: `401` (esperado).
- Assets del Portal vuelven a referenciar `/sgm-gidas/api/v1`.

**Nota operativa.** El túnel es efímero: si cambia el hostname hay que
actualizar `FRONTEND_URLS` (y, si se usa el enlace de recuperación por el túnel,
`PASSWORD_RESET_PUBLIC_URL`) y reiniciar `backend`.
