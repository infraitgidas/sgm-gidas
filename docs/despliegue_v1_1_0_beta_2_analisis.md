# Despliegue v1.1.0-beta.2 — Análisis, bloqueantes y plan de ejecución

Documento de preparación para actualizar la VM de producción **192.168.1.111**
(`/home/infra/gidas`) desde `v1.1.0-beta.1` hasta `v1.1.0-beta.2` (`09e4e10`,
2026-11-07), con sincronización al repositorio de infraestructura y rollback
probado antes de tocar datos.

| Campo | Valor |
|---|---|
| Fecha de análisis | 2026-11-13 |
| Operador | Emanuel Rodriguez Rodriguez (coord. infraestructura) |
| Versión desplegada en la VM | `v1.1.0-beta.1` + merge local (`f800778`) |
| Alembic actual | `a7c9e2f4b6d8` |
| Versión objetivo | `v1.1.0-beta.2` (`09e4e10`) |
| Alembic objetivo | `e8c2a4f6b0d1` (8 revisiones nuevas, cadena lineal) |
| Rama de integración | `release/v1.1.0-beta.2` (`f4f3a1c`) |
| Resultado del análisis | **Viable con 2 precondiciones obligatorias** |

---

## 1. Resumen ejecutivo

La beta.2 es una entrega grande: **56 commits, 306 archivos, +12.317 / −1.570**
respecto de la base común `v1.1.0-beta.1`. Trae autenticación con recuperación de
contraseña por correo, un servicio nuevo `email-worker`, reapertura y exportación
de memorias, separación de nombre/apellido de Personal y varios ajustes de
frontend.

El código se puede integrar sin dolor: el merge con la rama de infraestructura
solo tuvo **3 conflictos menores** y ya está resuelto en `release/v1.1.0-beta.2`.

Pero **el despliegue no puede ejecutarse tal cual**. Hay dos precondiciones
duras, ambas verificadas contra la VM real:

1. **La migración `d3f5a7c9e1b2` aborta con los datos actuales.** El plan de
   normalización de nombres solo acepta el dataset ficticio de ISS-34 y rechaza
   cualquier correspondencia desconocida. En producción hay **15 valores
   distintos que no están en el mapa**; los 17 registros de Personal, Becario e
   Investigador son datos de prueba.
2. **El backend no arranca sin configuración de correo.** `create_app()` ejecuta
   `validate_email_settings()`. Con `APP_ENV=staging` exige SMTP, dos claves
   nuevas y una `PASSWORD_RESET_PUBLIC_URL` **HTTPS** que pertenezca a un origen
   de `FRONTEND_URLS`. Hoy la VM atiende solo HTTP. Sin resolverlo, fallan
   `migrate`, `backend` y `email-worker` antes de iniciar.

Ambas tienen solución acotada y están detalladas en §5 y §8.

---

## 2. Estado actual de la VM (evidencia)

Verificado por SSH el 2026-11-13 19:37 UTC:

```text
hostname: sgm-gidas.gidas.local
HEAD:     f800778  (2 commits por delante del origin/main local de la VM)
status:   working tree limpio
alembic:  a7c9e2f4b6d8
disco:    37G total, 9,6G usados, 27G libres
```

Contenedores:

```text
gidas_prod_backend        Up 4 days (healthy)
gidas_prod_db             Up 4 days (healthy)
gidas_prod_frontend       Up 4 days (healthy)
gidas_prod_frontend_sgm   Up 4 days
gidas_prod_proxy          Up 4 days (healthy)
gidas_prod_redis          Up 4 days (healthy)
```

Backups disponibles:

```text
gidas-weekly-20261107-030001.dump   480K   (semanal automático)
gidas-weekly-20261031-030001.dump   480K
gidas-weekly-20261024-030002.dump   480K
gidas-weekly-20261017-030001.dump   474K
pre-upgrade-v1.1.0-20261008-065505.dump        391K
vol-pre-upgrade-v1.1.0-20261008-065505.tar.gz  7,8M
gidas-initial-20260828-113530.dump              386K
```

Configuración relevante (sin secretos):

