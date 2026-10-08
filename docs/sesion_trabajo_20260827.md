# Sesion de trabajo — Despliegue y optimizacion Docker (2026-08-27)

## Objetivo de la sesion

Desplegar el sistema GIDAS en produccion (VM 192.168.1.111), resolver la incidencia
de build, aplicar mejoras de optimizacion Docker/Compose seguros, y dejar el estado
documentado. **Criterio critico establecido por el operador: no perder los datos
ya creados (usuarios y UCT).**

## Participantes / ambiente

- Operador local: emanuel
- Servidor: VM Linux (Rocky Linux 10.1), `infra@192.168.1.111`
- Repo clonado en la VM: `/home/infra/gidas`
- Repo local: `/home/emanuel/Documentos/SGM-GIDAS`
- Remoto (solo lectura para el operador): `BrionesBenjamin22/SGM-GIDAS` en GitHub

---

## 1. Despliegue inicial

- Commit desplegado: `ceee87d5cc2b3748d3691dc41a2d526498a85a20`
- Mensaje: `feat: consolidar arquitectura, seguridad y experiencia administrativa`
- `APP_ENV=staging` (HTTP temporal sin TLS en LAN; no usar con datos reales aun).
- Stack: db (postgres:16), redis (7-alpine), migrate (one-shot), backend, frontend,
  nginx (proxy). Solo nginx publica `0.0.0.0:8080`.

## 2. Incidencia del build (403 de apt) y resolucion

### Sintoma
`docker compose up --build` fallo en la etapa builder del backend:
`403 Forbidden` en `deb.debian.org` + "repository no longer signed".

### Diagnostico pasos
1. Descartado bloqueo de puerto 80: host responde `200` a deb.debian.org.
2. Descartado proxy: sin HTTP_PROXY/apt proxy/config docker.
3. Descartado egress de contenedores: alpine `wget` responde `200` por http y https.
4. **Causa raiz**: `python:3.11-slim` = Debian 13 (trixie). **apt por http al CDN
   Fastly de deb.debian.org responde 403 desde el egress de produccion; https funciona.**

### Fix
En `backend/Dockerfile`, `sed` que fuerza las fuentes de Debian a https en las 3
etapas apt (builder, production, development). Catch-all para deb822 y legacy.

## 3. Estado verificado tras el deploy inicial

- 5 servicios up, db/redis/backend/frontend healthy, migrate exit 0.
- Frontend `/` -> 200 (titulo "GIDAS UCT").
- Backend `/api/v1/health/ready` -> `{"database":"ok","redis":"ok"}`.

## 4. Secretos y credenciales

Copia local de los `.env.production` reales (git-ignored, permiso 600):
- `.env.production` y `backend/.env.production`.
- Confirmado con `git check-ignore` que no se commitean.
- **Decision**: los secretos reales NO se documentan en texto plano en el repo;
  viven solo en los archivos `.env.production` ignorados.

## 5. Optimizacion Docker/Compose — Ronda 1

Ya habia mejoras previas (capturadas en commits locales):
- `58c929f fix(backend): usar fuentes de Debian por https para evitar 403 en el build`
- `f0b85d4 chore(docker): limites de recursos y versiones de imagenes fijadas`

Ronda 1 incluyo: fix apt https, limites db/backend, versiones `postgres:16.15` y
`redis:7.4-alpine`, y liberacion de 672 MB de build cache (`docker builder prune`).

## 6. Optimizacion Docker/Compose — Ronda 2 (bajo riesgo)

Previo: linea base de datos (8 usuarios, 1 UCT/grupo_utn, 3 roles) y backup
restaurable `/home/infra/gidas-backups/pre-optimizacion-20260827-215743.dump`
(419 KB, 75 tablas). Garantia: datos no se pierden.

Mejoras aplicadas y verificadas:

| # | Mejora | Archivo |
|---|--------|---------|
| 1 | gzip + gzip_static (compresion assets) | `frontend/nginx.conf`, `nginx/default.conf` |
| 2 | `build-essential` -> `gcc` en builder | `backend/Dockerfile` |
| 3 | Limites mem/cpu: redis (256m/0.25), migrate (512m/0.5), frontend (256m/0.5), proxy (256m/0.25) | `docker-compose.yml` |
| 4 | `init: true` en los 6 servicios | `docker-compose.yml` |
| 5 | `stop_grace_period: 45s` backend | `docker-compose.yml` |
| 6 | `start_period: 30s` healthcheck db | `docker-compose.yml` |
| 7 | Healthcheck del proxy nginx | `docker-compose.yml` |
| 8 | Dev alineado a `postgres:16.15-alpine` | `docker-compose.dev.yml` |

