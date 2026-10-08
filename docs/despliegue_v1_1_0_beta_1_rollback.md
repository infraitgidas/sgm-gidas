# Despliegue de v1.1.0-beta.1 en producción con rollback ante pérdida de datos

Runbook para actualizar la VM de producción (192.168.1.111) desde `ceee87d` hasta la release
`v1.1.0-beta.1` (`b8c1a81`, 2026-10-03), con un punto de restauración verificado y un
procedimiento de rollback si se pierden datos.

**Por qué existe este documento:** la release trae **22 migraciones nuevas**, varias de las
cuales **borran filas y columnas** al ejecutarse. Un `flask db downgrade` para volver atrás
**destruye datos**. Por eso el único rollback real ante pérdida de datos es restaurar desde un
dump verificado, y ese dump **se crea antes** de tocar nada.

Precedente: `docs/verificacion_release_v1_1_0_beta_1.md` (qué ajustes de infraestructura se
pierden y qué hay que preservar).

---

## Ruta rápida

1. **Preparar el código** — commitear los cambios de infraestructura locales y pushearlos, para
   que la VM pueda hacer `--ff-only`. (Fase 0)
2. **Crear el punto de restauración** — parar escritores, `pg_dump`, verificar con
   `pg_restore --list`, snapshot del volumen, copia fuera de la VM. (Fase 1)
3. **Preflight** — `scripts/validate-vm-deployment.sh`. (Fase 2)
4. **Actualizar** — `git checkout v1.1.0-beta.1` + `up --build -d`. (Fase 3)
5. **Verificar** — `migrate` exit 0 + `scripts/smoke-vm-deployment.sh`. (Fase 4)
6. Si algo falla → **árbol de decisión de rollback**. (Fase 5)

**Resultado esperado:** stack healthy, 6 servicios + `frontend_sgm` arriba, alembic en
`a7c9e2f4b6d8`, smoke en verde.

---

## Tabla de decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Rollback de datos | **Solo restore de dump** | Varios downgrades borran tablas con datos (ver §Riesgos) |
| `flask db downgrade` | **Prohibido en esta release** | 4 de 22 migraciones hacen `DELETE`/`DROP` en su rama inversa |
| Volumen PostgreSQL | **Nunca `docker compose down -v`** | `-v` borra `gidas_prod_postgres_data` y con él toda la base |
| Consistencia del dump | Parar escritores (`backend`, `migrate`) antes del `pg_dump` | Evita dump a medio escribir durante una transacción |
| Snapshot de volumen | Sí, además del dump, con la base detenida | Copia byte-a-byte: recupera aunque el dump esté corrupto |
| Copia fuera de la VM | Sí (`scp`) + el semanal que ya va por SMTP | La VM no es el único guardián de los datos |
| Código local sin commitear | Commitear y pushear **antes** de la ventana | Un `git pull` con working tree sucio en 6 archivos invita a resolver mal |
| Ventana | Sábado, después del cron de backup de las 03:00 | El dump semanal del día queda como respaldo adicional |

---

## Riesgos: por qué el downgrade no sirve

Estado actual de la BD en la VM: `alembic_version = 9823db81d6d2`.
Estado destino: `a7c9e2f4b6d8`. **Cadena lineal de 22 revisiones** nuevas.

Evidencia extraída de los archivos de migración de `origin/main`:

| Migración | Qué hace al avanzar (upgrade) | Qué hace al retroceder (downgrade) |
|---|---|---|
| `b12c8d5e7f90` limitar_autores | `DELETE FROM <tabla> WHERE personal_id IS NOT NULL` y `drop_column(personal_id)` | reconstruye la columna **vacía** |
| `c35e8a1b7d42` participaciones con becarios | `DELETE FROM participacion_relevante WHERE becario_id IS NOT NULL` | `DELETE` sobre la tabla |
| `d8f3a6c1b5e2` separar catálogo de visitas | `DELETE FROM visita_grupo`, `DELETE FROM visita_academica_memoria_version` | vuelve a `DELETE` |
| `f4b8c6d2e9a1` movimientos fuente equipamiento | `DELETE FROM movimiento_financiero` | **otro `DELETE`** sobre la misma tabla |
| `a85f1e2d3c4b` informes por período | crea `informe` / `informe_proyecto` / `informe_investigador` | `DELETE FROM auditoria_campo ...` y **`drop_table`** de las tres |
| `e3a7d9b2c4f1` movimiento financiero | crea `movimiento_financiero`, `categoria_erogacion`, `movimiento_memoria_version` | `drop_table` de las tres |
| `a12b9c4d6e80` generalizar autoría | crea tabla nueva y **`drop_table`** la anterior | recrea la anterior y borra la nueva |

