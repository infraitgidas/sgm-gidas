# Plan de automatización y CI/CD: de snapshot en Proxmox a verificación de release

Este plan convierte la actualización manual de la VM de producción en un pipeline por fases con
gates explícitos: parte de una tag nueva que aparece en el repo del dev y termina con la release
verificada en producción o revertida, incluyendo el snapshot previo en Proxmox y el respaldo de
datos. Cada fase declara objetivo, entregable, gates de salida, riesgos y esfuerzo estimado. Los
requisitos de la Fase 0 quedaron confirmados el **2026-10-09** (sección 7): nada de lo que este
plan da por hecho sigue pendiente de respuesta.

## Ruta rápida

1. Fase 0 **cerrada** el 2026-10-09: requisitos y decisiones confirmados (sección 7). El punto de
   partida es la Fase 1, que no depende de Proxmox ni toca producción.
2. Fase 1: gates estáticos de la release. Falla un gate, no se continúa.
3. Fase 2: snapshot en Proxmox + dump lógico verificado + copia externa.
4. Fase 3: `deploy-release.sh` idempotente (preflight, migrate, smoke, HTTP 200).
5. Fase 4: si un gate falla, árbol de decisión de rollback. Nunca `flask db downgrade`, nunca
   `docker compose down -v`.
6. Fase 5: verificación post-deploy, registro automático en el repo e informe por mail.
7. Fase 6: orquestador con polling de tags. Fase 7: drill mensual de restauración.

---

## 1. Objetivo y alcance

Automatizar de punta a punta el ciclo "aparece una tag `v*` en el repo del dev" hasta "release
verificada en producción o rollback ejecutado", cubriendo la detección, la validación estática, el
snapshot previo en Proxmox, el respaldo de datos, el despliegue, los gates de verificación, el
registro y la notificación. Quedan fuera del alcance: cambios en el código de la aplicación, la
escritura de migraciones (las escribe desarrollo) y el contenido de las releases. Referencias de
origen: `docs/estrategia_despliegue_portal_lan.md` y `docs/ci_cd.md`.

## 2. Estado actual

Estado verificado al 2026-10-08.

| Paso del ciclo | Hoy | Qué ya existe | Qué falta |
|---|---|---|---|
| Detección de release | Manual: alguien mira el repo del dev | `git ls-remote --tags dev` funciona sin credenciales (verificado) | Job de polling y criterio de tag estable |
| Sincronización de código | Manual, con 3 a 6 conflictos por merge | Runbook de resolución en `docs/despliegue_v1_1_0_beta_1_ejecucion.md` | Rama `release/vX` y gates de merge |
| Validación estática | Parcial | `scripts/validate-vm-deployment.sh`, `docker compose config --quiet`, CI en PR (`.github/workflows/ci.yml`) | Una sola head de Alembic, detección de migraciones destructivas, diff de `.env.example`, tests como gate de release |
| Snapshot previo | Manual, en la ventana; ya hay dos a mano en Proxmox (`inicio`, `upgradeV1_1_0_beta_1`) | Dump `pg_dump -Fc` + tar del volumen + copia externa (`docs/despliegue_v1_1_0_beta_1_rollback.md`, Fase 1) | Automatizar el snapshot con `qm snapshot 230` y verificarlo en cada ventana |
| Respaldo semanal | Automático y verificado | Cron sábado 03:00 + SMTP (`docs/backups_semanal_gidas.md`, sección 10) | El cron apunta a `/home/infra/scripts/backup_db.sh`, una copia fuera del repo |
| Despliegue | Manual: `up --build -d` con banderas | Preflight `GIDAS_ALLOW_LAN_BIND=1`, compose render | Script único idempotente `deploy-release.sh` |
| Verificación | Semi-manual | `scripts/smoke-vm-deployment.sh`, 4 chequeos HTTP hechos a mano | Los 4 HTTP y el conteo de usuarios como gate automático |
| Versión desplegada | No se puede confirmar desde la UI | `APP_VERSION` en el log del backend y tags de `docker images` | El frontend no reporta release (sin `VITE_APP_VERSION` ni `/version`) |
| Rollback | Manual, guiado por runbook | Árbol de decisión R0 a R3 en `docs/despliegue_v1_1_0_beta_1_rollback.md` | Decisión automática según el gate fallido |
| Registro y aviso | Manual en `docs/` | Plantilla de registro en el runbook, `scripts/send_mail.py` verificado con `/home/infra/gidas/.env.backup` | Registro en `docs/registros/` e informe de cierre automático |