```env
APP_ENV=staging
APP_VERSION=v1.1.0-beta.1
FRONTEND_URL=http://192.168.1.111:8080
FRONTEND_URLS=http://192.168.1.111:8080,http://localhost:8080,http://sgm.gidas.local
HSTS_ENABLED=False
RATELIMIT_STORAGE_URI=redis://redis:6379/0
```

No hay Nginx de host, ni TLS en `:443`, ni `/etc/nginx/tls`. El único puerto
publicado es `:8080`.

---

## 3. Delta de la release

### 3.1 Integración de código

| Tema | Resultado |
|---|---|
| Base común | `b8c1a81` (`v1.1.0-beta.1`) |
| Commits nuevos del dev | 56 |
| Conflicto `.gitignore` | Se conserva el nuestro (ignora `secrets*.yml`; no ignora `/tasks`) |
| Conflicto `backend/tools/validate_production_topology.py` | Se toma el del dev; conserva la excepción `GIDAS_ALLOW_LAN_BIND=1` y el mensaje que la prueba verifica literal |
| Conflicto `scripts/send_mail.py` | Se toma el del dev (incluye `infrait@frlp.utn.edu.ar` en destinatarios) |
| `docker-compose.yml` | Auto-fusionado: se conserva `frontend_sgm` y se agrega `email-worker` |
| `backend/Dockerfile`, `frontend/Dockerfile`, `nginx/default.conf`, `frontend/nginx.conf` | Idénticos entre ambas ramas |
| `frontend/src/main.tsx` | Auto-fusionado: agrega rutas `/recuperar-password` y `/restablecer-password` |

La rama `release/v1.1.0-beta.2` ya contiene el merge (`f4f3a1c`).
`docker compose config --services` renderiza los 8 servicios, incluidos
`frontend_sgm` y `email-worker`.

### 3.2 Migraciones nuevas

Cadena lineal desde `a7c9e2f4b6d8`:

```text
a7c9e2f4b6d8 (actual)
  └─ c2e4a6b8d0f1  personal_nombre_apellido
      └─ d3f5a7c9e1b2  normalizar_nombres_personal
          └─ e4a6c8f0b2d3  personal_snapshot_identidad
              └─ f6b8d0e2a4c6  moneda_equipamiento_transferencias
                  └─ c3e5a7b9d1f2  docencia_fecha_fin_opcional
                      └─ e5a7c9d1f3b6  password_reset_outbox
                          └─ a6c8e0f2b4d6  distincion_uct_propia
                              └─ e8c2a4f6b0d1  clasificacion_trabajos  (head)
```

| Revisión | Qué hace | Riesgo en producción |
|---|---|---|
| `c2e4a6b8d0f1` | Agrega `nombre`/`apellido` nullable a Personal, Becario, Investigador | Bajo |
| `d3f5a7c9e1b2` | Normaliza 112 registros ficticios con un mapa cerrado; **aborta si un valor no está en el mapa** | **ALTO — bloqueante** |
| `e4a6c8f0b2d3` | Vincula fotos históricas a `identidad_personal`; crea FK, unique e índice | Medio (valida duplicados) |
| `f6b8d0e2a4c6` | Agrega `moneda` default `ARS` a equipamiento y transferencias | Bajo, pero **asume ARS** |
| `c3e5a7b9d1f2` | Permite `fecha_fin` nula en docencia | Bajo |
| `e5a7c9d1f3b6` | Normaliza mails a minúsculas, unique funcional, `email_outbox`, `password_reset_request` | Medio (valida duplicados) |
| `a6c8e0f2b4d6` | Agrega `grupo_utn_id` NOT NULL a distinciones, con inferencia en 3 pasos | Medio (aborta si queda sin UCT) |
| `e8c2a4f6b0d1` | Agrega `referato` y `alcance` a trabajos | Bajo |

**Regla de rollback:** varias migraciones no son reversibles en datos
(`d3f5a7c9e1b2` lo declara explícitamente y `downgrade()` lanza error). El único
rollback real ante pérdida de datos es **restaurar el dump**. `flask db
downgrade` sigue prohibido y `docker compose down -v` también.

---

## 4. Pre-chequeos ejecutados sobre producción (solo SELECT)