### Verificacion post-aplicacion
- **Datos intactos**: 8 usuarios, 1 UCT, 3 roles.
- 5 servicios healthy (db, redis, backend, frontend, proxy).
- gzip confirmado: `Content-Encoding: gzip` en respuestas.
- stop_grace_period 45s aplicado.

### Quedo fuera (decision) — pinar imagenes por digest
La reproducibilidad por digest quedo fuera de esta ronda por el riesgo de un
rebuild en produccion con datos protegidos. Pendiente de una pasada dedicada.

## 7. Estado de Git / commits

- **2 commits locales sin publicar** (push a `BrionesBenjamin22/SGM-GIDAS` da 403,
  el operador no tiene permiso de escritura; se decidio dejar todo en local):
  - `58c929f fix(backend): ... https ...`
  - `f0b85d4 chore(docker): limites ... versiones ...`
- **Cambios sin commitear** (ronda 2): `backend/Dockerfile`, `docker-compose.yml`,
  `docker-compose.dev.yml`, `frontend/nginx.conf`, `nginx/default.conf`.
- El operador pidio **NO agregarse como colaborador ni tocar el remoto de Benjamin**.
  Todo queda en local y la VM se actualiza por scp.

## 7bis. Alias DNS `sgm.gidas.local` (aplicado y verificado)

Pedido del operador: que el alias DNS abra la app directo en el puerto 8080 del
`192.168.1.111` **sin escribir el puerto** en la URL.

### Aclaracion tecnica clave

**El DNS no transporta puertos**: un registro DNS resuelve solo nombre -> IP. Para
que un alias lleve al 8080 hace falta servirlo en el puerto por defecto (80) y
reenviar al stack. Se resolvio con un **nginx del host** escuchando en `:80` que
hace `proxy_pass http://127.0.0.1:8080` (patron ya previsto por el repo en
`nginx/gidas.external.conf.example`).

### Cambios aplicados

1. **MikroTik (192.168.1.1)** — entrada DNS estatica via SSH:
   `sgm.gidas.local -> 192.168.1.111`. Se conservo la preexistente
   `sgm-gidas.gidas.local -> 192.168.1.111` (ambas resuelven).
2. **nginx del host (VM)** — `/etc/nginx/conf.d/gidas.conf` (`listen 80`,
   `server_name sgm.gidas.local`, `proxy_pass http://127.0.0.1:8080`, headers
   X-Forwarded-*). `systemctl enable --now nginx`. Escucha en `0.0.0.0:80`.
3. **SELinux** (Enforcing) — `setsebool -P httpd_can_network_connect on`.
   Sin esto el proxy daba `502`; es el requisito canonico (Red Hat) para reverse
   proxy bajo SELinux. Se mantiene (necesario); no desactiva SELinux.
4. **Firewalld** — `http` (80/tcp) ya habilitado; `8080/tcp` sigue permitido.
5. **Backend CORS aditivo** — se agrego `http://sgm.gidas.local` a `FRONTEND_URLS`
   en `backend/.env.production` (3 origenes, sin tocar los existentes). Por
   `CORS_ORIGINS = FRONTEND_URLS`, el login/cookie reconoce el nuevo origen.

### Verificacion end-to-end

- `http://sgm.gidas.local` -> HTTP 200 (HTML de GIDAS UCT).
- `/api/v1/health/ready` via `:80` -> `database ok`, `redis ok`.
- Preflight CORS OPTIONS via `:80` con `Origin: http://sgm.gidas.local` ->
  `Access-Control-Allow-Origin: http://sgm.gidas.local` + `Allow-Credentials: true`.

### Cadena de resolucion

```
sgm.gidas.local -> MikroTik DNS (192.168.1.111) -> nginx host :80 -> 127.0.0.1:8080 -> stack
```

### Operacion y limpieza

