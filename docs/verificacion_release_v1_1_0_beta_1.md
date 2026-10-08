# Verificación de la release v1.1.0-beta.1 y sus ajustes de infraestructura

**Fecha:** 2026-10-08
**Rol responsable:** Coordinación de Infraestructura (Emanuel Rodriguez Rodriguez)
**Repo:** https://github.com/BrionesBenjamin22/SGM-GIDAS
**Release verificada:** `v1.1.0-beta.1` → commit `b8c1a81` (2026-10-03) — *"Segunda entrega para testing: memorias institucionales y optimización del sistema"*

---

## 1. Contexto

Benjamín Briones (desarrollo) envió un mail informando que subió a GitHub la release con los
ajustes solicitados por los coordinadores, y específicamente indicó:

> "@Emanuel Rodriguez Rodriguez modifique los archivos que indicaste -dockerfiles y compose,
> nginx conf- por lo tanto verifica si los ajustes que habías realizado en las máquinas del
> laboratorio se mantienen o se pierden. De todas formas fueron ajustados con los cambios
> exactos que marcaste."

Este documento deja registrada la verificación técnica de esa afirmación, punto por punto,
contra el código real del remoto y contra el estado real de la VM de producción.

---

## 2. Metodología

Verificación de solo lectura, sin modificar nada en el repo ni en la VM:

```bash
git fetch --all --prune
git rev-list --left-right --count main...origin/main      # divergencia
git diff --stat main...origin/main                        # alcance del cambio
git show origin/main:<archivo> | grep -n '<patrón>'       # presencia/ausencia de un ajuste
git diff origin/main -- <archivos infra>                  # upstream vs working tree local
git diff --stat main...origin/main -- <archivos infra>
timeout 15 ssh infra@192.168.1.111 'git status --short; git log --oneline -3; ...'
```

Archivos examinados: `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`,
`docker-compose.dev.yml`, `frontend/nginx.conf`, `nginx/default.conf`, más el estado de la VM.

---

## 3. Situación del repositorio

| Indicador | Valor |
|---|---|
| Tag nuevo | `v1.1.0-beta.1` (`b8c1a81`, 2026-10-03) |
| Commits que faltan en local | **289** |
| Archivos cambiados upstream | 625 (+42.231 / −18.567) |
| Commits locales sin pushear | `58c929f` (https en fuentes Debian), `f0b85d4` (límites e imágenes fijadas) |
| Archivos locales modificados sin commitear | `backend/Dockerfile`, `docker-compose.yml`, `docker-compose.dev.yml`, `frontend/nginx.conf`, `nginx/default.conf` |

**Técnicamente:** el merge base común es `ceee87d`. Todo lo que hiciste después existe solo en
tu máquina y no llegó a GitHub. Todo lo que hizo Benjamín existe solo en GitHub y no está en
tu máquina. Ninguna de las dos mitades conoce a la otra.

**En lenguaje simple:** están dos ramas del mismo trabajo que crecieron separadas. Nadie
pusheó lo suyo, así que nada de lo que hiciste vos está en la release, y nada de la release
está en tu máquina todavía.

---

## 4. Punto por punto: qué se verificó

### 4.1 Fix de fuentes Debian por https (evita el error 403 en el build)

**Estado: NO incluido en la release.**

Evidencia:

```bash
$ git show origin/main:backend/Dockerfile | grep -n -i 'sed -i.*http'
(sin salida)
```

Técnicamente: `origin/main` hace `RUN apt-get update && apt-get install curl` contra los
mirrors Debian en **http**. Tu commit `58c929f` agregaba
`sed -i 's|http://|https://|g' /etc/apt/sources.list.d/debian.sources` antes de cada
`apt-get update` en las tres etapas del Dockerfile (builder, runtime, development). Ese
`sed` no aparece en ningún `Dockerfile` del remoto.

**En lenguaje simple:** el problema de build que ya te habías arreglado (los repositorios de
Debian devolvían "403 prohibido" cuando se los pedía por http) **no está resuelto en la
release**. Si el mismo espejo vuelve a fallar, el build se rompe igual que la primera vez.

---

### 4.2 Arquitectura de dos frontends (Portal GIDAS en subpath `/sgm-gidas/`)

**Estado: NO incluido en la release. Es la pérdida más grave.**

Evidencia:

```bash
$ git ls-tree -r --name-only origin/main | grep -iE 'portal|external'
nginx/gidas.external.conf.example          # es un ejemplo, no la arquitectura

$ git show origin/main:docker-compose.yml | grep -nE '^  [a-z_]+:'
2:  db:    33:  redis:    63:  migrate:
94:  backend:    133:  frontend:    167:  nginx:
```