## 3. Arquitectura propuesta

**Decisión clave:** el runner hospedado de GitHub Actions no alcanza `192.168.1.111` (LAN
privada). Sin un componente dentro de la LAN, no hay forma de ejecutar preflight, `docker compose`
ni `pg_dump` desde la nube.

| Opción | Qué implica | Ventajas | Limitaciones |
|---|---|---|---|
| **A. Self-hosted runner en la LAN** | Instalar el runner de GitHub Actions en una máquina de la LAN y correr los jobs ahí | Experiencia nativa de Actions, visibilidad en PR, aprobaciones por environment | Secretos de infra en GitHub, servicio propio a mantener, si el runner corre en la VM de producción el pipeline pasa a tener acceso directo a prod, dependencia de la nube para disparar |
| **B. Orquestador local por cron** | Un job en la VM o en la estación que hace polling con `git ls-remote`/`gh`, recibe la orden y ejecuta las fases 1 a 5 localmente | Sin dependencia de la nube en el camino crítico, cero secretos en GitHub, corre junto a docker, psql y el host de Proxmox, arranca hoy con cron y bash | Sin visibilidad central, hay que construir locking, logs e informes a mano, un solo host como punto de ejecución |
| **C. Actions en nuestro repo con `repository_dispatch`** | El detecto dispara `repository_dispatch` en `infraitgidas/sgm-gidas` y un workflow corre en runner propio | Auditoría en GitHub, gates con environment y revisores | Es A más el dispatch: sigue necesitando runner en la LAN, secretos en GitHub y dos piezas móviles; el beneficio aparece recién con varios revisores |

**Recomendación:** empezar por **B** y evolucionar a **A** cuando el pipeline esté estable.
Razones: B no pone credenciales de infraestructura en GitHub (condición que `docs/ci_cd.md` fija
expresamente), no depende de la nube para desplegar, es la opción más simple de operar y de
auditar con el esquema actual de una sola VM. A se adopta después, cuando justifique el costo de
un servicio de runner y la revisión de la política de secretos. C queda descartado por ahora.

| Estado | Detalle |
|---|---|
| Decidido en este plan | Orden de fases, gates obligatorios, reglas duras (nunca downgrade, nunca `down -v`), B como arquitectura inicial, Fase 1 como punto de partida |
| Resuelto el 2026-10-09 | Host y VMID de Proxmox y método de snapshot (SSH `qm`), PBS, dónde vive el orquestador (estación), sin runner en la VM de producción, ventana de mantenimiento (sábado 08:00–12:00, tope 4 h), destinatarios de los informes (los tres buzones) y criterio de tag estable (prerelease con aprobación manual) |

## 4. Fases del plan

### Fase 0: requisitos y decisiones

**Estado:** **cerrada el 2026-10-09.** Requisitos y decisiones confirmados; el detalle está en la
sección 7.

**Objetivo:** cerrar todo lo que el plan da por confirmar antes de automatizar nada.

**Entregable:** lista de requisitos completada en este documento (sección 7) y decisiones
registradas.

**Decisiones tomadas (2026-10-09):**

| Punto | Decisión |
|---|---|
| Orquestador | Corre en la **estación de trabajo** (la clave SSH a Proxmox sólo existe ahí). Migra a una **CT en el mismo Proxmox** en la Fase 6 |
| Runner en la VM de producción | **No**. La VM sólo recibe comandos por SSH |
| Ventana de mantenimiento | **Sábado 08:00–12:00 AR, tope 4 h**, comunicada |
| Destinatarios de los informes | `gidas@frlp.utn.edu.ar`, `infra@frlp.utn.edu.ar`, `infrait@frlp.utn.edu.ar` |
| Criterio de tag estable | Tags `v*`; las **prerelease `v*-beta.*` nunca se despliegan solas**: esperan aprobación manual |
| Clave SSH de `root` a Proxmox | **Deuda aceptada para la Fase 2** (600, sólo en la estación); se reemplaza por usuario dedicado o token de API con `VM.Snapshot` en la Fase 6 |