- Se opero root con reglas sudoers NOPASSWD temporales (para no exponer la
  contrasena en el canal). Al cerrar se **revirtieron** (borradas por el operador
  root); `infra` volvio a exigir password. Se conservo solo la regla preexistente
  de `realm`/`adcli`. Verificado que el alias sigue respondiendo 200 tras la
  revercion (nginx/firewall/SELinux no dependen de las reglas sudoers).

## 7ter. Usuarios cargados en GIDAS (baseline en produccion)

Confirmado por el operador (coincide con el baseline de datos ya registrado:
8 usuarios, 1 UCT, 3 roles). Estado real consultado en la base (`public.usuario`
JOIN `public.rol`), datos no sensibles:

| ID | nombre_usuario | mail | rol | activo | primer_login |
|----|----------------|------|-----|--------|--------------|
| 1 | gidas | gidas@frlp.utn.edu.ar | ADMIN | si | no |
| 2 | lnahuel | lnahuel@frlp.utn.edu.ar | GESTOR | si | si |
| 3 | leorocca | leorocca@frlp.utn.edu.ar | GESTOR | si | si |
| 4 | penalvam | penalvam@frlp.utn.edu.ar | GESTOR | si | si |
| 5 | zquiroz | zquiroz@frlp.utn.edu.ar | GESTOR | si | si |
| 6 | jmarchesini | jmarchesini@frlp.utn.edu.ar | GESTOR | si | si |
| 7 | errodriguez | errodriguez@frlp.utn.edu.ar | GESTOR | si | si |
| 8 | aaferrando | aaferrando@frlp.utn.edu.ar | GESTOR | si | si |

- **`gidas`** es el unico ADMIN y el unico con `primer_login=no` (ya ingreso).
- Los **7 gestores** tienen `primer_login=si` (password pendiente de cambio /
  password temporal): la app los muestra como "Activo con password temporal".
- **Nota operativa (corregida)**: el mail de `zquiroz` tenia el dominio
  `frlp.unt.edu.ar` (los demas usaban `frlp.utn.edu.ar`). El operador lo corrigio a
  `zquiroz@frlp.utn.edu.ar`; verificado en base, ya consistente con el resto.
- Los `contrasena` son hashes y NO se documentan. `deleted_at` vacio: ninguno con
  soft delete.

## 8bis. Sesión 2026-08-28 — Arquitectura de acceso, TLS y diagnóstico CORS

Registro del trabajo del 28/08: se confirmó la arquitectura de acceso real y se
diagnosticó el aviso "Tu conexión con este sitio no es segura".

### 8bis.1 Arquitectura de acceso confirmada (dos frontends)

| Contenedor | Imagen | Base path | Sirve | Ruta nginx |
|---|---|---|---|---|
| `gidas_prod_frontend` | `gidas-frontend` | `/` (raíz) | LAN interna (`:8080`, `sgm.gidas.local`) | `location /` |
| `gidas_prod_frontend_sgm` | `gidas-frontend_sgm` | `/sgm-gidas/` | Portal / túnel Cloudflare | `location /sgm-gidas/` |

- `docker-compose.yml`: servicio `frontend_sgm` (línea 166), `VITE_BASE_PATH=/sgm-gidas/`
  (línea 179). `nginx/default.conf` separa por prefijo:
  `/sgm-gidas/api/*`→backend (rewrite), `/sgm-gidas/*`→`_sgm`, `/`→raíz.
- Ambos responden 200; `/sgm-gidas/api/v1/health/ready` → 200. El `_sgm` no tiene
  healthcheck (detalle menor).

### 8bis.2 Vías de acceso y estado TLS

| Vía | URL | Cert | Estado |
|---|---|---|---|
| Portal (dominio uni) | `https://gidas.frlp.utn.edu.ar/node/40` | `*.frlp.utn.edu.ar` (DigiCert) | ✅ TLS válido |
| Túnel Cloudflare | `https://thickness-…trycloudflare.com/sgm-gidas/` | `*.trycloudflare.com` (Google Trust) | ✅ TLS válido |
| LAN interna | `http://192.168.1.111:8080` / `sgm.gidas.local` | — (HTTP) | ⚠️ aviso esperado |