**Lectura técnica:** varias migraciones son transformaciones destructivas (mover datos a una
tabla nueva y borrar la vieja, o eliminar filas que ya no cumplen una regla). Ejecutar el
`downgrade` equivalente **no devuelve los datos originales**: crea esquemas vacíos o borra lo
que se acaba de cargar. Alembic reporta éxito igual, porque el código del downgrade está
"correcto" — simplemente no es reversible en datos.

**En lenguaje simple:** volver atrás con Alembic es como deshacer una mudanza tirando a la
basura las cajas nuevas: el programa vuelve al estado anterior, pero la información que estaba
adentro no. Por eso **antes de mudar guardamos una copia completa de la casa**: el dump.

---

## Fase 0 — Preparar el código (estación de trabajo, antes de la ventana)

Objetivo: que la VM pueda subir con `git pull --ff-only` sin conflictos.

**Contexto actual** (verificado):

| | Local (workstation) | VM (192.168.1.111) | `origin/main` |
|---|---|---|---|
| HEAD | `ceee87d` + 2 commits | `ceee87d` | `b8c1a81` (289 adelante) |
| Commits sin pushear | `58c929f` (https en apt), `f0b85d4` (límites/imágenes) | 0 | — |
| Modificados sin commitear | 5 archivos Docker/nginx | **7 archivos** | — |
| Untracked crítico | docs/scripts | **`frontend/Dockerfile.portal`, `frontend/nginx.portal.conf`** | no existen |

### 0.1 En la estación de trabajo

```bash
git status                      # confirmar los 5 archivos modificados
git add backend/Dockerfile docker-compose.yml docker-compose.dev.yml \
          frontend/nginx.conf nginx/default.conf
git commit -m "chore(infra): tuning de recursos y fuentes apt por https"
git pull --rebase origin main   # resolver los 6 conflictos (ver tabla abajo)
git push origin main
```

Tabla de resolución de conflictos (`git pull --rebase origin main`):

| Archivo | Qué gana | Por qué |
|---|---|---|
| `backend/Dockerfile` | upstream + **re-agregar el `sed` de https** | upstream usa `--only-binary=:all:` (más limpio), pero le falta el fix del 403 |
| `docker-compose.yml` | upstream + **re-agregar el servicio `frontend_sgm`** y el tuning `768m`/`0.5` | upstream no conoce el Portal; los límites genéricos son para otra máquina |
| `docker-compose.dev.yml` | upstream | sus imágenes están mejor fijadas |
| `frontend/nginx.conf` | upstream + **agregar el bloque `gzip on`** | upstream tiene `gzip_static`; falta el gzip dinámico |
| `nginx/default.conf` | upstream | trae `map X-Forwarded-Proto`, timeouts y `no-cache` de `index.html` |
| `frontend/Dockerfile`, `main.tsx` | resolver línea a línea | upstream tiene mejoras; local agrega `VITE_BASE_PATH` |

> Los archivos `Dockerfile.portal` / `nginx.portal.conf` quedaron **untracked en la VM**, no en
> la workstation. **Commitearlos también** (ver 0.2) o van a quedar huérfanos para siempre.

### 0.2 En la VM (si se opta por subir la arquitectura del Portal desde la VM)

```bash
ssh infra@192.168.1.111
cd /home/infra/gidas
git add frontend/Dockerfile.portal frontend/nginx.portal.conf
git add -u                              # los 7 modificados
git commit -m "feat(frontend): arquitectura de dos frontends para Portal GIDAS"
git pull --rebase origin main
git push origin main
```

Si la VM no debe tener push, hacer 0.2 igual pero **sin** `git push`, y dejar el resultado
commiteado en `main` local de la VM para que el `--ff-only` de la Fase 3 funcione.

---

## Fase 1 — Punto de restauración (obligatorio, en la VM)

Todo este bloque se ejecuta **antes** de cambiar el código. Si no se completa, no se continúa.

### 1.1 Estado base y espacio

```bash
ssh infra@192.168.1.111
cd /home/infra/gidas

git log --oneline -1                 # registrar el commit desplegado
docker compose --env-file .env.production ps
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"
df -h /                              # esperado: ~29 G libres
ls -lh /home/infra/gidas-backups/
```

Esperado hoy: alembic `9823db81d6d2`, dumps semanales desde `20260828` (~391 KB).

### 1.2 Parar los escritores

```bash
docker compose --env-file .env.production stop backend migrate frontend frontend_sgm nginx
```