**Gates de salida:**

- [x] Host de Proxmox, VMID y método de snapshot definidos: `192.168.1.13` (`pve-desa03`),
      VMID **230**, `qm snapshot` por SSH desde la estación.
- [x] PBS definido: **no está instalado**; el snapshot queda sólo en el hypervisor.
- [x] Definido dónde corre el orquestador: estación de trabajo (CT en Proxmox en la Fase 6).
- [x] Secretos con ubicación y permisos definidos, fuera del repo (sección 6), con la deuda de
      la clave de `root` aceptada para la Fase 2.
- [x] Ventana de mantenimiento definida y comunicada: sábado 08:00–12:00 AR, tope 4 h.

**Riesgos:** que la espera por respuestas frene la Fase 1. Mitigación: la Fase 1 no depende de
Proxmox y se puede ejecutar en paralelo. **Riesgo residual:** la clave de `root` del hypervisor
viaja en el orquestador hasta la Fase 6.

**Esfuerzo:** 2 a 8 horas de trabajo, más la espera de coordinación. **Cumplido el 2026-10-09.**

### Fase 1: gates estáticos de release

**Objetivo:** detectar y validar una release sin tocar producción. Es la fase más barata y de
cero riesgo en prod.

**Entregable:** script de gates (por ejemplo `scripts/release-gates.sh`) que emite un informe
`pass/fail`; la continuidad depende sólo de ese informe.

**Qué valida:**

- Detección de la tag nueva en el repo del dev (`git ls-remote --tags dev`, sin credenciales) y
  criterio de tag estable (`v*`, descartando prerelease si el criterio lo indica).
- Código bajado a una rama `release/vX` en nuestro repo (`origin`), sin modificar `main`.
- Merge resuelto sin marcadores de conflicto y sin claves YAML duplicadas.
- Una sola head de Alembic (`alembic heads` con cardinalidad 1).
- Migraciones destructivas: búsqueda estática en `backend/migrations/versions/` del SQL textual
  (`DELETE`, `TRUNCATE`, `DROP TABLE`/`DROP COLUMN`) **y** de la API de Alembic
  (`op.drop_table`, `op.drop_column`), distinguiendo la rama `upgrade()` (informativo) de la
  rama `downgrade()` (bloquea y requiere revisión humana). Motivo: `flask db downgrade` está
  prohibido porque **15 de las 22 migraciones desplegadas en `v1.1.0-beta.1`** tienen
  `downgrade()` destructivo (conteo verificado el 2026-10-08 sobre `main`; el runbook decía 4,
  cifra que sólo contaba SQL textual y por eso subestimaba el riesgo). Histórico completo:
  40 de 54.
- Diff de `backend/.env.example` y `.env.example` contra `.env.production` para detectar variables
  nuevas requeridas.
- `docker compose --env-file .env.production config --quiet` sobre la rama candidata.
- Suite del backend (`python -m unittest discover -s tests -v`) y, si se decide incluirla, la
  batería de frontend (`npm test`, `npm run typecheck`, `npm run build`), tal como lista
  `docs/ci_cd.md`.

**Gates de salida:**

- [ ] Informe `pass/fail` generado con detalle por check.
- [ ] Una sola head de Alembic confirmada.
- [ ] Lista de migraciones con `downgrade()` destructivo revisada por una persona.
- [ ] Variables de entorno nuevas identificadas y `.env.production` actualizado antes de continuar.

**Riesgos:** falsos positivos en el grep de migraciones (muchas hacen `DELETE` legítimo en el
`upgrade`). Mitigación: informar por rama, no fallar en bloqueo automático sobre `upgrade()`.

**Esfuerzo:** 6 a 12 horas.

### Fase 2: snapshot en Proxmox y respaldo de datos pre-upgrade

**Objetivo:** tener el punto de restauración antes de tocar nada, en dos capas (hipervisor y
datos) y con la cadena ya verificada.