Técnicamente: la release define **6 servicios** (`db`, `redis`, `migrate`, `backend`,
`frontend`, `nginx`). Tu `docker-compose.yml` local define **7**: agrega `frontend_sgm`,
que construye con `dockerfile: Dockerfile.portal` y publica la SGM bajo el subpath
`/sgm-gidas/` con `VITE_BASE_PATH=/sgm-gidas/`. Los archivos `frontend/Dockerfile.portal` y
`frontend/nginx.portal.conf` existen **solo como untracked en la VM**; no están en ningún
commit de GitHub.

**En lenguaje simple:** el sistema corre con dos frontends (raíz + Portal con subcarpeta).
Esa arquitectura la construiste vos y **no la subió Benjamín**. Si hacés `git pull` sobre la
VM tal como está, el servicio del Portal deja de existir en el compose y la puerta de acceso
público al sistema se cae. Los archivos `.portal` no se borran (son untracked), pero nada los
va a usar.

---

### 4.3 Límites de recursos (mem_limit / cpus)

**Estado: SÍ incluido, con valores distintos a los tuyos.**

Evidencia (upstream vs. tu working tree):

| Servicio | Upstream (`origin/main`) | Tu tuning (VM) |
|---|---|---|
| `backend` | `mem_limit: 1g`, `cpus: 2.0` | `mem_limit: 768m`, `cpus: "0.5"` |
| `redis` | `mem_limit: 256m`, `cpus: 0.5` | `mem_limit: 256m`, `cpus: "0.25"` |
| `nginx` | `mem_limit: 256m`, `cpus: 0.5` | `mem_limit: 256m`, `cpus: "0.25"` |
| `db` | `mem_limit: 1g`, `cpus: 1.0` | `mem_limit: 1g`, `cpus: "1.0"` |

Técnicamente: los límites existen en ambos lados. Upstream usa `2.0` CPUs para backend sobre
una VM de 2 CPUs, lo que anula efectivamente el límite de CPU; y 1 GiB de RAM para backend
sobre una VM de 3.6 GiB total es más agresivo que tus 768 MiB.

**En lenguaje simple:** Benjamín sí copió la idea de limitar recursos. Pero puso valores
genéricos para una máquina normal, y tu VM es chica. Al subir de `768m` a `1g` y de `0.5`
a `2.0` CPUs, backend puede comer más memoria de la que le habías asignado y no tener techo
de CPU real.

---

### 4.4 Versionado de imágenes Docker

**Estado: SÍ incluido, y está mejor que el tuyo.**

| Imagen | Upstream | Tu working tree |
|---|---|---|
| Python | `python:3.11.16-slim` | `python:3.11-slim` |
| Postgres | `postgres:16.15` | `postgres:16.15` |
| Redis | `redis:7.4.9-alpine` | `redis:7.4-alpine` |
| Nginx proxy | `nginxinc/nginx-unprivileged:1.31-alpine3.24` | `nginxinc/nginx-unprivileged:1.27-alpine` |

Técnicamente: upstream fija patch (`3.11.16`) y hasta el subtag del Alpine (`alpine3.24`),
mientras que tus tags flotantes (`3.11-slim`, `7.4-alpine`, `1.27-alpine`) pueden resolverse
a una versión distinta en cada build.

**En lenguaje simple:** acá Benjamín hizo mejor que vos. Él trabaja con versiones exactas;
tus etiquetas son más generales y pueden cambiar sin aviso. Adoptá la versión de él.

---

### 4.5 `stop_grace_period` (tiempo de apagado ordenado)

**Estado: SÍ incluido, más completo que el tuyo.**

Upstream define `stop_grace_period` en **todos** los servicios: `db: 30s`, `redis: 5s`,
`backend: 30s`, `nginx: 10s`. Tu working tree solo lo define en `backend: 45s`.

Técnicamente: es el tiempo que Docker espera antes de matar el proceso con SIGKILL. En
Postgres, un apagado brusco puede dejar la base a medio escribir; 30 segundos le dan lugar a
cerrar conexiones y hacer checkpoint.

**En lenguaje simple:** él agregó un margen de cortesía en todos los contenedores para que
al apagar no se rompa nada. Es una mejora: quedate con la de él.

---

### 4.6 Salud del proxy nginx

**Parcialmente incluido.**

- `HEALTHCHECK` **dentro de** `frontend/Dockerfile` → **sí** está en upstream
  (`wget -qO- http://127.0.0.1:8080/`).
- `healthcheck` del **servicio `nginx` en `docker-compose.yml`** → **no** está en upstream;
  es tuyo.