| Chequeo | Consulta | Resultado | Veredicto |
|---|---|---|---|
| Registros de nombres | `count(*)` en `personal`, `becario`, `investigador` | 6 + 6 + 5 = 17 | Informativo |
| Nombres nulos/vacíos | `nombre_apellido IS NULL OR trim(...)=''` | 0 | OK |
| Nombres fuera del mapa ISS-34 | 15 valores distintos comparados contra `NOMBRES` | **15 de 15 fuera** | **BLOQUEANTE** |
| Mails duplicados normalizados | `group by lower(trim(mail)) having count(*)>1` | 0 | OK |
| Mails a normalizar | `mail <> lower(trim(mail))` | 0 | OK |
| Distinciones sin UCT inferible | simulacro de los 3 pasos de `a6c8e0f2b4d6` | 0 (total: 1) | OK |
| Duplicados `(memoria_version_id, identidad_id)` | Personal, Becario, Investigador | 0 / 0 / 0 | OK |
| Tablas clave existentes | `identidad_personal` + 3 `*_memoria_version` | 4 | OK |

### 4.1 Valores que bloquean `d3f5a7c9e1b2`

```text
aaaa bbbbb
AAAAAAAAAAA LLLLLLLLLLLLL
Ana Lopez
cccc dddd                (3 filas en personal)
ddd  ssss
dddd  gggg
eeee ewwww
Juan Perez
Juana Goez
Juana Perez
prueba
test becario
test marce
Test marce apoyoo
ww ooo
```

El mapa de la migración contiene 131 correspondencias del dataset ficticio
revisado (ISS-34), pero ninguna de estas. El CHANGELOG del dev lo confirma:
*"El plan rechaza correspondencias desconocidas antes de escribir"*.

---

## 5. Bloqueantes y opciones

### 5.1 Bloqueante A — normalización de nombres

**Síntoma:** `migrate` falla con
`ISS-34: revisar correspondencia de personal #<id>; migracion cancelada.`

**Opciones:**

| Opción | Qué implica | Riesgo |
|---|---|---|
| **A1 (recomendada)** Upgrade escalonado: aplicar `c2e4a6b8d0f1`, cargar `nombre`/`apellido` de los 17 registros de prueba con un mapa aprobado, y luego aplicar el resto. `d3f5a7c9e1b2` salta las filas ya completas (`if registro["nombre"] and registro["apellido"]: continue`) | Cambia el nombre visible de 17 registros de prueba | Bajo y reversible desde el dump |
| A2 | Editar la migración para que omita valores desconocidos en vez de abortar | Divergencia con el dev; deja nombres nulos |
| A3 | Pedir al dev una release con migración tolerante | Demora la ventana |

**Mapa propuesto para A1** (los 17 registros son datos de prueba, no personas
reales):

| `nombre_apellido` actual | `nombre` | `apellido` |
|---|---|---|
| `aaaa bbbbb` | `aaaa` | `bbbbb` |
| `AAAAAAAAAAA LLLLLLLLLLLLL` | `AAAAAAAAAAA` | `LLLLLLLLLLLLL` |
| `Ana Lopez` | `Ana` | `Lopez` |
| `cccc dddd` | `cccc` | `dddd` |
| `ddd  ssss` | `ddd` | `ssss` |
| `dddd  gggg` | `dddd` | `gggg` |
| `eeee ewwww` | `eeee` | `ewwww` |
| `Juan Perez` | `Juan` | `Perez` |
| `Juana Goez` | `Juana` | `Goez` |
| `Juana Perez` | `Juana` | `Perez` |
| `prueba` | `prueba` | `prueba` |
| `test becario` | `test` | `becario` |
| `test marce` | `test` | `marce` |
| `Test marce apoyoo` | `Test marce` | `apoyoo` |
| `ww ooo` | `ww` | `ooo` |

### 5.2 Bloqueante B — configuración de correo y HTTPS

**Síntoma:** `create_app()` lanza
`Configure SMTP, URL publica y secretos de recuperacion antes de habilitar el
servicio` (o una de las validaciones siguientes) y `migrate`, `backend` y
`email-worker` no arrancan.

`validate_email_settings()` trata `staging` como productivo. Exige:

- `MAIL_SERVER`, `MAIL_DEFAULT_SENDER`, `PASSWORD_RESET_PUBLIC_URL`
- `EMAIL_OUTBOX_ENCRYPTION_KEY` (clave Fernet válida, 32 bytes)
- `PASSWORD_RESET_HMAC_KEY` (≥ 32 caracteres, independiente de los demás secretos)
- `SMTP_TLS_MODE` = `starttls` o `ssl`
- `PASSWORD_RESET_PUBLIC_URL` con esquema **https**, sin query/fragmento, con
  path terminado en `/restablecer-password`, y mismo `scheme:netloc` que algún
  origen de `FRONTEND_URLS`

**Opciones:**

| Opción | Qué implica | Riesgo |
|---|---|---|
| **B1 (recomendada para esta ventana)** Configurar SMTP real (Outlook 365, credenciales ya existentes en `.env.backup`), generar las dos claves, y declarar `PASSWORD_RESET_PUBLIC_URL=https://sgm.gidas.local/restablecer-password` agregando `https://sgm.gidas.local` a `FRONTEND_URLS`. La app sigue funcionando por HTTP; el enlace de recuperación **no será operativo hasta habilitar TLS** | Habilita la app y deja la feature documentada como no disponible | Bajo para el resto del sistema; requiere comunicar que recuperación queda pendiente |
| B2 | Montar TLS primero (Nginx de host + certificado) y recién después desplegar | Ventana más larga y cambio de URL de acceso |
| B3 | Excepción de código para permitir HTTP en staging | Divergencia de seguridad con el dev; no recomendada |

**Decisión recomendada:** A1 + B1. El despliegue queda verde, los usuarios siguen
entrando por HTTP como hoy y la recuperación de contraseña se habilita cuando
exista TLS.

---

## 6. Sincronización con el repositorio

| Elemento | Acción |
|---|---|
| Rama de integración | `release/v1.1.0-beta.2` (`f4f3a1c`) |
| Remoto de infraestructura | `origin` → `https://github.com/infraitgidas/sgm-gidas.git` |
| Tag propuesto | `v1.1.0-beta.2-infra.1` |
| Push | `git push origin release/v1.1.0-beta.2 && git push origin v1.1.0-beta.2-infra.1` |
| VM | `git fetch origin --tags && git checkout v1.1.0-beta.2-infra.1` |
| Repo del dev | No se toca durante la ventana. La integración se conserva en nuestro remoto |

La VM tiene 2 commits locales por delante de su `origin/main` viejo; el checkout
del tag nuevo deja ese historial accesible por SHA (`f800778`) para el rollback.

---

## 7. Plan de ejecución (resumen)

Todos los comandos se ejecutan en la VM salvo la Fase 0.

### Fase 0 — Integración y push (estación de trabajo)

```bash
git switch release/v1.1.0-beta.2
git tag -a v1.1.0-beta.2-infra.1 -m "Integracion v1.1.0-beta.2 para infraestructura"
git push origin release/v1.1.0-beta.2
git push origin v1.1.0-beta.2-infra.1
```

### Fase 1 — Punto de restauración (obligatorio)

1. Registrar estado: `git rev-parse HEAD`, alembic, `docker compose ps`, `df -h`.
2. Detener escritores: `stop backend migrate frontend frontend_sgm nginx`.
3. `pg_dump -Fc` a `/home/infra/gidas-backups/pre-upgrade-v1.1.0-beta.2-<TS>.dump`
   y verificar con `pg_restore --list` (> 75 objetos, > 0 bytes).
4. Snapshot del volumen con `db` detenida:
   `vol-pre-upgrade-v1.1.0-beta.2-<TS>.tar.gz` y verificar con `tar tzf`.
5. Copia externa por `scp` a `~/gidas-backups-externos/`.
6. Preservar imágenes actuales con tag `:pre-v1.1.0-beta.2`.
7. Drill de restauración en `gidas_drill` y borrar la base de prueba.

**Si la Fase 1 no termina en verde, no se continúa.**

### Fase 2 — Configuración de correo (B1)

Agregar a `backend/.env.production` (permisos `600`):

```env
MAIL_SERVER=smtp.office365.com
MAIL_PORT=587
MAIL_DEFAULT_SENDER=GIDAS <infrait@frlp.utn.edu.ar>
MAIL_USERNAME=infrait@frlp.utn.edu.ar
MAIL_PASSWORD=<desde /home/infra/gidas/.env.backup>
SMTP_TLS_MODE=starttls
SMTP_TIMEOUT_SECONDS=20
EMAIL_WORKER_POLL_SECONDS=5
EMAIL_OUTBOX_ENCRYPTION_KEY=<Fernet generada>
PASSWORD_RESET_HMAC_KEY=<aleatoria de 32+ caracteres>
PASSWORD_RESET_PUBLIC_URL=https://sgm.gidas.local/restablecer-password
```

