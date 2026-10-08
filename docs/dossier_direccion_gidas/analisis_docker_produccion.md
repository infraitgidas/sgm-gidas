# Analisis de Dockerfiles y Docker Compose para Produccion

> **Fecha:** 2026-08-27
> **Alcance:** Revision de `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`, `backend/entrypoint.sh`, `nginx/default.conf`, `nginx/default.dev.conf`, `nginx/gidas.external.conf.example`, `frontend/nginx.conf`, `.dockerignore` (backend y frontend), `requirements.txt`, `package.json`.
> **Metodo:** Revision estatica de buenas practicas de contenedores y optimizaciones necesarias para produccion. No se modifico codigo.
> **Documentos relacionados:** [Devolucion tecnica del sistema](./devolucion_tecnica_sistema.md), [Revision final de seguridad para despliegue](./revision_seguridad_despliegue.md)

---

## 1. Resumen ejecutivo

La arquitectura de build y el hardening base estan por encima del promedio para la
etapa del proyecto: multi-stage correcto, usuarios no root, `.dockerignore`
impecables, dependencias pinneadas, healthchecks reales y topologia con un unico
puerto publicado.

**Las optimizaciones necesarias no son de rediseno, sino de disciplina de
recursos, shutdown correcto y terminacion del proxy externo.** Hay 4 hallazgos
Altos que deberian resolverse antes del go-live, el primero de los cuales
(`gidas.external.conf.example` sin TLS) es el mismo bloqueante de HTTPS ya
registrado en la revision de seguridad.

La seccion 5 delimita ademas una estrategia de refinamiento multi-stage: el esquema
base ya esta aplicado, y los refinamientos con valor real son reducir la superficie
de ataque del builder, recortar paquetes innecesarios del runtime y precomprimir
los estaticos en build. Queda explicitado que el multi-stage optimiza la imagen,
no el rendimiento de runtime (seccion 5.1).

Entorno verificado: Docker 29.7.2, Compose v5.4.0 (soporta el operador `!override`
usado en el override de desarrollo; se requiere Compose v2.24+).

---

## 2. Inventario auditado

| Archivo | Rol |
|---|---|
| `backend/Dockerfile` | Multi-stage: builder (wheels) -> runtime (slim, no root) -> development / production |
| `backend/entrypoint.sh` | Espera de PostgreSQL, modo `migrate` (roles + upgrade + seed + grant) vs `serve` (gunicorn) |
| `backend/requirements.txt` | 25 dependencias pinneadas con `==` |
| `frontend/Dockerfile` | Multi-stage: npm ci -> build (Vite production) -> nginx-unprivileged |
| `frontend/nginx.conf` | Servido estatico + SPA fallback + cache de assets + CSP |
| `docker-compose.yml` | Topologia productiva: db, redis, migrate, backend, frontend, nginx |
| `docker-compose.dev.yml` | Override de desarrollo (publica puertos, monta codigo, desactiva hardening) |
| `nginx/default.conf` | Proxy interno: rate limiting, headers, respaldo dinamico |
| `nginx/default.dev.conf` | Proxy de desarrollo (mismo esquema, upstream frontend :5173, soporte HMR) |
| `nginx/gidas.external.conf.example` | Plantilla del proxy externo (front de TLS) |
| `backend/.dockerignore`, `frontend/.dockerignore` | Exclusiones de build context |

---

## 3. Buenas practicas verificadas

### 3.1 Dockerfiles

- **Multi-stage correcto** en ambos: `backend/Dockerfile` compila wheels en builder
  y copia solo los wheels al runtime; `frontend/Dockerfile` separa `npm ci`
  (capa cacheable via `COPY package*.json`) del build.
- **Usuarios no root**: `USER app` al final del runtime backend; imagen
  `nginxinc/nginx-unprivileged` para frontend y proxy. Imagenes slim/alpine con
  `--no-install-recommends` y limpieza de listas de apt.
- **Determinismo de dependencias**: `requirements.txt` con versiones fijas `==`;
  `npm ci` contra `package-lock.json`.
- **`.dockerignore` correctos**: ambos excluyen `.env*` (con excepcion de
  plantillas `.example`), `node_modules/`, `dist/`, `__pycache__`, `tests/`,
  logs y `.git`. No hay riesgo de fugar secretos por build context.