Técnicamente: son dos cosas distintas. El healthcheck del Dockerfile vigila al frontend; el
del compose vigila al proxy que termina en 8080.

**En lenguaje simple:** él agregó una sonda para el frontend, pero no la sonda que vos
pusiste para el proxy. Si usás la de él y borrás la tuya, el proxy se queda sin vigilancia.

---

### 4.7 Compresión gzip

**Enfoques distintos; ninguno contiene al otro.**

| | Upstream | Tu working tree |
|---|---|---|
| `frontend/nginx.conf` | solo `gzip_static on;` | `gzip on;` + `gzip_static on;` + lista de tipos + nivel 6 |
| `nginx/default.conf` | sin gzip dinámico | bloque `gzip` completo con `gzip_proxied any` |

Upstream sí prepara el build para eso: `frontend/Dockerfile` genera los `.gz` con
`find dist ... -exec gzip -9 -k {} +`.

Técnicamente: `gzip_static` sirve el archivo `.gz` ya precomprimido (cero CPU por request);
`gzip on` comprime al vuelo (usa CPU, pero también cubre respuestas del backend/API que
nunca van a tener `.gz` precomprimido).

**En lenguaje simple:** él comprime los archivos del frontend antes de arrancar (barato),
vos además comprimís las respuestas del backend en el momento (más CPU, pero cubre lo que él
no cubre). Lo ideal es combinar los dos bloques: conservar su `gzip_static` + su build `.gz`,
y sumar tu `gzip on` para las APIs.

---

### 4.8 Corrección de `X-Forwarded-Proto` y timeouts de proxy

**Estado: SÍ incluido, y vos lo tenías más viejo.**

Upstream trae en `nginx/default.conf`:

```nginx
map $http_x_forwarded_proto $gidas_forwarded_proto {
    default $scheme;
    http http;
    https https;
}
...
proxy_connect_timeout 10s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;
```

Tu working tree manda `proxy_set_header X-Forwarded-Proto $scheme;` directo.

Técnicamente: `$scheme` refleja el esquema que ve nginx (siempre `http` dentro de la red
interna), mientras que el `map` respeta el header del proxy externo (Cloudflare). Sin el
`map`, Flask genera URLs `http://` cuando el usuario llega por `https://`. Los timeouts
evitan que nginx mate conexiones lentas a 60s.

**En lenguaje simple:** con tu versión, cuando alguien entra por HTTPS desde la calle, el
sistema puede responderle enlaces "http" y activar el aviso de "conexión no segura". La
versión de él resuelve eso. Adoptá la de él.

---

### 4.9 Caché de `index.html`

**Estado: SÍ incluido, es una mejora tuya ausente.**

```nginx
location = /index.html {
    add_header Cache-Control "no-cache";
    expires -1;
    try_files $uri =404;
}
```

Técnicamente: los assets de Vite llevan hash en el nombre (`app.a1b2c3.js`) y se cachean
para siempre; el `index.html` no, porque es el manifiesto que apunta a esos hashes. Si el
navegador cachea el `index.html`, el usuario queda trabado en una versión vieja después de
un deploy.

**En lenguaje simple:** es el mecanismo que evita que, tras actualizar el sistema, la gente
sigua viendo la versión anterior por culpa de su navegador. Benjamín lo tiene, vos no.

---

### 4.10 Exposición del puerto nginx (`NGINX_BIND_ADDRESS`)

**Estado: valor por defecto distinto, pero protegido por `.env`.**

- Upstream: `${NGINX_BIND_ADDRESS:-127.0.0.1}` (solo localhost)
- Tu working tree: `${NGINX_BIND_ADDRESS:-0.0.0.0}` (todas las interfaces)
- VM: `.env.production` define `NGINX_BIND_ADDRESS=0.0.0.0` → el valor del `.env` gana

Técnicamente: `.env*` está en `.gitignore`, por lo que un `git pull` no lo toca. El default
solo aplica si la variable no existe.

**En lenguaje simple:** acá no se pierde nada: el valor está guardado en el archivo de
entorno, no en el código, y ese archivo no se actualiza con el pull. **Verificar igual después
del upgrade**, porque si algún día se regenera el `.env` el sistema dejaría de atender por LAN.

---

### 4.11 Estrategia de build del backend

**Estado: distinta; la de él es más limpia, pero no probada en tu VM.**

| | Upstream | Tu working tree |
|---|---|---|
| Builder | `pip wheel --only-binary=:all:` | `pip wheel` (compila si hace falta) + `apt-get install gcc libpq-dev` |
| Copia al runtime | `COPY` explícito de módulos | `COPY . .` |