No se detiene `db` (sigue vivo para el dump) ni `redis`.

### 1.3 Dump lógico verificado

```bash
TS=$(date +%Y%m%d-%H%M%S)
DUMP=/home/infra/gidas-backups/pre-upgrade-v1.1.0-${TS}.dump

docker compose --env-file .env.production exec -T db \
  pg_dump -U gidas_admin -d gidas_db -Fc --no-owner --no-privileges > "$DUMP"

test -s "$DUMP" && ls -lh "$DUMP"
docker compose --env-file .env.production exec -T db \
  pg_restore --list < "$DUMP" | head -20
docker compose --env-file .env.production exec -T db \
  pg_restore --list < "$DUMP" | wc -l      # debe superar las 75 tablas
```

**Criterio de aceptación:** archivo no vacío, `pg_restore --list` sin errores y con más de 75
objetos. Si falla cualquiera de las tres, **abortar la ventana**.

### 1.4 Snapshot del volumen (copia byte-a-byte)

```bash
SNAP=vol-pre-upgrade-v1.1.0-${TS}.tar.gz
docker compose --env-file .env.production stop db

docker run --rm \
  -v gidas_prod_postgres_data:/from:ro \
  -v /home/infra/gidas-backups:/to \
  postgres:16.15-alpine \
  sh -c "tar czf /to/${SNAP} -C /from ."

ls -lh /home/infra/gidas-backups/${SNAP}
tar tzf /home/infra/gidas-backups/${SNAP} | head
```

Se usa la imagen `postgres:16.15-alpine` **ya presente en la VM**, así no dependemos de
descargar nada. La base está detenida: el snapshot es consistente.

### 1.5 Copia fuera de la VM

```bash
# desde la estación de trabajo
scp infra@192.168.1.111:/home/infra/gidas-backups/pre-upgrade-v1.1.0-*.dump \
    infra@192.168.1.111:/home/infra/gidas-backups/vol-pre-upgrade-v1.1.0-*.tar.gz \
    ~/gidas-backups-externos/
```

Además, el dump semanal ya sale por SMTP a `gidas@frlp.utn.edu.ar` e
`infra@frlp.utn.edu.ar` (cron sábado 03:00) → hay una copia adicional fuera de la VM sin
hacer nada.

### 1.6 (Recomendado) Drill de restauración

Un dump no es válido hasta que se restaura. Con ~391 KB el drill cuesta segundos:

```bash
cd /home/infra/gidas
docker compose --env-file .env.production start db

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d postgres \
  -c "DROP DATABASE IF EXISTS gidas_drill; CREATE DATABASE gidas_drill;"

docker compose --env-file .env.production exec -T db \
  pg_restore -U gidas_admin -d gidas_drill --no-owner --no-privileges < "$DUMP"

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d gidas_drill \
  -tAc "select count(*) from information_schema.tables where table_schema='public'"

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d postgres \
  -c "DROP DATABASE gidas_drill;"
```

Esperado: conteo similar al de producción. **No ejecutar restore sobre la base activa.**

---

## Fase 2 — Preflight

```bash
cd /home/infra/gidas
git pull --ff-only origin main
git log --oneline -1                       # debe ser b8c1a81 o posterior

bash scripts/validate-vm-deployment.sh .env.production
```

El preflight valida `docker compose config`, la topología de producción, secretos trackeados
y `nginx -t` con `nginxinc/nginx-unprivileged:1.31-alpine3.24` (la release ya actualizó esa
referencia).

Chequeos manuales adicionales antes de arrancar:

- [ ] `.env.production` contiene `NGINX_BIND_ADDRESS=0.0.0.0` (si no, el Portal deja de atender por LAN)
- [ ] `grep -c frontend_sgm docker-compose.yml` → distinto de 0 (si dio 0, se perdió el servicio en el merge)
- [ ] existen `frontend/Dockerfile.portal` y `frontend/nginx.portal.conf`
- [ ] el dump y el snapshot de la Fase 1 están verificados y con copia externa

---

## Fase 3 — Actualización

```bash
cd /home/infra/gidas
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production up --build -d
```

Compose espera a `db`, ejecuta `migrate` (`flask db upgrade` → 22 revisiones), y recién
después levanta `backend`, `frontend`, `frontend_sgm` y `nginx`.

```bash
docker compose --env-file .env.production ps -a
docker compose --env-file .env.production logs --tail=200 migrate
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"
```

**Criterios de éxito:**

- `migrate` termina con exit `0` y no queda corriendo
- `alembic_version` = `a7c9e2f4b6d8`
- todos los servicios en `healthy` (incluido `frontend_sgm`)