**Entregable:** script de pre-upgrade que toma el snapshot y ejecuta el respaldo de datos con
verificación.

**Qué ejecuta:**

- Snapshot de la VM de producción (VMID 230) en `pve-desa03` (`192.168.1.13`) con
  `ssh root@192.168.1.13 qm snapshot 230 pre-<tag>`, desde la estación, que es donde hoy está
  la clave. Verificar con `qm listsnapshot 230`. Sin PBS, el snapshot no sale del host.
- Dump lógico con la secuencia ya usada en la ventana: parar escritores (`backend`, `migrate`,
  `frontend`, `frontend_sgm`, `nginx`), `pg_dump -Fc`, verificación con `pg_restore --list`, tar
  del volumen con `db` detenida y copia externa por `scp` (runbook, Fase 1).

**Gates de salida (si alguno falla, no se despliega):**

- [ ] Snapshot de Proxmox creado, con tamaño y fecha verificados (a confirmar el método: API o
      interfaz).
- [ ] Dump no vacío, `pg_restore --list` sin errores y con la cantidad esperada de objetos
      (1104 objetos TOC en la última verificación).
- [ ] Tar del volumen listable con `tar tzf`.
- [ ] Copia externa en la estación de trabajo confirmada.
- [ ] (Recomendado) drill de restauración en `gidas_drill` aprobado.

**Riesgos:** asumir que el snapshot de Proxmox existe sin poder probarlo. Mitigación: hasta que
se confirmen host y VMID, el script se limita al dump + volumen, que ya funcionaron, y lo marca
como pendiente.

**Esfuerzo:** 6 a 12 horas, de los cuales la parte de datos ya está probada en producción.

### Fase 3: pipeline de despliegue idempotente

**Objetivo:** reemplazar el paso manual con un único script que puede re-ejecutarse sin dañar.

**Entregable:** `scripts/deploy-release.sh <tag>` que reproduce el flujo de la ventana manual.

**Qué ejecuta, en orden:**

1. Tag de las imágenes previas (`:pre-<tag>`).
2. Preflight con `GIDAS_ALLOW_LAN_BIND=1 bash scripts/validate-vm-deployment.sh .env.production`
   y `docker compose --env-file .env.production config --quiet`.
3. `docker compose --env-file .env.production up --build -d`.
4. Gates posteriores: exit 0 del contenedor `migrate`, `alembic_version` igual al head esperado
   guardado en un manifest del repo (propuesta: `scripts/release-manifest.env` con `TAG`, `COMMIT`
   y `ALEMBIC_HEAD`), `bash scripts/smoke-vm-deployment.sh .env.production` y HTTP 200 en las 4
   URLs (`/api/v1/health/live`, `/`, `/sgm-gidas/` y `http://192.168.1.111:8080/`).
5. Chequeos de datos: conteo de usuarios y hash de contraseñas sin exponerlos en el log, para
   detectar pérdida de filas tras migraciones destructivas.

**Transparencia de la ventana:** durante `up --build -d` la aplicación no está disponible (el
proxy y los frontends se reconstruyen). La ventana manual de `v1.1.0-beta.1` duró 3 h 19 min
(06:55 a 10:14 UTC) incluyendo la resolución de conflictos; el pipeline automatizado elimina esa
parte, pero el tiempo real de bloqueo debe medirse en la primera corrida, no suponerse.

**Gates de salida:**

- [ ] El script corre dos veces seguidas sobre la misma tag sin efectos adversos (idempotencia).
- [ ] `migrate` en exit 0 y `alembic_version` igual al manifest.
- [ ] Smoke en verde y HTTP 200 en las 4 URLs.
- [ ] Logs de cada paso conservados junto al registro de la ventana.

**Riesgos:** que un script monolítico oculte un fallo intermedio. Mitigación: `set -eu`, un gate
por paso, y salida explícita indicando en qué fase se detuvo.

**Esfuerzo:** 12 a 24 horas.

### Fase 4: rollback automático por gates

**Objetivo:** que la decisión de reversión la tome el pipeline según el gate fallido, siguiendo el
árbol de decisión existente.

