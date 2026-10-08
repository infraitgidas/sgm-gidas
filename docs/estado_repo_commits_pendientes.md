# Estado del repo y commits pendientes de publicar

Fecha: 2026-08-27 (actualizado)
Repo: https://github.com/BrionesBenjamin22/SGM-GIDAS (origin/main)

## Decisión del operador

El operador pidio **NO agregarse como colaborador ni subir al remoto de Benjamin**.
Todos los cambios quedan **local** (branch `main`) y la VM se actualiza por scp.

## Commits creados localmente, SIN publicar

El branch local `main` quedo **2 commits adelante** de `origin/main`:

| Commit | Mensaje | Archivos |
| --- | --- | --- |
| `58c929f` | `fix(backend): usar fuentes de Debian por https para evitar 403 en el build` | `backend/Dockerfile` |
| `f0b85d4` | `chore(docker): limites de recursos y versiones de imagenes fijadas` | `docker-compose.yml` |

Contenido:

- `backend/Dockerfile`: antepone un `sed` que fuerza las fuentes de Debian a
  https en las 3 etapas que corren apt (builder, production, development). Corrige
  el `403 Forbidden` + "repository no longer signed" de apt contra el CDN de
  deb.debian.org desde el egress de produccion.
- `docker-compose.yml`: limite de recursos `db` (mem 1g / cpu 1.0) y `backend`
  (mem 768m / cpu 0.5); versiones fijadas `postgres:16.15` y `redis:7.4-alpine`.

## Por que no se publicaron

`git push origin main` fallo con:

```text
remote: Permission to BrionesBenjamin22/SGM-GIDAS.git denied to rodriguezemautn.
fatal: no es posible acceder ... (403)
```

Causa: el remoto apunta a `BrionesBenjamin22/SGM-GIDAS`, pero la credencial
guardada en el cliente git autentica como `rodriguezemautn`, que **no tiene
permiso de escritura** en ese repositorio. El push de un usuario sin permiso sobre
un repo ajeno es rechazado por GitHub (403).

## Cambios sin commitear (working tree) — Ronda 2 de optimizacion

Ademas de los 2 commits, el working tree tiene modificaciones sin commitear
correspondientes a la ronda 2 de mejoras Docker/Compose:

| Archivo | Cambio |
| --- | --- |
| `backend/Dockerfile` | `build-essential` -> `gcc` en builder |
| `docker-compose.yml` | limites mem/cpu (redis, migrate, frontend, proxy), `init: true`, `stop_grace_period`, `start_period`, healthcheck proxy |
| `docker-compose.dev.yml` | dev alineado a `postgres:16.15-alpine` |
| `frontend/nginx.conf` | gzip + gzip_static |
| `nginx/default.conf` | gzip |

Estos cambios estan **aplicados y verificados en la VM** (sincronizados por scp,
stack reconstruido, datos intactos). Para versionarlos, quedarian en un commit:
`perf(docker): compresion gzip, limites de recursos e init en los servicios`.

## Cambios nuevos del 2026-08-28 (working tree, sin commitear)

| Archivo | Cambio |
| --- | --- |
| `docker-compose.yml` | servicio `frontend_sgm` (base `/sgm-gidas/`) para acceso por portal |
| `nginx/default.conf` | bloques de ruteo por prefijo `/sgm-gidas/*` → `frontend_sgm` |
| `frontend/src/main.tsx` | corrección TDZ: `createBrowserRouter` declarado antes de `createRoot.render` |
| `scripts/backup_db.sh` | backup semanal PostgreSQL + retención + envío (también en VM) |
| `scripts/send_mail.py` | envío SMTP a Outlook 365 con adjunto (también en VM) |
| `docs/backups_semanal_gidas.md` | documentación del backup automático + inicial |
| `docs/despliegue_entrega_direccion.md` | entrega a directivos (arquitectura 2 frontends, TLS, CORS) |
| `docs/devolucion_tecnica_sistema.md` | añadido bloqueante CORS + plan de remediación |
| `docs/sesion_trabajo_20260827.md` | sección 8bis (arquitectura acceso, TLS, CORS) |

> `.env.backup` NO se versiona (en `.gitignore`; contiene la app-password con
> permisos 600 en la VM).

Mensajes de commit propuestos (NO ejecutados):

```text
feat(deploy): acceso por portal con segundo frontend (subpath /sgm-gidas/)
fix(frontend): orden de inicializacion del router (error TDZ)
feat(ops): backup semanal y envio del dump por email a Outlook 365
docs: entrega a directivos, diagnstico TLS/CORS y automatizacion de backups
```

Pendiente de decision del operador si se commitean en local.

## Como retomar la publicacion (elegir una via)

1. **Colaborador**: que `BrionesBenjamin22` agregue a `rodriguezemautn` como
   colaborador con permiso de escritura. Luego:
   `git push origin main`.
2. **Fork + PR**: si el usuario con acceso es otro, crear/cambiar remoto al fork
   propio y abrir un Pull Request hacia `BrionesBenjamin22/SGM-GIDAS`.
3. **Credencial correcta**: si el usuario de GitHub con acceso difiere del email
   `errodriguez@frlp.utn.edu.ar` guardado, actualizar la credencial del repo antes
   de reintentar.

Los commits estan a salvo en el branch local `main` y no se pierden hasta que se
publique o se resuelva el acceso.

## Despliegue actual de la VM (independiente de Git)

La VM `192.168.1.111` (/home/infra/gidas) ya tiene aplicados y en ejecucion ambos
cambios (sincronizados manualmente), de modo que el despliegue en produccion NO
depende de este push. El push es necesario para que un futuro `git pull` en la VM
no revierta los archivos.

Ver: `docs/despliegue_20260827.md`.