Y en `FRONTEND_URLS` agregar `https://sgm.gidas.local` (mantener los orígenes
HTTP actuales). Actualizar `APP_VERSION=v1.1.0-beta.2`.

Generación de claves:

```bash
# Clave Fernet valida usando solo la libreria estandar
python3 -c "import base64,secrets; print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
# Clave HMAC de 48 caracteres
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

Las claves deben ser distintas entre sí y de `SECRET_KEY`, `JWT_SECRET` y
`REFRESH_SECRET`.

### Fase 3 — Upgrade escalonado de migraciones (A1)

```bash
# 1) Solo la migración que agrega las columnas
docker compose --env-file .env.production run --rm --no-deps \
  --entrypoint sh migrate -c "flask db upgrade c2e4a6b8d0f1"

# 2) Cargar nombre/apellido de los 17 registros (mapa aprobado, en transacción)
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -v ON_ERROR_STOP=1 <<'SQL'
BEGIN;
UPDATE personal SET nombre='cccc', apellido='dddd' WHERE nombre_apellido='cccc dddd';
UPDATE personal SET nombre='Juana', apellido='Perez' WHERE nombre_apellido='Juana Perez';
UPDATE personal SET nombre='prueba', apellido='prueba' WHERE nombre_apellido='prueba';
UPDATE personal SET nombre='Test marce', apellido='apoyoo' WHERE nombre_apellido='Test marce apoyoo';
UPDATE becario SET nombre='Ana', apellido='Lopez' WHERE nombre_apellido='Ana Lopez';
UPDATE becario SET nombre='dddd', apellido='gggg' WHERE nombre_apellido='dddd  gggg';
UPDATE becario SET nombre='eeee', apellido='ewwww' WHERE nombre_apellido='eeee ewwww';
UPDATE becario SET nombre='Juan', apellido='Perez' WHERE nombre_apellido='Juan Perez';
UPDATE becario SET nombre='test', apellido='becario' WHERE nombre_apellido='test becario';
UPDATE becario SET nombre='ww', apellido='ooo' WHERE nombre_apellido='ww ooo';
UPDATE investigador SET nombre='AAAAAAAAAAA', apellido='LLLLLLLLLLLLL' WHERE nombre_apellido='AAAAAAAAAAA LLLLLLLLLLLLL';
UPDATE investigador SET nombre='aaaa', apellido='bbbbb' WHERE nombre_apellido='aaaa bbbbb';
UPDATE investigador SET nombre='ddd', apellido='ssss' WHERE nombre_apellido='ddd  ssss';
UPDATE investigador SET nombre='Juana', apellido='Goez' WHERE nombre_apellido='Juana Goez';
UPDATE investigador SET nombre='test', apellido='marce' WHERE nombre_apellido='test marce';
COMMIT;
SQL

# 3) Verificar que no queden filas sin nombre/apellido
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc \
  "SELECT count(*) FROM (SELECT nombre,apellido FROM personal UNION ALL SELECT nombre,apellido FROM becario UNION ALL SELECT nombre,apellido FROM investigador) x WHERE nombre IS NULL OR apellido IS NULL;"
# Esperado: 0

