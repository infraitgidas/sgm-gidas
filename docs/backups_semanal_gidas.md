# Backup y restauración de la base de datos GIDAS UCT

**Área:** InfraIT GIDAS
**Fecha de implementación:** 2026-08-28
**Estado:** AUTOMATIZADO y verificado (backup semanal + envío por email)

---

## 1. Resumen

Se automatizó el **backup semanal** de la base de datos PostgreSQL de GIDAS y su
**envío por email** (adjunto) a los responsables. El proceso genera un dump
*postgres-custom* del volumen de datos, aplica una política de retención y lo
despacha por SMTP a Outlook 365.

**Entregables de la automatización:**
- Script de backup: `/home/infra/scripts/backup_db.sh`
- Script de envío: `/home/infra/scripts/send_mail.py`
- Configuración secreta: `/home/infra/gidas/.env.backup` (permisos `600`)
- Programación: `crontab` del usuario `infra` (sábados 03:00)

---

## 2. Esquema del proceso

```
cron (sáb 03:00)
   └─► backup_db.sh
         ├─► docker compose exec db pg_dump -Fc  →  gidas-weekly-<fecha>.dump
         ├─► retención (conserva últimas 4 semanas)
         └─► send_mail.py <dump>  →  SMTP smtp.office365.com:587 (STARTTLS)
                                      → gidas@frlp.utn.edu.ar, infra@frlp.utn.edu.ar,
                                        infrait@frlp.utn.edu.ar
```

---

## 3. Archivos

| Archivo | Ubicación | Rol |
|---|---|---|
| `backup_db.sh` | `/home/infra/scripts/` (VM) · `scripts/` (repo local) | Genera el dump, retención, dispara envío |
| `send_mail.py` | `/home/infra/scripts/` (VM) · `scripts/` (repo local) | Envía por SMTP adjunto |
| `.env.backup` | `/home/infra/gidas/` (VM) · `scripts/` (repo local, gitignored) | Credenciales SMTP y configuración |

---

## 3bis. Backup inicial de referencia (post-despliegue)

Se generó y envió un **snapshot inicial** de referencia, posterior a la puesta en
producción y la corrección del frontend (error TDZ). Sirve como punto de partida
antes de que la BD crezca con datos reales de operación.

- **Dump:** `/home/infra/gidas-backups/gidas-initial-20260828-113530.dump` (~388 KB)
- **Formato:** `PostgreSQL custom database dump - v1.15-0`
- **Envido por email** a `gidas@frlp.utn.edu.ar` e `infra@frlp.utn.edu.ar`
  (asunto "Backup INICIAL BBDD GIDAS (referencia post-despliegue)"), exit `0`.
- **Contenido:** mismo baseline verificado (8 usuarios, 3 roles, 1 UCT).

---

## 4. Script de backup (`backup_db.sh`)

Genera el dump desde el contenedor `db` del stack:

```bash
docker compose --env-file .env.production exec -T db \
    pg_dump -U gidas_admin -d gidas_db -Fc \
    --no-owner --no-privileges > <backup_dir>/gidas-weekly-<fecha>.dump
```

- Estructura `-Fc` (custom): comprimido, permite `pg_restore` selectivo.
- `--no-owner --no-privileges`: portabilidad al restaurar.
- **Retención:** conserva las últimas `RETENTION_WEEKS` (default `4`) y purga las
  más antiguas vía `find`.
- Si se pasa `--no-mail` genera solo el dump, sin enviar.

---

## 5. Script de envío (`send_mail.py`)

- Usa `smtplib` de Python estándar contra `smtp.office365.com:587` con **STARTTLS**.
- Autentica con la cuenta remitente y su **app-password**.
- Adjunta el dump al correo dirigido a los destinatarios configurados.
- Exit `0` = ok; `1` = error (reporta en stderr).

### Configuración (`/home/infra/gidas/.env.backup`)

```ini
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_SENDER=infrait@frlp.utn.edu.ar
SMTP_APP_PASSWORD=********   # app-password de Outlook 365 (permisos 600)
SMTP_TO=gidas@frlp.utn.edu.ar,infra@frlp.utn.edu.ar,infrait@frlp.utn.edu.ar

BACKUP_DIR=/home/infra/gidas-backups
RETENTION_WEEKS=4
```

> ⚠️ **El archivo `.env.backup` tiene permisos `600` y NO se documenta ni
> versiona** (cubierto por `.gitignore`). No exponer el valor de
> `SMTP_APP_PASSWORD`.

---

## 6. Programación (cron)

En el crontab del usuario `infra`:

```
0 3 * * 6 bash /home/infra/scripts/backup_db.sh >> /home/infra/gidas-backups/backup.log 2>&1
```

- **Frecuencia:** semanal, sábados a las 03:00.
- Log: `/home/infra/gidas-backups/backup.log`.

---

## 7. Verificación

