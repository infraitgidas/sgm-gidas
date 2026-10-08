# Índice de documentación de la release v1.1.0-beta.1

Mapa de toda la documentación relacionada con la actualización del sistema GIDAS a la versión
`v1.1.0-beta.1`, desplegada el 8 de octubre de 2026 en la VM de producción 192.168.1.111 y
verificada en verde (build, 22 migraciones, smoke, Portal y LAN). El objetivo del índice es que
cada lector encuentre rápido el documento que necesita, sin recorrer toda la carpeta `docs/`.

## Ruta rápida (3 lecturas)

1. `docs/dossier_direccion_gidas/mail_actualizacion_v1_1_0_beta_1.md`, nota de estado para la
   Dirección: qué pasó, qué cambia para el usuario y qué queda pendiente.
2. `docs/despliegue_v1_1_0_beta_1_ejecucion.md`, qué se hizo realmente en la ventana, con la
   evidencia y las desviaciones respecto del plan.
3. `docs/despliegue_v1_1_0_beta_1_rollback.md`, solo si algo falla: cómo volver al estado
   anterior sin perder datos.

---

## 1. Comunicaciones

| Documento | Qué contiene | Audiencia |
|---|---|---|
| `docs/dossier_direccion_gidas/mail_actualizacion_v1_1_0_beta_1.md` | Estado formal de la actualización para la Dirección: verificación, avisos de contraseña, pendientes | Dirección de GIDAS |
| `docs/comunicacion_dev_v1_1_0_beta_1.md` | Mensaje listo para el desarrollador: 2 ajustes faltantes de su código, nota sobre la versión del frontend, lo que funcionó, decisiones y sincronización de repos, con la tabla anexa de 11 puntos. Separa lo que es responsabilidad de infraestructura de lo que es responsabilidad de desarrollo | Desarrollo (Benjamín Briones) |

La comunicación al desarrollador deja claro qué es nuestro (estrategia de despliegue, acceso
LAN, preflight, imágenes y backups) y qué es suyo (código, releases y decisiones de su feature).

## 2. Estrategia y responsabilidades

| Documento | Qué contiene | Audiencia |
|---|---|---|
| `docs/estrategia_despliegue_portal_lan.md` | Estrategia de despliegue y acceso (Portal / LAN): arquitectura de acceso, gates de validación, release y rollback, política de repos y tabla de responsabilidades entre desarrollo e infraestructura | Infraestructura GIDAS (interno) + dev (solo lectura) |

## 3. Verificación y despliegue

| Documento | Qué contiene | Audiencia |
|---|---|---|
| `docs/verificacion_release_v1_1_0_beta_1.md` | Verificación punto por punto de la release contra el código real y la VM: 11 ajustes, qué llegó y qué no | Coordinación de infraestructura, desarrollo |
| `docs/despliegue_v1_1_0_beta_1_ejecucion.md` | Registro de la ventana del 2026-10-08: punto de restauración, conflictos resueltos, desviaciones, evidencias y pendientes | Coordinación de infraestructura, operación |
| `docs/despliegue_v1_1_0_beta_1_rollback.md` | Runbook de actualización con rollback ante pérdida de datos: fases, tabla de decisiones, riesgos de las migraciones destructivas y árbol de decisión | Operación, guardia |

## 4. Antecedentes del despliegue

| Documento | Qué contiene | Audiencia |
|---|---|---|
| `docs/despliegue_20260827.md` | Registro del despliegue productivo del 27 de agosto de 2026: incidencia de build por fuentes apt/HTTPS, optimizaciones y alias DNS | Operación |
| `docs/despliegue_produccion.md` | Guía operativa de despliegue manual con Docker Compose: arranque, verificación, operación cotidiana y recuperación | Operación |
| `docs/despliegue_entrega_direccion.md` | Documento de entrega a la Dirección: estado del sistema, vías de acceso, servicios activos y pendientes | Dirección de GIDAS |
| `docs/revision_seguridad_despliegue.md` | Matriz de controles de seguridad para despliegue (HTTPS, JWT, CORS, rate limiting, secretos) con bloqueantes y checklist | Seguridad, infraestructura |
| `docs/analisis_docker_produccion.md` | Auditoría de Dockerfiles y Docker Compose: buenas prácticas verificadas, hallazgos priorizados y plan de remediación | Infraestructura, desarrollo |