# 4) Aplicar el resto y verificar el head
docker compose --env-file .env.production run --rm --no-deps \
  --entrypoint sh migrate -c "flask db upgrade"
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"
# Esperado: e8c2a4f6b0d1
```

### Fase 4 — Despliegue

```bash
git fetch origin --tags
git checkout v1.1.0-beta.2-infra.1
GIDAS_ALLOW_LAN_BIND=1 bash scripts/validate-vm-deployment.sh .env.production
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production up --build -d
docker compose --env-file .env.production ps -a
docker compose --env-file .env.production logs --tail=200 migrate
```

Criterios de éxito:

- `migrate` exit `0` y no queda corriendo.
- alembic `e8c2a4f6b0d1`.
- 7 servicios `healthy` (`frontend_sgm` no tiene healthcheck definido).
- `email-worker` arriba con heartbeat `/tmp/gidas-email-worker-heartbeat`.

### Fase 5 — Verificación

```bash
GIDAS_ALLOW_LAN_BIND=1 bash scripts/smoke-vm-deployment.sh .env.production
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/api/v1/health/live
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/api/v1/health/ready
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8080/sgm-gidas/
```

Prueba funcional mínima:

- Login, listado y detalle de proyectos.
- Memorias institucionales: reapertura y descarga Excel desde el listado.
- Formularios de Personal: Nombre y Apellido precargados.
- Distinciones: alta con proyecto opcional conservando UCT.
- Acceso LAN por `http://sgm.gidas.local:8080` y Portal `/sgm-gidas/`.
- **Recuperación de contraseña:** verificar que la pantalla existe y que el
  endpoint responde de forma controlada; el envío real queda pendiente de TLS.

### Fase 6 — Registro y cierre

Completar la tabla de registro (§9), actualizar `APP_VERSION`, y recién después
de la aceptación visual del usuario actualizar documentación técnica y
`CHANGELOG.md`.

---

## 8. Rollback

El procedimiento completo está en
`docs/despliegue_v1_1_0_beta_2_rollback.md`. Resumen:

| Situación | Ruta | Pérdida |
|---|---|---|
| Falló antes de aplicar migraciones | **R0** — volver a `f800778` y reconstruir | Ninguna |
| Migraciones aplicadas y datos corruptos | **R1** — código anterior + restore del dump | Lo creado desde el dump |
| Dump local corrupto | **R2** — snapshot del volumen | Lo creado desde el snapshot |
| Sin dump ni snapshot | **R3** — último semanal | Hasta 7 días |

**Prohibido en toda la ventana:** `flask db downgrade`, `docker compose down -v`,
restaurar sobre la base activa con escritores conectados.

---

## 9. Registro de la ventana

**Ejecutada el 2026-11-13.** El detalle completo con evidencia está en
`docs/despliegue_v1_1_0_beta_2_ejecucion.md`.

| Campo | Valor |
|---|---|
| Fecha / ventana | 2026-11-13 16:50 – 16:56 (UTC−3) |
| Commit anterior | `f800778` |
| Alembic anterior | `a7c9e2f4b6d8` |
| Tag desplegado | `v1.1.0-beta.2-infra.1` (`013ba97`) |
| Alembic nuevo | `e8c2a4f6b0d1` |
| Dump pre-upgrade | `pre-upgrade-v1.1.0-beta.2-20261113-165006.dump` (481 K, 1104 TOC) |
| Snapshot de volumen | `vol-pre-upgrade-v1.1.0-beta.2-20261113-165006.tar.gz` (9,1 M, 1754 archivos) |
| Copia externa | `~/gidas-backups-externos/` |
| Imágenes preservadas | `:pre-v1.1.0-beta.2` |
| Drill de restore | Sí — 88 tablas |
| `migrate` | Exit 0 |
| Smoke | Verde |
| Prueba funcional | Pendiente de aceptación del usuario |
| Recuperación de contraseña | Operativa por el túnel HTTPS (SMTP 235, ruta 200, request 202); URL estable pendiente |
| Rollback ejecutado | No |
| Incidentes | Sesión del Portal: cookie path + origen de túnel; corregido (ver ejecución §9) |

---

## 10. Checklist pre-ventana

- [ ] Aprobado el mapa de nombres (A1) y la opción de correo/HTTPS (B1).
- [ ] Rama `release/v1.1.0-beta.2` y tag `v1.1.0-beta.2-infra.1` pusheados.
- [ ] Ventana comunicada (post-cron de backups del sábado 03:00).
- [ ] Dump y snapshot generados, verificados y copiados fuera de la VM.
- [ ] Drill de restauración aprobado.
- [ ] Imágenes actuales preservadas con tag.
- [ ] Claves `EMAIL_OUTBOX_ENCRYPTION_KEY` y `PASSWORD_RESET_HMAC_KEY` generadas.
- [ ] Credenciales SMTP copiadas desde `.env.backup` sin exponerlas en logs.
- [ ] `APP_VERSION` actualizado.
- [ ] Espacio en disco > 2 G.