**Entregable:** sección de rollback dentro de `deploy-release.sh` (o `scripts/rollback-release.sh`)
que elige entre R0, R1, R2 y R3.

| Situación | Acción | Referencia |
|---|---|---|
| Gate falló antes de migrar (preflight, build, `migrate` con exit != 0 y `alembic_version` sin moverse) | **R0**: volver a las imágenes `:pre-<tag>` y al commit anterior, sin tocar datos | Runbook, §5.2 |
| Gate falló después de migrar y hay datos sospechosos | **R1**: código anterior + restore del dump pre-upgrade | Runbook, §5.3 |
| Dump local corrupto o ausente | **R2**: snapshot del volumen (y snapshot de Proxmox si está disponible) | Runbook, §5.4 |
| Sin dump ni snapshot | **R3**: último dump semanal por SMTP o `gidas-initial-20260828` | Runbook, §5.5 |
| Las migraciones corrieron y ya se escribieron datos de usuarios | Decisión humana: se conservan los logs, se cierra el acceso y se escala al coordinador | Runbook, §5.1 |

**NUNCA en ningún punto:**

- `flask db downgrade` (15 de las 22 migraciones de esta release destruyen datos en su
  `downgrade()`; 40 de 54 en el histórico. Conteo verificado el 2026-10-08).
- `docker compose down -v` (borra el volumen `gidas_prod_postgres_data`).
- Restaurar un dump sobre la base activa con escritores conectados.

**Gates de salida:**

- [ ] Cada rama del árbol probada al menos una vez en un entorno no productivo o simulada con
      comandos de sólo lectura.
- [ ] Los logs del `migrate` fallido se conservan antes de cualquier reconstrucción.
- [ ] El runbook `docs/despliegue_v1_1_0_beta_1_rollback.md` queda referenciado desde el script.

**Riesgos:** automatizar un restore sin haber hecho drill. Mitigación: la Fase 4 no se activa en
automático hasta que la Fase 7 apruebe al menos un drill.

**Esfuerzo:** 8 a 16 horas.

### Fase 5: verificación post-deploy y cierre

**Objetivo:** cerrar la ventana con evidencia, no con impresión.

**Entregable:** verificación automatizada, registro en el repo e informe por mail.

**Qué ejecuta:**

- `scripts/smoke-vm-deployment.sh .env.production` y los 4 chequeos HTTP (incluye la dirección de
  la LAN, que el smoke actual no cubre).
- Checks de contenido: portal `/sgm-gidas/`, acceso LAN, login con un usuario de prueba creado
  para la ocasión (sin depender de credenciales reales en el pipeline) y presencia de los datos
  nuevos de la release (por ejemplo `tipo_cambio` y `login_attempt`, que existen desde
  `v1.1.0-beta.1`).
- Versión desplegada: como el frontend no reporta release (brecha conocida en
  `docs/estrategia_despliegue_portal_lan.md`), se confirma con el tag de las imágenes y con
  `APP_VERSION` en el log del backend.
- Registro automático en `docs/registros/despliegue-<tag>.md` con la plantilla del runbook
  (versión, commit, alembic, gates, resultado, operador o disparador).
- Informe de cierre con `scripts/send_mail.py` usando `/home/infra/gidas/.env.backup`
  (SMTP Office365, 587 STARTTLS, ya verificado).

**Gates de salida:**

- [ ] Smoke en verde y 4 respuestas HTTP 200.
- [ ] Checks de contenido en verde.
- [ ] Registro generado en `docs/registros/`.
- [ ] Mail de informe enviado a los tres buzones (`exit 0`). Ojo: `exit 0` prueba **aceptación
      del SMTP**, no entrega; la entrega se confirma mirando el buzón (lección del 2026-10-09,
      `docs/backups_semanal_gidas.md`, sección 11).
- [ ] Puntos post-deploy de la release detectados y listados (por ejemplo: cron de BCRA, hoy no
      instalado según `docs/bcra_sincronizacion_tipos_cambio.md`, y el cron semanal de backup).

**Riesgos:** dependencia de credenciales de prueba. Mitigación: usuario de prueba de baja
privilegia, creado y borrado dentro de la ventana.