## 5. Operación

| Documento | Qué contiene | Audiencia |
|---|---|---|
| `docs/backups_semanal_gidas.md` | Backup semanal de la base de datos con envío por correo, retención y procedimiento de restauración | Operación |
| `docs/configuracion_manual_pendiente.md` | Variables de configuración pendientes y secretos que deben renovarse, con verificación posterior | Operación, seguridad |
| `docs/ci_cd.md` | Estado de la integración continua: validación por pull request, convención de commits y entrega manual por SSH | Desarrollo, infraestructura |
| `scripts/validate-vm-deployment.sh` | Preflight de la VM: compose, topología, secretos y nginx interno (requiere `GIDAS_ALLOW_LAN_BIND=1` para binding LAN) | Operación, guardia |
| `scripts/smoke-vm-deployment.sh` | Smoke test post-despliegue: migrate, liveness, readiness y frontend | Operación, guardia |
| `scripts/backup_db.sh` + `scripts/send_mail.py` | Dump de la base y envío del backup por SMTP | Operación |
| `scripts/run-bcra-sync.sh` + `scripts/bcra-sync.cron.example` | Sincronización de cotizaciones BCRA y ejemplo de cron (18:00 AR), disponibles desde `v1.1.0-beta.1` y aún no instalados | Operación |
| `docs/bcra_sincronizacion_tipos_cambio.md` | Qué hace la sincronización de tipos de cambio del BCRA: API y serie usadas, variables de entorno, tabla `tipo_cambio`, cómo instalar el cron (ruta corregida), cómo verificarla y decisiones pendientes | Operación, desarrollo |
| `docs/backups_semanal_gidas.md` | Backup semanal con envío por correo: proceso, archivos, restauración y **sección 10 con la verificación del 2026-10-08 post-upgrade** (cron, SMTP, dump y mail de prueba) | Operación |

## 6. Seguimiento y tareas

| Documento | Qué contiene | Audiencia |
|---|---|---|
| `tasks/finished/auth-refresh-cookie-http-only.md` | Cookie de refresh en httpOnly | Seguimiento |
| `tasks/finished/backend-excepciones-dominio-tipadas.md` | Excepciones de dominio tipadas en backend | Seguimiento |
| `tasks/finished/backend-respuestas-error-seguras.md` | Respuestas de error sin filtrar información sensible | Seguimiento |
| `tasks/finished/backend-security-nginx-rate-limit.md` | Rate limiting de seguridad en nginx | Seguimiento |
| `tasks/finished/frontend-calidad-seguridad.md` | Calidad y seguridad de frontend | Seguimiento |
| `tasks/finished/frontend-code-splitting.md` | División de código en frontend | Seguimiento |
| `tasks/finished/frontend-security-audit.md` | Auditoría de seguridad de frontend | Seguimiento |
| `tasks/finished/search-verificacion-recuperacion-real.md` | Verificación de búsqueda y recuperación reales | Seguimiento |
| `tasks/pendient/security-roadmap.md` | Hoja de ruta de seguridad pendiente | Seguimiento, seguridad |

---

## Próximo paso

Pendientes abiertos tras la ventana: decidir con desarrollo la instalación del cron de BCRA
(hoy no está instalado y `tipo_cambio` tiene 0 filas), confirmar la primera corrida automática
de backups sobre la versión nueva (sábado 11/10, 03:00, ver `backup.log`), y revisar el resto
de tareas en `tasks/pendient/`. La verificación manual de la cadena de backups y su envío por
correo quedó hecha el 2026-10-08 (incluye un mail de prueba con el dump post-upgrade).
