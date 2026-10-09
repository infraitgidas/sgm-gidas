---
id: ci-cd-snapshot-a-verificacion
title: Automatizar el despliegue desde snapshot en Proxmox hasta verificacion de release
status: pendient
area: infraestructura
module: ci-cd
priority: alta
risk_level: medio-alto
execution_order: 5
created_at: 2026-10-08
updated_at: 2026-10-09
source: despliegue-v1.1.0-beta.1
commit_sugerido: "docs(ci): plan de automatizacion de snapshot a verificacion"
owner: coordinator-agent
blocked_by: []
related_tasks:
  - security-roadmap
  - infra-ci-cd-pipeline-produccion
---

# Objetivo

Convertir el despliegue manual de releases en un pipeline por fases con gates, desde la
deteccion de una tag nueva en el repo del dev hasta la verificacion en produccion o el
rollback, incluyendo el snapshot previo en Proxmox. El plan completo, con arquitectura,
tabla de gates y riesgos, vive en `docs/plan_ci_cd_automatizacion.md`. Esta tarea absorbe
el punto 4 del roadmap (`CI/CD de seguridad`, referenciado en
`tasks/pendient/security-roadmap.md` como `infra-ci-cd-pipeline-produccion`).

Reglas duras heredadas del runbook `docs/despliegue_v1_1_0_beta_1_rollback.md`: nunca
`flask db downgrade`, nunca `docker compose down -v`, nunca restaurar sobre la base activa.

# Subtareas y orden de ejecucion

## 1. Gates estaticos de release (Fase 1)

- Estado: **pendiente**. Es el punto de partida: no depende de Proxmox ni toca produccion.
- Objetivo: detectar una tag `v*` en el repo del dev y validarla sin riesgo.
- Entregable: `scripts/release-gates.sh` que emite un informe `pass/fail`.
- Criterios de aceptacion:
  - [ ] Deteccion de tag nueva con `git ls-remote --tags dev` (sin credenciales).
  - [ ] Codigo bajado a rama `release/vX` en `origin`, sin tocar `main`.
  - [ ] Una sola head de Alembic verificada.
  - [ ] Busqueda de migraciones destructivas en `backend/migrations/versions/`, cubriendo SQL
        textual y la API de Alembic (`op.drop_table`, `op.drop_column`), con la rama
        `downgrade()` marcada como bloqueo y la `upgrade()` como informativa. Referencia:
        15 de 22 destructivas en `v1.1.0-beta.1` (40 de 54 en el historico).
  - [ ] Diff de `backend/.env.example` y `.env.example` contra `.env.production`.
  - [ ] `docker compose --env-file .env.production config --quiet`.
  - [ ] Suite backend con `python -m unittest discover -s tests -v` (misma bateria de
        `docs/ci_cd.md`).
- Dependencias: ninguna.
- Riesgo: ninguno en produccion.

## 2. Requisitos y decisiones de infraestructura (Fase 0)

- Estado: **cerrada el 2026-10-09**. Desbloquea la subtarea 3.
- Objetivo: cerrar los puntos marcados como requisito a confirmar en la seccion 7 del plan.
- Entregable: requisitos confirmados y decisiones registradas en
  `docs/plan_ci_cd_automatizacion.md`.
- Criterios de aceptacion:
  - [x] Acceso a Proxmox por consola SSH y por la interfaz web (confirmado 2026-10-08).
  - [x] Host de Proxmox, VMID y metodo de snapshot definidos: `192.168.1.13` (`pve-desa03`),
        VMID **230**, `qm snapshot 230 <nombre>` por SSH desde la estacion.
  - [x] PBS definido: no instalado; el snapshot queda solo en el hypervisor.
  - [x] Dónde corre el orquestador: **estacion de trabajo**; migra a una CT en el mismo Proxmox
        en la Fase 6 (la clave SSH hacia 192.168.1.13 solo esta en la estacion).
  - [x] Runner u orquestador en la VM de produccion: **no se permite**; la VM solo recibe
        comandos por SSH desde la estacion.
  - [x] Salida a internet hacia GitHub verificada el 2026-10-09 desde los dos candidatos:
        `https://github.com` responde 200 y `git ls-remote --tags` devuelve `v1.1.0-beta.1` sin
        credenciales desde la estacion y desde la VM.
  - [x] Ventana de mantenimiento y destinatarios de informes definidos: sabado 08:00-12:00 AR
        (tope 4 h) y los tres buzones (`gidas@`, `infra@`, `infrait@frlp.utn.edu.ar`).
  - [x] Criterio de tag estable: las `v*-beta.*` no se despliegan solas; el polling avisa y
        esperan aprobacion manual.
  - [x] Clave SSH de root hacia Proxmox: **deuda aceptada** para la Fase 2 (600, solo en la
        estacion); se reemplaza por usuario dedicado o token de API con `VM.Snapshot` en la
        Fase 6.
