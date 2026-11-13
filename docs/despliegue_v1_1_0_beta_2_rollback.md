# Rollback del despliegue v1.1.0-beta.2

Procedimiento de recuperación para la ventana de actualización de la VM
**192.168.1.111** (`/home/infra/gidas`) desde `v1.1.0-beta.1` (`f800778`) hasta
`v1.1.0-beta.2` (`09e4e10`, tag `v1.1.0-beta.2-infra.1`).

El análisis y el plan están en `docs/despliegue_v1_1_0_beta_2_analisis.md`.

> **Ejecutado el 2026-11-13.** El registro completo está en
> `docs/despliegue_v1_1_0_beta_2_ejecucion.md`. Las 8 migraciones quedaron
> aplicadas (`e8c2a4f6b0d1`), por lo que **R0 ya no aplica**: ante cualquier
> problema de datos corresponde R1 y, si el dump falla, R2. El punto de
> restauración sigue disponible en `/home/infra/gidas-backups/`.

**Por qué el downgrade no es una opción:** la release trae 8 migraciones nuevas.
`d3f5a7c9e1b2` declara explícitamente que la normalización de nombres es
irreversible y su `downgrade()` lanza error. Otras migraciones agregan columnas
`NOT NULL` y restricciones. El único rollback real ante pérdida de datos es
**restaurar el dump verificado**, que se crea antes de tocar nada.

---

## Tabla de decisiones

| Tema | Decisión | Motivo |
|---|---|---|
| Rollback de datos | **Solo restore de dump o snapshot** | `d3f5a7c9e1b2` no se puede revertir |
| `flask db downgrade` | **Prohibido** | No devuelve datos; puede borrar filas |
| Volumen PostgreSQL | **Nunca `docker compose down -v`** | Borra `gidas_prod_postgres_data` |
| Consistencia del dump | Detener escritores antes de `pg_dump` | Evita dump a medio escribir |
| Snapshot de volumen | Sí, con `db` detenida | Recupera aunque el dump esté corrupto |
| Copia externa | Sí, por `scp` | La VM no es el único guardián |
| Working tree de la VM | Limpio antes de la ventana | El checkout del tag debe poder fallar limpio |

---

## Fase 1 — Punto de restauración (obligatorio)

### 1.1 Estado base y espacio

```bash
ssh infra@192.168.1.111
cd /home/infra/gidas

git rev-parse HEAD                 # esperado: f800778
git status --short                 # esperado: vacío
docker compose --env-file .env.production ps
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"
df -h /                            # esperado: > 2 G libres
ls -lh /home/infra/gidas-backups/
```

Registrar `HEAD` y `alembic_version` en el documento de análisis (§9).

### 1.2 Preservar las imágenes actuales

```bash
docker tag gidas-backend:latest        gidas-backend:pre-v1.1.0-beta.2
docker tag gidas-frontend:latest       gidas-frontend:pre-v1.1.0-beta.2
docker tag gidas-frontend_sgm:latest   gidas-frontend_sgm:pre-v1.1.0-beta.2
docker tag gidas-migrate:latest        gidas-migrate:pre-v1.1.0-beta.2
docker images | grep pre-v1.1.0-beta.2
```

### 1.3 Detener escritores

```bash
docker compose --env-file .env.production stop backend migrate frontend frontend_sgm nginx
```

`db` y `redis` siguen arriba.

### 1.4 Dump lógico verificado

```bash
TS=$(date +%Y%m%d-%H%M%S)
DUMP=/home/infra/gidas-backups/pre-upgrade-v1.1.0-beta.2-${TS}.dump

docker compose --env-file .env.production exec -T db \
  pg_dump -U gidas_admin -d gidas_db -Fc --no-owner --no-privileges > "$DUMP"

test -s "$DUMP" && ls -lh "$DUMP"
docker compose --env-file .env.production exec -T db \
  pg_restore --list < "$DUMP" | head -20
docker compose --env-file .env.production exec -T db \
  pg_restore --list < "$DUMP" | wc -l      # debe superar las 75 tablas
```