Verificado el 2026-08-28:
- Dump generado: `gidas-weekly-20260828-111212.dump` (~388 KB).
- Formato validado: `PostgreSQL custom database dump - v1.15-0`.
- Envío: SMTP autenticado a `smtp.office365.com` exitoso (exit `0`), destinatarios
  `gidas@frlp.utn.edu.ar` e `infra@frlp.utn.edu.ar`.

---

## 8. Restauración

Para restaurar el último dump:

```bash
cd /home/infra/gidas
docker compose --env-file .env.production exec -T db \
    pg_restore -U gidas_admin -d gidas_db --clean \
    < /home/infra/gidas-backups/gidas-weekly-<fecha>.dump
```

> Realizar una prueba de restauración periódica para validar la integridad de los
> respaldos (drill de recuperación).

---

## 9. Limitaciones y deuda operativa

- **Ningún MTA (Postfix/Exim) configurado como relay** en la VM; el envío se hace
  por **SMTP directo a Outlook 365** con la cuenta `infrait@frlp.utn.edu.ar`.
- El SMTP AUTH debe estar habilitado en Microsoft 365 para la cuenta remitente.
- El app-password es un **secreto**; si se expone, rotarlo y actualizar
  `.env.backup`.
- No se adjunta el dump si el correo excede límites (el de Outlook 365 es 25 MB);
  a este volumen (~390 KB) no hay riesgo.

---

## 10. Verificación 2026-10-08 (tras el upgrade a v1.1.0-beta.1)

Recontrol de la cadena completa después de la actualización de producción. **Resultado:
todo operativo.**

| Punto verificado | Evidencia |
|---|---|
| Cron instalado | `0 3 * * 6` → `bash /home/infra/scripts/backup_db.sh`, log en `gidas-backups/backup.log` |
| Corridas históricas | 5 seguidas exitosas: 05/09, 12/09, 19/09, 26/09 y 03/10 (dump + email) |
| Destinatarios | `gidas@frlp.utn.edu.ar`, `infra@frlp.utn.edu.ar` |
| Política de retención | 4 semanas, purga automática observada en cada corrida |
| Configuración secreta | `/home/infra/gidas/.env.backup` con permisos `600` y dueño `infra` |
| Autenticación SMTP | `smtp.office365.com:587` con STARTTLS + login como `infrait@frlp.utn.edu.ar` → OK (prueba sin envío) |
| Script ejecutado por el cron | idéntico al del repo (`diff` limpio) |
| Dump con la base ya migrada | `gidas-weekly-20261008-092846.dump`, 472 KB, **1104 objetos TOC** (907 antes del upgrade), con las tablas nuevas (`tipo_cambio`, `login_attempt`, logros del PID) |
| Envío real | Mail de prueba con ese dump enviado a ambos destinatarios, `exit=0` |

**Próxima verificación:** el sábado 10/10 a las 03:00 corre la primera corrida automática
sobre la versión nueva. Confirmar en `backup.log` que figure `Dump ok` y `Email enviado ok`.

**Deuda operativa detectada:** el cron apunta a `/home/infra/scripts/backup_db.sh`, una copia
fuera del repo. Hoy es idéntica al archivo versionado, pero una edición en el repo no llegaría
al cron. Unificar apuntando al script del repo o agregar el diff al preflight.

---

## 11. Destinatarios: se sumó la casilla operativa (2026-10-09)

Diagnóstico a pedido de infraestructura: el backup semanal "no llegaba" a
`infrait@frlp.utn.edu.ar`. Verificación de la cadena:

- Sondeo SMTP: `LOGIN 235` OK y los tres buzones existen (`250 2.1.5 Recipient OK`)
  para `gidas@`, `infra@` e `infrait@`; `infra@` no rebota.
- Envío de un mensaje mínimo a `infrait@`: aceptado por Office 365 con id de cola
  `PH0PR02MB8359F41F8F15E8AFE09484D0BB922@PH0PR02MB8359.namprd02.prod.outlook.com` y
  **recibido** en la casilla.

**Causa:** `infrait@frlp.utn.edu.ar` es el **remitente** del canal, no un destinatario. Los
envíos iban sólo a `gidas@` e `infra@`, así que en esa casilla los mensajes aparecían en
*Enviados*, nunca en *Recibidos*. No hubo falla de entrega.

**Cambio aplicado:** `SMTP_TO` en `/home/infra/gidas/.env.backup` (permisos `600` conservados)
ahora incluye `infrait@frlp.utn.edu.ar`. Respaldo previo en
`/home/infra/gidas-backups/.env.backup.bak-20261009`. Validado ejecutando el mismo
`send_mail.py` que usa el cron, con un adjunto mínimo: `Email enviado a: gidas@..., infra@...,
infrait@...`, `exit=0`. La corrida del sábado 10/10 será la primera con los tres destinatarios.

> Lectura correcta del log: `Email enviado ok` prueba **aceptación del SMTP** (250), no
> entrega. La confirmación de entrega requiere mirar el buzón; el script no puede darla.
