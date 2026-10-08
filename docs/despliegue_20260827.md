# Registro de despliegue productivo — GIDAS UCT

Fecha: 2026-08-27
Operador: emanuel (local) / infra (VM)
Servidor: VM Linux 192.168.1.111, acceso SSH `infra@192.168.1.111`
Repo clonado en la VM: `/home/infra/gidas`

> Este documento **no** contiene valores secretos reales. Los secretos viven
> exclusivamente en los archivos `.env.production` (raiz y `backend/`), que estan
> **ignorados por Git** y con permisos `600`. Copia local: misma ruta en el repo
> local. Copia en la VM: `/home/infra/gidas/`.

## 1. Version desplegada

- Commit: `ceee87d5cc2b3748d3691dc41a2d526498a85a20`
- Mensaje: `feat: consolidar arquitectura, seguridad y experiencia administrativa`
- `APP_VERSION=ceee87d`
- `APP_ENV=staging` (HTTP temporal sin TLS en LAN; no usar con datos reales aun)

## 2. Incidencia durante el build y resolucion

### Sintoma

El primer `docker compose --env-file .env.production up --build -d` fallo en la
etapa `builder` del backend:

```text
Err:2 http://deb.debian.org/debian trixie-updates InRelease  403 Forbidden
Err:3 http://deb.debian.org/debian-security trixie-security InRelease  403 Forbidden
E: The repository 'http://deb.debian.org/debian trixie InRelease' is no longer signed.
```

### Diagnostico (proceso seguido)

1. ~~Puerto 80 bloqueado~~ — descartado: desde el host, `http://deb.debian.org`
   y `https://deb.debian.org` responden `200`.
2. ~~Proxy de egress~~ — descartado: sin `HTTP_PROXY`/`HTTPS_PROXY`, sin proxy apt,
   sin config proxy en Docker (ni host ni VM).
3. ~~Egress de contenedores bloqueado~~ — descartado: desde un contenedor
   `alpine`, `wget` a las rutas de apt responde `200` por http y por https.
4. **Causa raiz**: `python:3.11-slim` es ahora Debian 13 (trixie). **apt por
   `http://` al CDN Fastly de `deb.debian.org` responde `403` desde el egress de
   produccion**, mientras que `https://` funciona. Confirmado reproduciendo
   `apt-get update` dentro de `python:3.11-slim`: falla con fuentes `http://` y
   funciona tras cambiar a `https://`.

### Fix

En `backend/Dockerfile`, en las 3 etapas que corren apt (builder, runtime,
development), se antepone un `sed` que fuerza las fuentes de Debian a https:

```dockerfile
RUN (sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || sed -i 's|http://|https://|g' /etc/apt/sources.list 2>/dev/null) \
    && apt-get update \
    && ...
```

El catch-all maneja tanto el formato deb822 (`debian.sources`) como el legacy
(`sources.list`), segun la imagen base.

## 3. Estado verificado tras el deploy

```text
NAME                  STATUS                        PORTS
gidas_prod_proxy      Up                          0.0.0.0:8080->8080/tcp
gidas_prod_frontend   Up (healthy)                 8080/tcp
gidas_prod_backend    Up (healthy)                 5000/tcp
gidas_prod_db         Up (healthy)                 5432/tcp
gidas_prod_redis      Up (healthy)                 6379/tcp
gidas_prod_migrate    (efimero, exit 0)
```

- Solo nginx publica puerto (`8080`). backend/frontend/db/redis internos en
  `gidas_prod_network`.
- Frontend responde `200` en `/` (titulo `GIDAS UCT`).
- Backend `/api/v1/health/ready` responde `200`:
  `{"data":{"dependencies":{"database":"ok","redis":"ok"},"status":"ready"}}`.

## 4. Secretos locales

Copia local de los secretos reales de produccion (ignorados por Git, permiso 600):

- `.env.production` -> variables de Compose + PostgreSQL + frontend build.
- `backend/.env.production` -> secretos de la API (SECRET_KEY, JWT_SECRET,
  REFRESH_SECRET, DATABASE_URL, rate limits, etc.).

Verificacion de que no se commitean:

```bash
git check-ignore .env.production backend/.env.production
```

Otras notas de configuracion real (no secretos):

- `APP_ENV=staging` mientras no haya TLS. Activar HTTPS -> `APP_ENV=production`
  y origenes `https://` antes de datos reales.
- `NGINX_BIND_ADDRESS=0.0.0.0`, `NGINX_PORT=8080`. Limitarlo por firewall a la
  red autorizada.
- `FRONTEND_URL=http://192.168.1.111:8080`, `FRONTEND_URLS` incluye ademas
  `http://localhost:8080`.
- `HSTS_ENABLED=False` (correcto hasta validar HTTPS extremo a extremo).