**Criterio de aceptación:** archivo no vacío, `pg_restore --list` sin errores y
más de 75 objetos. Si falla cualquiera, **abortar la ventana**.

### 1.5 Snapshot del volumen

```bash
SNAP=vol-pre-upgrade-v1.1.0-beta.2-${TS}.tar.gz
docker compose --env-file .env.production stop db

docker run --rm \
  -v gidas_prod_postgres_data:/from:ro \
  -v /home/infra/gidas-backups:/to \
  postgres:16.15-alpine \
  sh -c "tar czf /to/${SNAP} -C /from ."

ls -lh /home/infra/gidas-backups/${SNAP}
tar tzf /home/infra/gidas-backups/${SNAP} | head
docker compose --env-file .env.production start db
```

### 1.6 Copia fuera de la VM

Desde la estación de trabajo:

```bash
mkdir -p ~/gidas-backups-externos
scp infra@192.168.1.111:/home/infra/gidas-backups/pre-upgrade-v1.1.0-beta.2-*.dump \
    infra@192.168.1.111:/home/infra/gidas-backups/vol-pre-upgrade-v1.1.0-beta.2-*.tar.gz \
    ~/gidas-backups-externos/
ls -lh ~/gidas-backups-externos/
```

### 1.7 Drill de restauración

```bash
cd /home/infra/gidas

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d postgres \
  -c "DROP DATABASE IF EXISTS gidas_drill; CREATE DATABASE gidas_drill;"

docker compose --env-file .env.production exec -T db \
  pg_restore -U gidas_admin -d gidas_drill --no-owner --no-privileges < "$DUMP"

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d gidas_drill \
  -tAc "select count(*) from information_schema.tables where table_schema='public'"

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d postgres \
  -c "DROP DATABASE gidas_drill;"
```

**No restaurar sobre la base activa.**

---

## Fase 2 — Árbol de decisión

| Situación detectada | Ruta | Pérdida de datos |
|---|---|---|
| Falló el preflight, el build o el checkout del tag; no se aplicó ninguna migración | **R0** | Ninguna |
| Se aplicó solo `c2e4a6b8d0f1` y falló la carga de nombres | **R0** | Ninguna (columnas nuevas nullable) |
| Se aplicó parte de la cadena y `migrate` falló sin escribir datos | **R0** | Ninguna |
| Se aplicaron todas las migraciones y hay datos corruptos, filas borradas o incoherencia | **R1** | Lo creado desde el dump |
| El dump está corrupto o falta | **R2** | Lo creado desde el snapshot |
| No hay dump ni snapshot | **R3** | Hasta 7 días |

**Regla de oro:** ante la duda sobre los datos, **no** ejecutar
`flask db downgrade`. Cerrar el acceso, conservar volúmenes y logs, y restaurar.

---

## R0 — Rollback solo de código

Aplica cuando no se aplicaron migraciones o solo `c2e4a6b8d0f1` (columnas
nullable, inocuas para el código anterior).

```bash
cd /home/infra/gidas
docker compose --env-file .env.production ps -a
docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"

# Conservar logs del intento
docker compose --env-file .env.production logs migrate \
  > /home/infra/gidas-backups/migrate-fallo-$(date +%Y%m%d-%H%M%S).log

git checkout f800778
docker compose --env-file .env.production up --build -d
GIDAS_ALLOW_LAN_BIND=1 bash scripts/smoke-vm-deployment.sh .env.production
```

Si el código anterior usa `backend/.env.production`, los campos `MAIL_*` y las
claves nuevas son ignorados por la versión beta.1; no es necesario quitarlos.

**Criterio de aceptación:** alembic sigue en `a7c9e2f4b6d8` (o `c2e4a6b8d0f1`),
contenedores `healthy`, smoke en verde.

---

## R1 — Rollback con restauración de datos

Usar cuando se aplicaron las migraciones y hay pérdida o corrupción.

### Paso 1 — Cerrar escritura

```bash
docker compose --env-file .env.production stop nginx backend migrate frontend frontend_sgm
```

`email-worker` también debe detenerse si existe:

```bash
docker compose --env-file .env.production stop email-worker 2>/dev/null || true
```