- Dependencias: ninguna. Cerrada el 2026-10-09.

## 3. Snapshot en Proxmox y respaldo pre-upgrade (Fase 2)

- Estado: **pendiente**. Desbloqueada: la subtarea 2 quedo cerrada el 2026-10-09 (orquestador en
  la estacion, ventana definida y clave SSH a Proxmox disponible). La parte de datos puede
  avanzarse en paralelo.
- Objetivo: punto de restauracion en dos capas antes de tocar nada.
- Entregable: script de pre-upgrade que ejecuta snapshot + dump + copia externa con
  verificacion.
- Criterios de aceptacion:
  - [ ] Snapshot de la VM creado y verificado con `qm snapshot 230 <nombre>` por SSH desde la
        estacion (metodo definido el 2026-10-09).
  - [ ] Dump `pg_dump -Fc` no vacio, `pg_restore --list` sin errores.
  - [ ] Tar del volumen listable con `tar tzf`.
  - [ ] Copia externa en la estacion de trabajo confirmada.
  - [ ] Drill de restauracion en `gidas_drill` aprobado.
- Dependencias: subtarea 2 (Proxmox); secuencia de Fase 1 de
  `docs/despliegue_v1_1_0_beta_1_rollback.md` ya probada en produccion.

## 4. Pipeline de despliegue idempotente (Fase 3)

- Estado: **pendiente**. Bloqueada por las subtareas 1 y 3.
- Objetivo: reemplazar el paso manual con un unico script reproductible.
- Entregable: `scripts/deploy-release.sh <tag>`.
- Criterios de aceptacion:
  - [ ] Tag de imagenes previas `:pre-<tag>`.
  - [ ] Preflight con `GIDAS_ALLOW_LAN_BIND=1 bash scripts/validate-vm-deployment.sh
        .env.production`.
  - [ ] `docker compose --env-file .env.production up --build -d`.
  - [ ] Gates: `migrate` exit 0, `alembic_version` igual al head del manifest del repo,
        `scripts/smoke-vm-deployment.sh .env.production` y HTTP 200 en las 4 URLs
        (`/api/v1/health/live`, `/`, `/sgm-gidas/` y `http://192.168.1.111:8080/`).
  - [ ] Chequeo de datos (conteo de usuarios) sin exponer credenciales en logs.
  - [ ] Idempotencia: dos corridas seguidas sobre la misma tag sin efectos adversos.
- Dependencias: subtareas 1 y 3.

## 5. Rollback automatico por gates (Fase 4)

- Estado: **pendiente**. Bloqueada por la subtarea 4 y por al menos un drill de la
  subtarea 8.
- Objetivo: que el pipeline elija R0, R1, R2 o R3 segun el gate fallido.
- Entregable: seccion de rollback en `deploy-release.sh` o `scripts/rollback-release.sh`.
- Criterios de aceptacion:
  - [ ] Gate fallido antes de migrar revierte solo imagenes (R0).
  - [ ] Gate fallido despues de migrar deriva a dump pre-upgrade (R1) o snapshot (R2).
  - [ ] Escrituras de usuarios detectadas tras migrar derivan a decision humana.
  - [ ] Referencia al runbook incluida y "NUNCA" explicito en el script y en la documentacion.
  - [ ] Logs del `migrate` fallido conservados antes de cualquier reconstruccion.
- Dependencias: subtarea 4.

## 6. Verificacion post-deploy y cierre (Fase 5)