## 4bis. Optimizacion del despliegue (aplicada)

Se aplicaron mejoras de optimizacion y endurecimiento tras el primer deploy:

### Mejora 1 — liberar build cache de Docker

`docker builder prune -f` libero **672 MB** de cache de build reunido (restaban 493.9 MB
de capas activas no reclaimable). Tambien se ejecuto `docker image prune -f`
(sin dangling para eliminar). Recomendado como mantenimiento periodico.

### Mejora 2 — limites de memoria y CPU (proteccion de la VM)

La VM tiene 3,6 GiB RAM y 2 CPUs. Se fijaron limites para evitar que un leak
tumbe el host con oom-kill del kernel:

| Servicio | `mem_limit` | `cpus` |
| --- | --- | --- |
| `db` (postgres:16.15) | `1g` | `1.0` |
| `backend` | `768m` | `0.5` |

### Mejora 3 — fijar versiones de imagenes (reproducibilidad)

- `postgres:16` -> `postgres:16.15` (minor estable, confirmada por el pg_dump del contenedor).
- `redis:7-alpine` -> `redis:7.4-alpine` (linea estable).
- `python:3.11-slim` y `node:20-alpine` ya estaban a nivel de minor (3.11 / 20); se mantienen.

### Aplicacion y verificacion

- Compose validado localmente y en la VM (`docker compose config --quiet`).
- `docker compose up --build -d` recreo db (16.15), redis (7.4), migrate, backend,
  frontend. El volumen `postgres_data` persiste (mismo nombre, sin `-v`).
- Post-verificacion: 75 tablas intactas en schema `public`; backend
  `/api/v1/health/ready` -> `database: ok`, `redis: ok`; frontend `/` -> HTTP 200;
  limites activos: db mem=1073741824/cpu=1000000000, backend mem=805306368/cpu=500000000.

## 4ter. Optimizacion Docker/Compose (segunda ronda)

Se aplicaron 8 mejoras de bajo riesgo tras el evaluacion tecnica. **Garantia de datos**:
linea base registrada (8 usuarios, 1 UCT/grupo_utn, 3 roles) y backup previo en
la VM en `/home/infra/gidas-backups/pre-optimizacion-20260827-215743.dump`
(419 KB, verificable con `pg_restore --list`, 75 tablas con datos).

Mejoras aplicadas (todas en `docker-compose.yml`, `backend/Dockerfile`,
`frontend/nginx.conf` y `nginx/default.conf`):

1. **gzip + gzip_static** en `frontend/nginx.conf` y gzip en `nginx/default.conf`
   (compresion de assets y proxy; verificado `Content-Encoding: gzip`).
2. **Limpieza de imagen builder**: `build-essential` -> `gcc` en backend/Dockerfile
   (los wheels manylinux bastan; se conserva gcc como red de seguridad).
3. **Limites de recursos** (mem/cpus) para redis (256m/0.25), migrate (512m/0.5),
   frontend (256m/0.5), proxy/nginx (256m/0.25). db (1g/1.0) y backend (768m/0.5)
   ya los tenian.
4. **`init: true`** en los 6 servicios long-running.
5. **`stop_grace_period: 45s`** en backend (cortes limpios de gunicorn).
6. **`start_period: 30s`** en healthcheck de db (primer arranque frio).
7. **Healthcheck del proxy nginx** (antes no lo tenia).
8. **Dev alineado a `postgres:16.15-alpine`** en `docker-compose.dev.yml` (antes 15).

Resultado: stack reconstruido, **datos intactos** (8 usuarios, 1 UCT, 3 roles),
5 servicios healthy (db, redis, backend, frontend, proxy), gzip activo,
`Content-Encoding: gzip` en respuestas.

Pendiente (decisión): pinar imagenes por digest (reproducibilidad) quedo fuera
de esta ronda por el riesgo de un rebuild en produccion con datos protegidos.

## 4quater. Alias DNS `sgm.gidas.local` en la LAN (aplicado)

Se configuro el acceso de la LAN a la app mediante un alias DNS que abre
directamente la aplicacion en el puerto 8080 **sin escribir el puerto** en la URL.

### Requisito y topologia

- La app corre en el stack (puerto `8080` del host) y los clientes de la LAN abrian
  `http://192.168.1.111:8080`.
- El pedido fue que un alias DNS redirija directo al puerto 8080.
- **El DNS no transporta puertos**: un registro DNS solo resuelve nombre -> IP.
  Por eso el puerto se resuelve con un `nginx` del host que escucha en `:80` y hace
  `proxy_pass` al stack en `127.0.0.1:8080`. El navegador queda en `http://sgm.gidas.local`
  (por el puerto por defecto 80) y la app responde.

### Cambios aplicados