**Esfuerzo:** 8 a 16 horas.

### Fase 6: disparador y orquestación

**Objetivo:** que el pipeline corra sin que nadie tenga que acordarse.

**Entregable:** job de cron (o servicio equivalente) que detecta tags, decide y ejecuta.

**Qué hace:**

- Polling periódico con `git ls-remote --tags dev` (verificado sin credenciales) contra la última
  tag desplegada, registrada en el manifest.
- Filtro: sólo tags `v*` estables, salvo orden explícita. Las betas se despliegan con la misma
  ruta pero con aprobación manual previa.
- Ejecuta Fases 1 a 5 en orden y aborta en el primer gate en rojo.
- Notificación por mail al empezar (inicio de ventana) y al terminar (informe de la Fase 5).
- Ventana horaria definida (2026-10-09): **sábado 08:00–12:00 AR, tope 4 h**. Evita el sábado
  03:00 del cron de backup semanal (`docs/backups_semanal_gidas.md`, sección 6) y acota la
  duración al orden de la ventana manual de `v1.1.0-beta.1` (3 h 19 min).
- Lock para que no corran dos despliegues a la vez.

**Gates de salida:**

- [ ] Detección probada con una tag de prueba.
- [ ] Lock efectivo ante dos ejecuciones simultáneas.
- [ ] Corrida de prueba completa en modo "sólo informe" antes de habilitar el despliegue real.
- [ ] Confirmado que la VM o la estación tiene salida a internet para alcanzar GitHub.

**Riesgos:** que el polling dispare en horario inadecuado o con la VM ocupada. Mitigación: ventana
horaria, lock y modo informe previo.

**Esfuerzo:** 6 a 12 horas.

### Fase 7: ejercicios

**Objetivo:** que los respaldos sigan sirviendo cuando hagan falta.

**Entregable:** ejecución mensual con evidencia.

**Checklist mensual:**

- [ ] Drill de restauración desde el dump en `gidas_drill` (procedimiento del runbook, Fase 1.6).
- [ ] Drill de restauración desde el snapshot del volumen, y desde el snapshot de Proxmox
      (tomado por SSH o por la interfaz).
- [ ] Verificación de la cadena de backup semanal: cron del sábado 03:00, `Dump ok` y
      `Email enviado ok` en `backup.log`, retención de 4 semanas.
- [ ] Verificación de que el cron apunta al script del repo o de que el diff entre
      `/home/infra/scripts/backup_db.sh` y `scripts/backup_db.sh` está en cero (deuda detectada en
      `docs/backups_semanal_gidas.md`, sección 10).
- [ ] Registro del drill en `docs/registros/`.

**Riesgos:** ninguno para producción (los drills son sobre copias).

**Esfuerzo:** 4 horas por corrida mensual.

## 5. Tabla de gates

| Gate | Qué valida | Dónde corre | Si falla |
|---|---|---|---|
| Detección de tag | Existe tag `v*` nueva en el repo del dev | Orquestador (Fase 6) | Aviso y reintento en la próxima corrida |
| Rama `release/vX` | Merge sin conflictos ni YAML duplicado | Orquestador (Fase 1) | Bloquea |
| Una sola head de Alembic | Cardinalidad de `alembic heads` igual a 1 | Orquestador (Fase 1) | Bloquea |
| Migraciones destructivas | `downgrade()` con `DELETE`/`DROP`/`TRUNCATE` | Orquestador (Fase 1) | Bloquea hasta revisión humana |
| Diff de entorno | `backend/.env.example` contra `.env.production` | Orquestador (Fase 1) | Bloquea |
| Compose render | `docker compose config --quiet` | Orquestador (Fase 1) | Bloquea |
| Suite de tests | `unittest` backend (+ frontend si se incluye) | Orquestador (Fase 1) | Bloquea |
| Snapshot de Proxmox | Snapshot creado y verificable | Proxmox (Fase 2) | Bloquea el despliegue |
| Dump pre-upgrade | No vacío, `pg_restore --list` OK, copia externa | VM (Fase 2) | Bloquea el despliegue |
| Preflight | Compose, topología, secretos, `nginx -t` | VM (Fase 3) | Bloquea, no se construye |
| `migrate` exit 0 | Contenedor de migraciones sin error | VM (Fase 3) | Rollback R0 |
| `alembic_version` | Head igual al manifest de la release | VM (Fase 3) | R0 si no hubo escrituras; si no, escala a R1 con decisión humana |
| Smoke | Liveness, readiness, frontend | VM (Fase 3) | Según árbol: R0 o R1 |
| HTTP 200 en 4 URLs | API, app, Portal y LAN | VM (Fase 3) | Rollback o aviso según alcance |
| Checks de contenido | Portal, LAN, login de prueba, tablas nuevas | VM (Fase 5) | Rollback o aviso con decisión humana |
| Registro y mail | Evidencia escrita e informe enviado | Orquestador (Fase 5) | Aviso, el despliegue ya quedó registrado en log |
| Cadena de backup semanal | Cron, dump, email, retención | VM (Fase 7) | Aviso y deuda operativa |