Técnicamente: `--only-binary=:all:` obliga a usar solo ruedas precompiladas, por eso no
necesita compilador. Funciona únicamente si **todas** las dependencias de `requirements.txt`
tienen rueda para esa plataforma. `COPY . .` necesita un `.dockerignore` estricto para no
subir basura o secretos a la imagen (existe `frontend/.dockerignore`; verificar el de backend).

**En lenguaje simple:** él evita compilar código C en el build (más rápido y más liviano),
pero si alguna librería no tiene versión precompilada, el build revienta. Tu versión es más
tolerante a costa de un build más pesado. Hay que probarla en la VM antes de elegir.

---

## 5. Estado de la VM de producción (192.168.1.111)

```text
HEAD:               ceee87d   (merge base; 289 commits detrás de origin/main)
Contenedores:       6/6 Up, 2 days — backend, db, frontend, frontend_sgm, proxy, redis
Archivos modificados sin commitear (7):
  backend/Dockerfile, docker-compose.yml, frontend/Dockerfile,
  frontend/nginx.conf, frontend/src/main.tsx, frontend/vite.config.ts,
  nginx/default.conf
Untracked relevante (2):
  frontend/Dockerfile.portal, frontend/nginx.portal.conf
Entorno:            .env.production con NGINX_BIND_ADDRESS=0.0.0.0 (gitignored, seguro)
```

Conflicto al hacer `git pull`: **6 de 7** archivos modificados también cambiaron upstream
(el único limpio es `frontend/vite.config.ts`).

**Técnicamente:** la VM no tiene commits propios — todos sus cambios están en el working
tree sin commitear. Un `git pull` se negará o pedirá resolución en los 6 archivos, y resolver
a ciegas puede borrar la arquitectura `frontend_sgm`.

**En lenguaje simple:** la VM está sana pero "desordenada": el trabajo hecho ahí no está
guardado en ningún commit. Si alguien tira de GitHub sin preparar, se pierde el Portal y los
ajustes de tuning.

---

## 6. Tabla resumen

| # | Ajuste | ¿En la release? | Acción |
|---|---|---|---|
| 1 | Fix https en fuentes Debian | **No** | Re-aplicar (`58c929f`) |
| 2 | Arquitectura dos frontends / Portal | **No** | Commitear y subir, o preservar aparte |
| 3 | Límites de recursos | Sí, valores distintos | Re-tuning para la VM (768m / 0.5) |
| 4 | Versionado de imágenes | Sí, mejor que el tuyo | Adoptar el de upstream |
| 5 | `stop_grace_period` | Sí, más completo | Adoptar el de upstream |
| 6 | Healthcheck del proxy nginx | **No** (solo el del frontend) | Mantener el tuyo |
| 7 | gzip: `gzip_static` + build `.gz` | Sí | Adoptar y **sumar** tu gzip dinámico |
| 8 | `X-Forwarded-Proto` + timeouts | Sí, mejor que el tuyo | Adoptar el de upstream |
| 9 | `no-cache` en `index.html` | Sí | Adoptar el de upstream |
| 10 | `NGINX_BIND_ADDRESS` | Default distinto | Verificar `.env.production` tras upgrade |
| 11 | Build backend sin compilador | Sí (distinto) | Probar en VM antes de adoptar |

---

## 7. Conclusión

La afirmación *"fueron ajustados con los cambios exactos que marcaste"* es **parcialmente
correcta**: los límites de recursos y la idea de fijar imágenes sí llegaron, con valores
genéricos. **No llegaron** el fix de fuentes Debian por https ni — sobre todo — la
arquitectura de dos frontends que sostiene el acceso público por Portal.

No existe riesgo inmediato: la VM no está tocada y los contenedores están healthy. El riesgo
aparece en el momento exacto en que se sincronice con la release sin un plan.

---

## 8. Próximos pasos propuestos

1. Responder a Benjamín con los puntos 1, 2 y 6 de la tabla (lo que falta).
2. Commitear y pushear los cambios de infraestructura locales (incluye los 2 commits
   pendientes) para que dejen de vivir solo en el working tree.
3. Ejecutar el upgrade de la VM con rebase + resolución consciente de los 6 conflictos,
   preservando `frontend_sgm`, `Dockerfile.portal` y `nginx.portal.conf`.
4. Verificar tras el upgrade: `NGINX_BIND_ADDRESS`, servicio `frontend_sgm` levantando,
   build de backend sin `gcc` y compresión gzip combinada.
5. Re-correr esta misma batería de verificación como checklist de aceptación.