### 3.2 Compose de produccion

- **Hardening generalizado**: `read_only: true`, `cap_drop: ALL`,
  `no-new-privileges: true`, `pids_limit`, `tmpfs` — aplicado a redis, migrate,
  backend, frontend y nginx.
- **Healthchecks reales**: `pg_isready` en db, `redis-cli ping` en redis,
  `curl /api/v1/health/ready` (PG + Redis) en backend, `wget /` en frontend.
- **Orden de arranque por condicion**: `migrate` espera `db: service_healthy`;
  `backend` espera `migrate: service_completed_successfully` y `redis: service_healthy`.
- **`migrate` efimero**: roles -> `flask db upgrade` -> seed -> grant de minimo
  privilegio, con `restart: "no"`.
- **Redis sin persistencia** (`--appendonly no --save ""`), `maxmemory 128mb`
  con `allkeys-lru`: correcto, dado que solo almacena contadores de rate limiting
  y su perdida no afecta datos funcionales.
- **Topologia**: unicamente `nginx` publica puertos; db y redis solo `expose` en la
  red interna. Red bridge nombrada por ambiente.
- **Logging rotado** por servicio (10 MB x 5 archivos, parametrizado con
  `LOG_MAX_SIZE` / `LOG_MAX_FILES`).
- **Override de desarrollo claramente separado**: publica puertos, monta codigo en
  vivo, desactiva hardening y se documenta como no apto para produccion.

### 3.3 Nginx

- **Rate limiting doble**: zona `api_limit` 30 r/s (burst 60) para `/api/`, zona
  `auth_limit` 10 r/m con bursts diferenciados por endpoint
  (login 5, refresh 10, register 3, logout 10, cambiar-password 5).
- **Respuesta 429 JSON** con `Retry-After`, `Cache-Control: no-store` y CSP
  minima (`default-src 'none'`) via `error_page 429 = @rate_limited`.
- **Respaldo dinamico** con `resolver 127.0.0.11` y variables `$frontend_upstream`
  / `$backend_upstream`: evita que el proxy rompa si un contenedor reinicia.
- **Headers defensivos** (CSP, X-Frame-Options, nosniff, Referrer-Policy,
  Permissions-Policy) en proxy, estaticos y respuesta 429. En produccion
  `script-src 'self'` sin `unsafe-inline`; el conf dev documenta la excepcion HMR.
- **Cache de assets hasheados**: `expires 30d` + `immutable` para
  js/css/img/fonts (Vite hashea por defecto, por lo que `immutable` es seguro).
- **`server_tokens off`** en todas las configuraciones.

---

## 4. Hallazgos y optimizaciones priorizadas

### 4.1 Alto — resolver antes del go-live

| # | Hallazgo | Evidencia | Impacto |
|---|---|---|---|
| A1 | **Proxy externo sin TLS** | `nginx/gidas.external.conf.example` escucha en HTTP plano, sin redirect 443, sin HSTS, sin HTTP/2 | Es la plantilla que terminara en el servidor. Sin TLS no opera la cookie `Secure` del refresh ni HSTS. Coincide con el bloqueante #1 de `revision_seguridad_despliegue.md`. |
| A2 | **Sin limites de memoria/CPU** | `docker-compose.yml`: solo `pids_limit` en cada servicio | Una exportacion Excel (openpyxl) o un query de busqueda pesado pueden consumir toda la RAM del host y degradar a otros servicios e incluso al daemon. `pids_limit` no protege contra fugas de memoria. |
| A3 | **`init: true` ausente** | `docker-compose.yml` (los 6 servicios) | gunicorn/nginx/postgres como PID 1: procesos zombie y senales mal propagadas. Con `read_only` + `cap_drop` el problema se agrava (no hay shell externo para reap). |
| A4 | **`stop_grace_period` por defecto (10 s)** | `docker-compose.yml` | PostgreSQL y gunicorn no cierran en 10 s con requests en vuelo: reciben SIGKILL, riesgo de requests cortadas (exportaciones) o cierre abrupto de la DB. |

### 4.2 Medio — optimizaciones de impacto