- Estado: **pendiente**. Bloqueada por la subtarea 4.
- Objetivo: cerrar cada ventana con evidencia y notificacion.
- Entregable: verificacion automatizada, registro en `docs/registros/` e informe por mail.
- Criterios de aceptacion:
  - [ ] Smoke y los 4 chequeos HTTP en verde.
  - [ ] Checks de contenido: portal, LAN, login con usuario de prueba propio y tablas nuevas
        (`tipo_cambio`, `login_attempt`).
  - [ ] Version confirmada por tag de imagen y `APP_VERSION` (brecha del frontend documentada
        en `docs/estrategia_despliegue_portal_lan.md`).
  - [ ] Registro generado en `docs/registros/despliegue-<tag>.md`.
  - [ ] Mail de cierre enviado a los tres buzones con `scripts/send_mail.py` (exit 0). Ojo:
        exit 0 prueba aceptacion del SMTP, no entrega; la entrega se confirma en el buzon
        (`docs/backups_semanal_gidas.md`, seccion 11).
  - [ ] Puntos post-deploy listados (cron de BCRA sin instalar, cron semanal de backup).
- Dependencias: subtarea 4.

## 7. Disparador y orquestacion (Fase 6)

- Estado: **pendiente**. Se habilita despues de varias corridas manuales del pipeline.
- Objetivo: detectar tags nuevas y ejecutar las fases sin intervencion diaria.
- Entregable: job de cron (o servicio) con polling, filtros, lock e informes.
- Criterios de aceptacion:
  - [ ] Polling con `git ls-remote --tags dev` contra la ultima tag desplegada.
  - [ ] Filtro de tags estables (`v*`) con criterio documentado para betas: las `v*-beta.*` NUNCA
        se despliegan solas; el polling avisa y esperan aprobacion manual (definido 2026-10-09).
  - [ ] Ventana horaria definida: sabado 08:00-12:00 AR, tope 4 h (evita el cron de backup de las
        03:00).
  - [ ] Lock contra despliegues simultaneos.
  - [ ] Corrida en modo "solo informe" antes de habilitar el despliegue real.
- Dependencias: subtareas 4, 5 y 6; ventana definida en la subtarea 2.

## 8. Ejercicios y verificacion de la cadena de backup (Fase 7)

- Estado: **pendiente**. Frecuencia mensual, continua desde el primer dump automatizado.
- Objetivo: comprobar que los respaldos restauran cuando hacen falta.
- Entregable: registro de drill en `docs/registros/`.
- Criterios de aceptacion:
  - [ ] Drill desde dump y desde snapshot del volumen (y desde snapshot de Proxmox si
        existe).
  - [ ] Cadena semanal verificada: cron del sabado 03:00, `Dump ok` y `Email enviado ok` en
        `backup.log`, retencion de 4 semanas, y **confirmacion de entrega** en los tres buzones
        (`docs/backups_semanal_gidas.md`, secciones 10 y 11). `Email enviado ok` solo prueba
        aceptacion del SMTP.
  - [ ] Direccion del cron (`/home/infra/scripts/backup_db.sh`) unificada al script del repo
        o diff en cero.
- Dependencias: subtarea 3.

# Criterio de cierre de la tarea

- [ ] Las 8 subtareas en estado cerrado con evidencia vinculada.
- [ ] Una release real desplegada de punta a punta con el pipeline y registrada en
      `docs/registros/`.
- [ ] Un rollback ejecutado (al menos simulado) siguiendo el arbol de decision.
- [ ] `docs/plan_ci_cd_automatizacion.md` actualizado con lo aprendido y con los requisitos
      de Proxmox resueltos o marcados como descartados.
- [ ] `docs/ci_cd.md` actualizado para reflejar la etapa de CD nueva.
- [ ] Commit por modulo, sin cambios mezclados.

# Proximo paso

- [x] Requisitos y decisiones de la Fase 0 cerrados el 2026-10-09 (subtarea 2).
- [ ] Publicar el plan y esta tarea en `origin/main`.
- [ ] Arrancar la subtarea 1 (gates estaticos), ejecutable hoy sin respuestas pendientes.