### Paso 2 — Volver el código

```bash
git checkout f800778
```

### Paso 3 — Resetear el esquema y restaurar

El dump previo no contiene las tablas nuevas de la release; hay que vaciar el
esquema antes de restaurar.

```bash
DUMP=/home/infra/gidas-backups/pre-upgrade-v1.1.0-beta.2-<TS>.dump

docker compose --env-file .env.production exec -T db psql -U gidas_admin -d gidas_db \
  -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'

docker compose --env-file .env.production exec -T db \
  pg_restore -U gidas_admin -d gidas_db --no-owner --no-privileges < "$DUMP"

docker compose --env-file .env.production exec -T db \
  psql -U gidas_admin -d gidas_db -tAc "select version_num from alembic_version"
```

Esperado: `a7c9e2f4b6d8`.

> **Nota sobre permisos:** tras el restore, el esquema puede quedar sin los
> grants de `gidas_app`. El arranque de `migrate` con el código anterior
> reaplica `seed_roles.py` y `manage_database_roles.py grant`, por lo que el
> Paso 4 los restituye.

### Paso 4 — Levantar y verificar

```bash
docker compose --env-file .env.production up --build -d
GIDAS_ALLOW_LAN_BIND=1 bash scripts/smoke-vm-deployment.sh .env.production
```

`migrate` corre con el código viejo cuyo head es `a7c9e2f4b6d8` → `flask db
upgrade` es un no-op.

### Paso 5 — Verificar integridad funcional

- [ ] Login OK.
- [ ] Conteos clave: `usuario`, `proyecto_investigacion`, memorias.
- [ ] Tablas nuevas ausentes (`email_outbox`, `password_reset_request`).
- [ ] `alembic_version = a7c9e2f4b6d8`.
- [ ] Documentar el incidente **antes** de reabrir el servicio.

---

## R2 — Rollback desde el snapshot de volumen

Último recurso antes de la copia externa.

```bash
SNAP=/home/infra/gidas-backups/vol-pre-upgrade-v1.1.0-beta.2-<TS>.tar.gz

docker compose --env-file .env.production down       # SIN -v
docker run --rm \
  -v gidas_prod_postgres_data:/to \
  -v /home/infra/gidas-backups:/from \
  postgres:16.15-alpine \
  sh -c "rm -rf /to/* && tar xzf /from/$(basename "$SNAP") -C /to"

git checkout f800778
docker compose --env-file .env.production up --build -d
GIDAS_ALLOW_LAN_BIND=1 bash scripts/smoke-vm-deployment.sh .env.production
```

El snapshot se tomó con la base detenida y el código viejo → volumen y código
quedan consistentes.

---

## R3 — Desde una copia externa

```bash
scp ~/gidas-backups-externos/pre-upgrade-v1.1.0-beta.2-*.dump \
    infra@192.168.1.111:/home/infra/gidas-backups/
```

Luego repetir los pasos 3 y 4 de R1.

Alternativa: descargar el dump semanal adjunto del correo de las 03:00 del
sábado y restaurarlo con el mismo procedimiento.

---

## Qué NO hacer

- **No** ejecutar `flask db downgrade` para "deshacer" la release.
- **No** ejecutar `docker compose down -v` en ningún punto.
- **No** restaurar un dump sobre la base activa con escritores conectados.
- **No** hacer `git pull` o `checkout` en la VM con el working tree sucio.
- **No** continuar la Fase 4 si la Fase 1 no terminó en verde.
- **No** borrar los `pre-upgrade-*` ni los `vol-pre-upgrade-*` hasta cerrar la
  ventana y confirmar estabilidad.

---

## Checklist de preparación de rollback

- [ ] Commit anterior conocido: `f800778`.
- [ ] Dump y snapshot con ruta exacta anotados.
- [ ] Copia externa verificada.
- [ ] Drill de restauración aprobado.
- [ ] Imágenes `:pre-v1.1.0-beta.2` creadas.
- [ ] `flask db downgrade` NO ejecutado.
- [ ] `docker compose down -v` NO ejecutado.
- [ ] Logs de `migrate` conservados si algo falla.