- El dominio público `gidas.frlp.utn.edu.ar` resuelve a `200.10.126.117` y **no** pasa
  por Cloudflare directo; el portal lo gestiona.
- El aviso "conexión no segura" por LAN es **HTTP puro** (esperado). Los tramos HTTPS
  del túnel/portal **no** avisan por certificado (verificado `ssl_verify=0`).
- **No se requiere Let's Encrypt**: los HTTPS ya usan CAs públicas de confianza.

### 8bis.3 Hallazgo: CORS bloquea el login por el túnel

- `FRONTEND_URLS` (backend) solo tiene orígenes internos
  (`http://192.168.1.111:8080`, `http://localhost:8080`, `http://sgm.gidas.local`).
- El orígen del túnel (`https://thickness-…trycloudflare.com`) **no está** → el backend
  **no emite `Access-Control-Allow-Origin`** → el navegador **bloquea el login por CORS**
  (funciona con curl, no en navegador).
- Fix propuesto: agregar el orígen del túnel (aditivo, con backup). **Diferido por
  decisión del operador** (el nombre del Quick Tunnel es temporal; cambia en cada
  reinicio). Alternativa a mediano plazo: **Named Tunnel** con hostname fijo
  (coordinar con TIC).

### 8bis.4 Acceso recomendado (Camino 1)

- Usuarios/directivos acceden por el **túnel HTTPS** (portal `/node/40` → túnel).
- La **IP LAN `192.168.1.111:8080`** queda para **administración** (consciente del aviso
  HTTP).
- Documentación de entrega a directivos actualizada: `docs/despliegue_entrega_direccion.md`.

### 8bis.5 Estado Git / a resolver

- Pendiente de commitear en local (sin publicar a GitHub, push 403): servicio
  `frontend_sgm` en `docker-compose.yml`, ajustes de `nginx/default.conf` (prefijo sgm),
  corrección TDZ en `frontend/src/main.tsx`, y esta documentación.
- Ver `docs/estado_repo_commits_pendientes.md`.

## 8. Pendientes abiertos (decisiones del operador)

1. **Politica de backup / snapshot semanal** de la VM en tar, con notificacion por
   email a `gidas@frlp.utn.edu.ar` e `infra@frlp.utn.edu.ar`. Pendiente de definir
   el canal SMTP/relay (la VM no tiene MTA completo; el correo institucional pasa
   por Outlook 365; candidato de envio `infrait@frlp.utn.edu.ar` requiere app-password).
2. **CI/CD por deteccion de cambios en `main` del repo de Benjamin** (deploy watcher
   desde la VM, Otra via: polling con `git fetch`). Pendiente de diseño y confirmacion.
3. **Pinar imagenes por digest** (reproducibilidad).
4. **HTTPS/TLS** antes de datos reales.
   - *Estado 2026-08-28:* acceso público ya cubierto por TLS (dominio `*.frlp.utn.edu.ar`
     de DigiCert + túnel `*.trycloudflare.com` de Google Trust). **LAN interna** sigue
     por HTTP (aviso esperado). Ver sección 8bis abajo.
5. Backup automatizado del volumen `postgres_data` (conectado con la politica de backup).
6. **Commitear en local** los cambios sin publicar: ronda 2 (`backend/Dockerfile`,
   `docker-compose.yml`, `docker-compose.dev.yml`, `frontend/nginx.conf`,
   `nginx/default.conf`) y la documentacion nueva
   (`docs/despliegue_20260827.md`, `docs/sesion_trabajo_20260827.md`,
   `docs/estado_repo_commits_pendientes.md`). Girar los mensajes de commit propuestos
   en `docs/estado_repo_commits_pendientes.md`.
7. ~~Verificar y, si aplica, corregir el mail de zquiroz (dominio unt/utn)~~ —
   **RESUELTO**: el operador lo corrigio a `zquiroz@frlp.utn.edu.ar`; verificado en base.

## 9. Referencias

- Registro de despliegue: `docs/despliegue_20260827.md`
- Guia operativa completa: `docs/despliegue_produccion.md`
- Estado commits: `docs/estado_repo_commits_pendientes.md`
- Analisis docker: `docs/analisis_docker_produccion.md`
- Seguridad: `docs/revision_seguridad_despliegue.md`
- Secretos pendientes: `docs/configuracion_manual_pendiente.md`