## 6. Seguridad y secretos

| Secreto o permiso | Dónde vive | Regla |
|---|---|---|
| Clave SSH hacia el host de Proxmox (`root@192.168.1.13`) | Sólo en la estación de trabajo; permisos `600` | **Deuda aceptada el 2026-10-09 para la Fase 2:** es clave de `root`, con privilegio total sobre el hypervisor. Se reemplaza por usuario dedicado o token de API con `VM.Snapshot` en la Fase 6, junto con el CT del orquestador |
| Token de API de Proxmox | Sólo si se elige la vía API en vez de SSH | Archivo `600` fuera del repo, privilegio mínimo `VM.Snapshot` |
| Credenciales SMTP | `/home/infra/gidas/.env.backup`, permisos `600`, ya verificado | Nunca en el repo, cubierto por `.gitignore` |
| `.env.production` | VM, fuera de git | Nunca versionado; el preflight ya escanea secretos trackeados con `backend/tools/scan_tracked_secrets.py` |
| Credenciales en GitHub | No existen hoy y no se agregan mientras la arquitectura sea B | Si más adelante se elige A, revisar antes la política de secretos |
| Credenciales SSH o de API de la app en el pipeline | Sólo si se usan, en archivos `600` del orquestador | Nunca en argumentos de línea de comandos ni en logs |

Auditabilidad: cada corrida del pipeline deja (quién o qué la disparó, tag, commit, gates y
resultado) en `docs/registros/` y en el mail de cierre. El orquestador corre en la estación de
trabajo y opera la VM por SSH como el usuario `infra`, de modo que los comandos quedan en sus
logs.

Destinatarios de los informes (definido el 2026-10-09): `gidas@frlp.utn.edu.ar`,
`infra@frlp.utn.edu.ar` e `infrait@frlp.utn.edu.ar`, los tres ya validados en el canal de backup
(`SMTP_TO` en `/home/infra/gidas/.env.backup`).

## 7. Requisitos a confirmar con el coordinador

Cierre de la Fase 0: **todo confirmado el 2026-10-09.** El detalle de las decisiones está en la
Fase 0.

- [x] Acceso a Proxmox: por consola SSH y por la interfaz web (2026-10-08).
- [x] Host de Proxmox: `192.168.1.13` (`pve-desa03`, PVE 8.4.19); se llegó por SSH con clave
      desde la estación de trabajo.
- [x] VMID de la VM de producción: **230** (`sgm-gidas`, 4 GB RAM, 40 GB).
- [x] PBS: **no instalado**. Los snapshots quedan sólo en el hypervisor, sin copia fuera del
      host.
- [x] Método de snapshot: `qm snapshot 230 <nombre>` por SSH al host. Ya existen dos tomados a
      mano: `inicio` (2026-08-28) y `upgradeV1_1_0_beta_1` (2026-10-08, ventana del upgrade).
- [x] Dónde vive el orquestador: **estación de trabajo**; en la Fase 6 migra a una CT en el mismo
      Proxmox. Dato que lo decidió: la clave SSH hacia `192.168.1.13` sólo está en la estación.