1. **MikroTik (192.168.1.1)** — entrada DNS estatica (via SSH al router):
   - `sgm.gidas.local` -> `192.168.1.111` (comentario `SGM-GIDAS Alias 8080`).
   - Se conservo la entrada preexistente `sgm-gidas.gidas.local` -> `192.168.1.111`
     (comentario `SGM-GIDAS-VM`), que ya apuntaba a la VM.
   - Verificado con `[:resolve "sgm.gidas.local"]` -> `192.168.1.111` desde el router.

2. **nginx del host (VM 192.168.1.111)** — `/etc/nginx/conf.d/gidas.conf`
   (patron oficial del repo `backend/../nginx/gidas.external.conf.example`):
   ```nginx
   server {
       listen 80;
       server_name sgm.gidas.local;
       client_max_body_size 20M;
       location / {
           proxy_pass http://127.0.0.1:8080;
           proxy_http_version 1.1;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_set_header X-Request-ID $request_id;
       }
   }
   ```
   - nginx del host habilitado y activo: `systemctl enable --now nginx`.
   - Escucha en `0.0.0.0:80`.

3. **SELinux** (VM Rocky enforcing) — se habilito el boolean:
   - `setsebool -P httpd_can_network_connect on`.
   - Sin esto, el nginx del host respondia `502 Bad Gateway` al hacer `proxy_pass`
     hacia el puerto del stack. Es el requisito canonico (Red Hat) para que nginx
     sirva como reverse proxy bajo SELinux. Se mantiene activo (necesario permanente);
     no desactiva SELinux.

4. **Firewalld** — `http` (80/tcp) ya estaba habilitado; `8080/tcp` sigue permitido.
   Se confirmo con `firewall-cmd --list-ports` (`8080/tcp`).

5. **Backend CORS (aditivo, no destructivo)** — se agrego `http://sgm.gidas.local`
   como un origen mas en `FRONTEND_URLS` del `backend/.env.production`, SIN tocar
   los origenes existentes. Resultado: 3 origenes, incluidos `sgm.gidas.local` y
   `192.168.1.111`. `CORS_ORIGINS = FRONTEND_URLS` en `config.py`, por lo que el
   login/cookie reconoce el nuevo origen.

### Verificacion end-to-end

- `http://sgm.gidas.local` (puerto 80) -> HTTP 200 (HTML de GIDAS UCT).
- `/api/v1/health/ready` via `:80` -> `database ok`, `redis ok`.
- Preflight CORS OPTIONS via `:80` con `Origin: http://sgm.gidas.local`:
  `Access-Control-Allow-Origin: http://sgm.gidas.local` y
  `Access-Control-Allow-Credentials: true` -> el login desde el alias funciona.

### Cadena de resolucion resultante

```
sgm.gidas.local (LAN)
  -> MikroTik DNS estatico 192.168.1.111
  -> nginx del host :80 (VM)
  -> proxy_pass 127.0.0.1:8080
  -> stack Docker GIDAS (frontend/backend)
```

### Limpieza de credenciales temporales

Se usaron reglas sudo NOPASSWD temporales (`/etc/sudoers.d/gidas-tmp` y
`gidas-tmp-setsebool`) para operar root sin exponer la contrasena en el canal.
**Pendiente: revertir (borrar) esas reglas** para no dejar sudo ampliado en
produccion; conservar solo la preexistente de `realm`/`adcli`. El boolean SELinux
se mantiene (necesario).

## 5. Aun pendiente

- Commitear el fix de `backend/Dockerfile` (apt por https) en el repo, para que
  un proximo `git pull` en la VM no sobreescriba el archivo fijado manualmente.
  Mensaje propuesto:
  `fix(backend): usar fuentes de Debian por https para evitar 403 en el build`
  La VM ya quedo con el fix; quedo sincronizado tambien en el repo local.
- **Revertir las reglas sudoers NOPASSWD temporales** en la VM
  (`/etc/sudoers.d/gidas-tmp` y `/etc/sudoers.d/gidas-tmp-setsebool`) tras dejar
  documentado este cambio, para no dejar sudo ampliado en produccion. Conservar
  solo la regla preexistente de `realm`/`adcli`.
- **Documentar en el repo** los cambios de las rondas de optimizacion (1 y 2) y el
  alias DNS de la seccion 4quater: estan en el working tree local sin commitear.
- Cerrar HTTPS, firewall y provision segura de secretos antes de datos reales.
  Ver `docs/revision_seguridad_despliegue.md` y `docs/configuracion_manual_pendiente.md`.

## 6. Referencias

- Guia completa de operacion: `docs/despliegue_produccion.md`
- Rotacion de secretos comprometidos: `docs/configuracion_manual_pendiente.md`
- Registro de despliegue recomendado (plantilla): seccion 15 de
  `docs/despliegue_produccion.md`.