| # | Hallazgo | Evidencia | Recomendacion |
|---|---|---|---|
| M1 | **Sin compresion gzip/brotli** | `frontend/nginx.conf`, `gidas.external.conf.example` | Bundle ~338 KB se sirve crudo; con gzip ~100 KB. Aplicar en el proxy externo (el interno es trafico LAN sin beneficio). |
| M2 | **`index.html` sin `Cache-Control`** | `frontend/nginx.conf` `location /` | El navegador puede quedar con HTML viejo tras un deploy (cache heuristica por Last-Modified). Fijar `no-cache` para `index.html`. |
| M3 | **Postgres desalineado dev/prod** | `docker-compose.dev.yml` (15-alpine) vs `docker-compose.yml` (16) | Migraciones que pasan en dev y fallan en prod. Alinear a PG 16. |
| M4 | **Gunicorn sin reciclado de workers** | `backend/entrypoint.sh` (sin `--max-requests`) | SQLAlchemy + openpyxl acumulan memoria en workers longevos. Agregar `--max-requests` / `--max-requests-jitter`. |
| M5 | **Timeouts de exportacion cortos** | `entrypoint.sh` (`GUNICORN_TIMEOUT=60`) + `proxy_read_timeout` default 60 s | Una exportacion de memoria pesada puede exceder y devolver 504. Elevar a 120 s. |

### 4.3 Menor — higiene

| # | Hallazgo | Evidencia | Recomendacion |
|---|---|---|---|
| m1 | Imagenes flotantes sin pin de minor/digest | `FROM python:3.11-slim`, `node:20-alpine`, `postgres:16`, `redis:7-alpine` | Pin a minor (`postgres:16.12`, etc.) o digest; bump controlado. |
| m2 | `libpq5` innecesario en runtime | `backend/Dockerfile` (psycopg2-binary embebe libpq) | Quitar del runtime (~5 MB); mantener `libpq-dev` solo en builder si se requiere compilar. |
| m3 | Espera de PostgreSQL sin timeout | `backend/entrypoint.sh` | Acotar el loop de espera (~120 s) y salir con error para fallar rapido. |
| m4 | `!override` exige Compose v2.24+ | `docker-compose.dev.yml` | Documentar el requisito en README (local verificado: v5.4.0). |

---

## 5. Estrategia de optimizacion multi-stage

### 5.1 Que optimiza y que no

El multi-stage es una tecnica de BUILD: optimiza la imagen en tamano, superficie
de ataque, pull y tiempo de deploy. **No mejora el rendimiento de runtime**
(RAM/CPU del proceso ni velocidad de requests a nivel de aplicacion): eso lo
determinan gunicorn, nginx, la base de datos y el codigo. La separacion conceptual
es importante para no invertir en el lugar equivocado.

Estado actual: el esquema base ya esta aplicado en ambos Dockerfiles. El punto mas
fuerte es el frontend, cuyo runtime (`nginx-unprivileged`) contiene SOLO el `dist`,
sin `node_modules`: la optimizacion mas importante que existe en un build Node.
Los refinamientos de esta seccion son incrementales, no un rediseno.

### 5.2 Backend: refinamientos aplicables

| Refinamiento | Efecto | Riesgo / nota |
|---|---|---|
| Builder sin herramienta de compilacion | Todas las deps tienen wheels manylinux (bcrypt, greenlet, SQLAlchemy, psycopg2-binary, PyJWT...). Forzar `--only-binary=:all:` elimina `build-essential` del builder | Si se agrega una dep sin wheel, el build falla con mensaje claro: es la senal correcta |
| Runtime sin `libpq5` | `psycopg2-binary` embebe libpq; el runtime no lo usa | Mantener `curl` para el healthcheck |
| `COPY` selectivo | Copiar solo lo que ejecuta (modulos, migrations, tools, assets, entrypoint) en vez de `COPY . .` | Costo de mantenimiento: al agregar archivos al arbol hay que actualizar el COPY |

`backend/Dockerfile` objetivo:

```dockerfile
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --only-binary=:all: --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FLASK_APP=app.py

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/* \
    && addgroup --system app \
    && adduser --system --ingroup app --home /app app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir /wheels/* \
    && rm -rf /wheels

COPY app.py config.py extension.py entrypoint.sh ./
COPY modules ./modules
COPY migrations ./migrations
COPY tools ./tools
COPY seed_roles.py ./
COPY assets ./assets

RUN chmod +x /app/entrypoint.sh \
    && chown -R app:app /app

EXPOSE 5000

USER app

CMD ["/app/entrypoint.sh"]

FROM runtime AS development

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*
USER app

FROM runtime AS production
```