- [x] Runner u orquestador dentro de la VM de producción: **no se permite**. La VM sólo recibe
      comandos por SSH desde la estación.
- [x] Salida a internet hacia GitHub (necesaria para el polling): verificada el 2026-10-09 desde
      los dos candidatos. `https://github.com` responde 200 desde la estación y desde la VM
      (0.39 s), y `git ls-remote --tags https://github.com/BrionesBenjamin22/SGM-GIDAS` devuelve
      la tag `v1.1.0-beta.1` sin credenciales desde ambas.
- [x] Tolerancia a la ventana de mantenimiento: sábado **08:00–12:00 AR**, tope **4 h**. La
      ventana manual de `v1.1.0-beta.1` duró 3 h 19 min.
- [x] Destinatarios de los informes de inicio, cierre y rollback:
      `gidas@frlp.utn.edu.ar`, `infra@frlp.utn.edu.ar` e `infrait@frlp.utn.edu.ar` (los tres
      validados en el canal SMTP el 2026-10-09).
- [x] Criterio de tag estable: se siguen tags `v*`; las prerelease `v*-beta.*` **no** se
      despliegan automáticamente: el polling las reporta y esperan aprobación manual.
- [x] Clave SSH de `root` hacia Proxmox: **deuda aceptada** para la Fase 2 (vive sólo en la
      estación, permisos `600`, documentada en la sección 6). Reemplazo por usuario dedicado o
      token de API con privilegio `VM.Snapshot` en la Fase 6.

## 8. Hoja de ruta resumida

| Orden | Fase | Por qué en este orden | Esfuerzo |
|---|---|---|---|
| 1 | Fase 1: gates estáticos | Bajo riesgo, alto valor, no necesita Proxmox ni toca prod | 6 a 12 h |
| 2 | Fase 0: requisitos | **Cerrada el 2026-10-09**: desbloquea la Fase 2 | 2 a 8 h (cumplido) |
| 3 | Fase 2: snapshot y respaldo | Reduce el riesgo de la primera ventana automatizada | 6 a 12 h |
| 4 | Fase 3: despliegue idempotente | Reemplaza el paso manual con gates | 12 a 24 h |
| 5 | Fase 4: rollback por gates | Depende de la Fase 3 y de drills previos | 8 a 16 h |
| 6 | Fase 5: verificación y cierre | Cierra la evidencia de cada ventana | 8 a 16 h |
| 7 | Fase 6: orquestación | Sólo después de varias corridas manuales del pipeline | 6 a 12 h |
| 8 | Fase 7: ejercicios | Continuo, desde que exista el primer dump automatizado | 4 h/mes |

Esfuerzo total estimado: entre 52 y 100 horas de infraestructura (aproximadamente 7 a 13 días
hábiles), sin contar los drills mensuales. La espera de la Fase 0 ya no aplica: quedó cerrada el
2026-10-09.

## 9. Próximo paso

1. **Hecho:** la tarea y sus subtareas viven en `tasks/pendient/ci-cd-snapshot-a-verificacion.md`.
2. **Hecho:** los requisitos de la sección 7 quedaron confirmados el 2026-10-09.
3. Publicar este plan y la tarea en `origin/main`.
4. Arrancar la Fase 1 (gates estáticos): `scripts/release-gates.sh` con su informe `pass/fail`.

## Referencias

- `docs/despliegue_v1_1_0_beta_1_ejecucion.md`: evidencia de la última ventana manual y desviaciones.
- `docs/despliegue_v1_1_0_beta_1_rollback.md`: árbol de decisión de rollback y reglas duras.
- `docs/backups_semanal_gidas.md`: cadena de backup semanal verificada (sección 10).
- `docs/estrategia_despliegue_portal_lan.md`: reparto dev e infraestructura, gates y política de repos.
- `docs/ci_cd.md`: estado actual del CI y condiciones para un CD futuro.
- `docs/bcra_sincronizacion_tipos_cambio.md`: ejemplo de feature con programación a cargo de infraestructura.
- `scripts/validate-vm-deployment.sh`, `scripts/smoke-vm-deployment.sh`, `scripts/backup_db.sh`,
  `scripts/send_mail.py`: gates y herramientas existentes.