---

## Fase 4 — Verificación

```bash
cd /home/infra/gidas
bash scripts/smoke-vm-deployment.sh .env.production
```

El smoke valida: exit de `migrate`, `/api/v1/health/live`, `/api/v1/health/ready` y `/`.

Verificación funcional mínima (lista nueva de la release):

- [ ] Login con un usuario existente
- [ ] Listado de proyectos (PID) carga
- [ ] **Memorias institucionales** visible y creable (función nueva)
- [ ] Export del Excel de memorias genera archivo
- [ ] Portal en `http://192.168.1.43/sgm-gidas/` responde (arquitectura de dos frontends)
- [ ] Acceso LAN por `sgm.gidas.local:8080` sigue funcionando
- [ ] `docker compose --env-file .env.production ps` sin reinicios (`Restarting`)

Si hay cron de BCRA (nuevo en esta release): instalar después del smoke, no durante la ventana.

```bash
# opcional, una vez estable el despliegue — ver scripts/bcra-sync.cron.example
0 18 * * * /bin/sh /home/infra/gidas/scripts/run-bcra-sync.sh
```

---

## Fase 5 — Rollback

### 5.1 Árbol de decisión

| Situación detectada | Ruta | Pérdida de datos |
|---|---|---|
| `migrate` falló con exit ≠ 0 **y** `alembic_version` sigue en `9823db81d6d2` | **R0** — volver al código anterior | Ninguna |
| `migrate` OK, pero la app falla y los datos no se tocaron | **R0** (código) sin restore | Ninguna |
| Se ejecutaron las migraciones y hay datos corruptos, filas borradas o incoherencia | **R1** — código anterior + restore del dump | Se pierde lo creado **desde** el dump |
| El dump local está corrupto o falta | **R2** — snapshot de volumen | Se pierde lo creado desde el snapshot |
| No hay dump ni snapshot (no se hizo Fase 1) | **R3** — último dump semanal por SMTP o `gidas-initial-20260828` | Hasta 7 días de datos |

**Regla de oro:** ante la duda sobre los datos, **no** ejecutar `flask db downgrade`. Cerrar
el acceso, conservar volúmenes y logs, y restaurar.

### 5.2 R0 — Rollback solo de código (migraciones no aplicadas)

```bash
cd /home/infra/gidas
docker compose --env-file .env.production ps -a
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"

git checkout <COMMIT_ANTERIOR>     # ceee87d
docker compose --env-file .env.production up --build -d
bash scripts/smoke-vm-deployment.sh .env.production
```

Conservar los logs del `migrate` fallido antes de reconstruir:

```bash
docker compose --env-file .env.production logs migrate > /home/infra/gidas-backups/migrate-fallo-${TS}.log
```

### 5.3 R1 — Rollback con restauración de datos

Usar cuando las migraciones corrieron y hay pérdida o corrupción de datos.

**Paso 1 — cerrar escritura**

```bash
docker compose --env-file .env.production stop nginx backend migrate frontend frontend_sgm
```

**Paso 2 — volver el código al estado anterior**

```bash
git checkout <COMMIT_ANTERIOR>     # ceee87d
```

**Paso 3 — resetear el esquema y restaurar**

El dump previo **no contiene** las tablas nuevas que creó la release; por eso hay que vaciar
el esquema antes de restaurar, si no quedarían tablas huérfanas.

```bash
DUMP=/home/infra/gidas-backups/pre-upgrade-v1.1.0-<TS>.dump

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d gidas_db \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'

docker compose --env-file .env.production exec -T db \
  pg_restore -U gidas_admin -d gidas_db --no-owner --no-privileges < "$DUMP"

docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"
```

Esperado: `9823db81d6d2` (el valor que tenía la base antes de la ventana).

**Paso 4 — levantar y verificar**

```bash
docker compose --env-file .env.production up --build -d
bash scripts/smoke-vm-deployment.sh .env.production
```

`migrate` va a correr con el código viejo cuyo `head` también es `9823db81d6d2` → `flask db
upgrade` es un no-op, y luego reaplica `seed_roles` y los grants de mínimo privilegio.

**Paso 5 — verificar integridad funcional**

- [ ] Login OK
- [ ] Conteos clave (`usuarios`, `proyecto_investigacion`, tablas de memorias nuevas **ausentes**)
- [ ] `alembic_version` = `9823db81d6d2`
- [ ] Documentar el incidente **antes** de reabrir el servicio

### 5.4 R2 — Rollback desde el snapshot de volumen