Nota: si en el futuro una dependencia requiere compilar desde source, el builder
debe volver a incluir la herramienta correspondiente (p. ej. `libpq-dev` para
psycopg2 no binario) y flexibilizar `--only-binary`.

### 5.3 Frontend: precompresion estatica en build

Es la unica palanca de rendimiento por request que aporta el build: comprimir una
vez en build y servir el `.gz` con `gzip_static`, evitando que nginx comprima en
cada request. Con un bundle de ~338 KB, el cliente recibe ~100 KB y nginx libera
CPU de compresion.

`frontend/Dockerfile` objetivo (paso extra en el stage `build`; `gzip` ya esta
incluido en Alpine):

```dockerfile
FROM node:20-alpine AS dependencies

WORKDIR /app

COPY package*.json ./
RUN npm ci

FROM dependencies AS build

ARG VITE_APP_ENV=production
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_API_URL=/api
ARG VITE_SERVER_FILTER_PERSONAL=true

ENV VITE_APP_ENV=${VITE_APP_ENV} \
    VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_API_URL=${VITE_API_URL} \
    VITE_SERVER_FILTER_PERSONAL=${VITE_SERVER_FILTER_PERSONAL}

COPY . .
RUN npm run build:production \
    && find dist -type f \( -name '*.js' -o -name '*.css' -o -name '*.svg' -o -name '*.json' \) -exec gzip -9 -k {} +

FROM nginxinc/nginx-unprivileged:1.27-alpine AS production

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
```

`frontend/nginx.conf`: agregar `gzip_static on;` dentro de `server` (sirve el `.gz`
preexistente y cae a compresion dinamica si no existe).

Alternativa al `find` en Dockerfile: plugin `vite-plugin-compression` (misma
salida, mas declarativo).

### 5.4 Ganancia esperada y limites

| Aspecto | Backend | Frontend |
|---|---|---|
| Tamano de imagen | Reduccion minoritaria (quitar `libpq5`) | Ya minima; sin cambio |
| Superficie de ataque | Builder sin toolchain; runtime sin paquetes no usados | Ya minima (sin `node_modules`) |
| Performance por request | Sin cambio | TTFB mejor por gzip estatico |
| Seguridad supply-chain | Wheels binarios reproducibles | `npm ci` + lockfile (ya) |

El multi-stage NO resuelve: consumo de RAM/CPU de procesos (se atiende con los
hallazgos A2/A3/A4 de la seccion 4), velocidad de request (paginacion en BD, FTS,
caching HTTP) ni el go-live sin TLS (A1). Son planos distintos: build vs runtime.

---

## 6. Estado objetivo recomendado

### 6.1 `nginx/gidas.external.conf.example` — proxy externo con TLS

```nginx
# Proxy externo del servidor. Termina TLS y reenvia al Nginx interno del compose.
# Uso con certbot: obtener certificado y luego habilitar el server 443.
# Ejemplo con Let's Encrypt:
#   certbot certonly --nginx -d gidas.example.com

server {
    listen 80;
    server_name gidas.example.com;

    # Redireccion permanente a HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name gidas.example.com;

    ssl_certificate     /etc/letsencrypt/live/gidas.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/gidas.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # HSTS: activar SOLO cuando el TLS este verificado en produccion
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Seguridad y compresion
    server_tokens off;
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/javascript application/json image/svg+xml;
    client_max_body_size 20M;

    # Timeouts para exportaciones (openpyxl puede tardar >60 s)
    proxy_read_timeout 120s;
    proxy_send_timeout 120s;

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

Nota: al habilitar TLS deben ajustarse `REFRESH_COOKIE_SECURE=True` (si no es el
default) y verificar que Flask registre `X-Forwarded-Proto` via `ProxyFix`
(ya configurado en `backend/app.py`).

### 6.2 `docker-compose.yml` — limites, init y shutdown correcto

```yaml
  db:
    # ...existente...
    mem_limit: 1g
    cpus: 1.0
    init: true
    stop_grace_period: 30s

  redis:
    # ...existente...
    mem_limit: 256m
    cpus: 0.5
    init: true
    stop_grace_period: 5s

  migrate:
    # ...existente...
    mem_limit: 512m
    init: true

  backend:
    # ...existente...
    mem_limit: 1g
    cpus: 2.0
    init: true
    stop_grace_period: 30s

  frontend:
    # ...existente...
    mem_limit: 256m
    cpus: 0.5
    init: true
    stop_grace_period: 10s

  nginx:
    # ...existente...
    mem_limit: 256m
    cpus: 0.5
    init: true
    stop_grace_period: 10s
```

Con esto, la sumatoria (3.3 GB) es consistente con la VM de 4 GB estimada para
10 usuarios en la [devolucion tecnica](./devolucion_tecnica_sistema.md).

### 6.3 `backend/entrypoint.sh` — gunicorn con reciclado y timeout

```sh
exec gunicorn "app:app" \
  --bind 0.0.0.0:5000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --timeout "${GUNICORN_TIMEOUT:-120}" \
  --max-requests "${GUNICORN_MAX_REQUESTS:-1000}" \
  --max-requests-jitter "${GUNICORN_MAX_REQUESTS_JITTER:-100}" \
  --access-logfile - \
  --error-logfile -
```

Mas tiempo de espera acotada en el loop de PostgreSQL:

```sh
# antes del loop while actual
wait_timeout="${DB_WAIT_TIMEOUT:-120}"
elapsed=0
while ... ; do
  sleep 2
  elapsed=$((elapsed + 2))
  if [ "$elapsed" -ge "$wait_timeout" ]; then
    echo "Error: PostgreSQL no disponible tras ${wait_timeout}s" >&2
    exit 1
  fi
done
```

### 6.4 `frontend/nginx.conf` — cache correcto de index.html

```nginx
    location = /index.html {
        add_header Cache-Control "no-cache";
        expires -1;
    }
```

(Nunca `immutable` para `index.html`; solo para assets hasheados.)

### 6.5 Dev — alinear PostgreSQL

- `docker-compose.dev.yml`: cambiar `postgres:15-alpine` -> `postgres:16-alpine`
  para espejar el major de produccion.

---

## 7. Plan de remediacion

| Prioridad | Accion | Archivos | Esfuerzo |
|---|---|---|---|
| P0 | Plantilla de proxy externo con TLS + gzip + timeouts | `nginx/gidas.external.conf.example` | Bajo |
| P0 | `mem_limit` + `cpus` + `init: true` + `stop_grace_period` | `docker-compose.yml` | Bajo |
| P1 | `Cache-Control` de `index.html` + gzip en frontend | `frontend/nginx.conf` | Bajo |
| P1 | PG 16 en dev; reciclado + timeout gunicorn; timeout de espera de DB | `docker-compose.dev.yml`, `backend/entrypoint.sh` | Bajo |
| P1 | Refinar multi-stage backend: builder binary-only, runtime sin `libpq5`, `COPY` selectivo | `backend/Dockerfile` | Bajo |
| P1 | Precompresion estatica gzip en build + `gzip_static` | `frontend/Dockerfile`, `frontend/nginx.conf` | Bajo |
| P2 | Pins de imagen; documentar requisito Compose v2.24+ | Dockerfiles, `docker-compose.dev.yml`, README | Bajo |

Todas las acciones son de bajo esfuerzo y no alteran la arquitectura. La
prioridad de negocio es P0: sin la plantilla TLS no hay go-live; sin limites de
memoria un export descontrolado puede tumbar el host.

---

## 8. Referencias

- `backend/Dockerfile`, `backend/entrypoint.sh`, `backend/requirements.txt`
- `frontend/Dockerfile`, `frontend/nginx.conf`, `frontend/package.json`
- `docker-compose.yml`, `docker-compose.dev.yml`
- `nginx/default.conf`, `nginx/default.dev.conf`, `nginx/gidas.external.conf.example`
- `backend/.dockerignore`, `frontend/.dockerignore`
- [Devolucion tecnica del sistema](./devolucion_tecnica_sistema.md)
- [Revision final de seguridad para despliegue](./revision_seguridad_despliegue.md)