Último recurso antes de ir al mail. Copia exacta del volumen, sin lógica intermedia.

```bash
SNAP=/home/infra/gidas-backups/vol-pre-upgrade-v1.1.0-<TS>.tar.gz

docker compose --env-file .env.production down       # SIN -v
docker run --rm \
  -v gidas_prod_postgres_data:/to \
  -v /home/infra/gidas-backups:/from \
  postgres:16.15-alpine \
  sh -c "rm -rf /to/* && tar xzf /from/$(basename "$SNAP") -C /to"

git checkout <COMMIT_ANTERIOR>
docker compose --env-file .env.production up --build -d
```

El snapshot se tomó con la base detenida y con el código viejo → el volumen y el código
quedan consistentes entre sí.

### 5.5 R3 — Desde una copia externa

```bash
scp ~/gidas-backups-externos/pre-upgrade-v1.1.0-*.dump infra@192.168.1.111:/home/infra/gidas-backups/
# (o descargar el dump semanal desde el adjunto del mail)
```

Luego repetir el paso 3 y 4 de R1.

---

## Checklist pre-ventana

- [ ] Fase 0 completa: infraestructura commiteada y pusheada, `origin/main` en `b8c1a81` o posterior
- [ ] `frontend_sgm`, `Dockerfile.portal` y `nginx.portal.conf` trackeados en el repo
- [ ] Ventana comunicada y horario elegido (post-cron de los sábados 03:00)
- [ ] Dump `pre-upgrade-v1.1.0-*` generado, verificado con `pg_restore --list`
- [ ] Snapshot de volumen generado y listado con `tar tzf`
- [ ] Copia externa (`scp`) realizada
- [ ] Drill de restauración en `gidas_drill` aprobado
- [ ] Commit desplegado registrado (`ceee87d`)
- [ ] Espacio en disco verificado (> 2 G)

## Checklist post-despliegue

- [ ] `migrate` exit `0`
- [ ] `alembic_version = a7c9e2f4b6d8`
- [ ] `scripts/validate-vm-deployment.sh` en verde
- [ ] `scripts/smoke-vm-deployment.sh` en verde
- [ ] `frontend_sgm` y acceso LAN por `sgm.gidas.local:8080` funcionando
- [ ] Flujo de memorias + export Excel probado
- [ ] `NGINX_BIND_ADDRESS=0.0.0.0` presente en `.env.production`
- [ ] Versión, fecha, operador y resultado registrados

## Checklist de rollback (preparación)

- [ ] Se conoce el commit anterior: `ceee87d`
- [ ] Ruta del dump y del snapshot anotadas en el registro de la ventana
- [ ] `flask db downgrade` NO ejecutado en ningún momento
- [ ] `docker compose down -v` NO ejecutado en ningún momento
- [ ] Logs del `migrate` conservados si algo falló

---

## Registro del despliegue

> Ejecutado el 2026-10-08: ver el registro completo con evidencia y desviaciones en
> `docs/despliegue_v1_1_0_beta_1_ejecucion.md`.

| Campo | Valor |
|---|---|
| Versión desplegada | `v1.1.0-beta.1` (`b8c1a81`) |
| Versión anterior | `ceee87d` |
| Fecha / ventana | |
| Operador | |
| Commit anterior en alembic | `9823db81d6d2` |
| Commit nuevo en alembic | `a7c9e2f4b6d8` |
| Migraciones aplicadas | 22 |
| Dump pre-upgrade | `pre-upgrade-v1.1.0-<TS>.dump` |
| Snapshot volumen | `vol-pre-upgrade-v1.1.0-<TS>.tar.gz` |
| Drill de restore | sí / no |
| Resultado del smoke | |
| Rollback ejecutado | no / R0 / R1 / R2 / R3 |
| Incidentes | |

---

## Qué NO hacer

- **No** ejecutar `flask db downgrade` para "deshacer" la release.
- **No** ejecutar `docker compose down -v` en ningún punto del proceso.
- **No** restaurar un dump sobre la base activa y con escritores conectados.
- **No** hacer `git pull` en la VM con el working tree sucio: primero commitear (Fase 0).
- **No** continuar la Fase 3 si la Fase 1 no terminó en verde.
- **No** borrar los dumps previos: la retención de `backup_db.sh` conserva 4 semanas, pero
  los `pre-upgrade-*` y `vol-pre-upgrade-*` se conservan **hasta cerrar** la ventana.

---

## Siguiente paso

Ejecutar la Fase 0 (commitear y pushear la infraestructura) y agendar la ventana de la
Fases 1-4.
