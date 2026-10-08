# Despliegue y configuración actual — Sistema GIDAS UCT

**Informe de entrega a la Dirección de GIDAS**
**Elaborado por:** Emanuel Rodríguez — Coordinador de InfraIT GIDAS
**Fecha:** 2026-08-28
**Estado:** EN PRODUCCIÓN (funcional, acceso interno y público por portal)

---

## 1. Resumen ejecutivo

Se encuentra **desplegado y operativo** el sistema web **GIDAS UCT** sobre la
infraestructura del laboratorio. La aplicación tiene **dos vías de acceso**:

1. **Acceso interno (LAN)** por raíz: `http://192.168.1.111:8080` y el alias
   `http://sgm.gidas.local`, para el equipo de coordinación e investigadores en la
   red del laboratorio. *(Sirve por HTTP → el navegador muestra el aviso de
   "conexión no segura"; se accede por HTTP intencionalmente, vía de administración.)*
2. **Acceso público** a través del **Portal GIDAS** (`https://gidas.frlp.utn.edu.ar/node/40`)
   que enlaza un **túnel Cloudflare** (`https://thickness-…trycloudflare.com/sgm-gidas/`)
   hacia la app. El TLS de ambas URLs es válido y de confianza (certificado del
   dominio de la universidad + certificado de Cloudflare). **Pendiente de
   coordinación:** habilitar el orígen del túnel en `FRONTEND_URLS` (CORS) para que
   el login funcione en el navegador (ver sección 5.3).

Durante la puesta en producción se resolvieron incidencias de build (apt/HTTPS),
se optimizó el stack Docker/Compose y se **corrigió un fallo de ejecución del
frontend** (error TDZ). Se reconstruyó la exposición con dos frontends coordinados:
uno para la **raíz** (acceso LAN) y otro para el **subpath `/sgm-gidas/`** (acceso
por el portal). Todo verificado funcional, **sin pérdida de datos** (8 usuarios,
1 UCT, 3 roles intactos).

**Acceso actual:**
- Interno (admin): `http://192.168.1.111:8080` y `http://sgm.gidas.local`
- Público: `https://gidas.frlp.utn.edu.ar/node/40` → túnel `…trycloudflare.com/sgm-gidas/`

---

## 2. Arquitectura del sistema

La aplicación corre como un stack de contenedores **Docker Compose** en la VM de
producción, con separación de responsabilidades y comunicación interna por red
privada de Docker.

| Componente | Tecnología | Rol |
|---|---|---|
| **Frontend (raíz)** | React + Vite (SPA) | Interfaz de acceso interno (LAN) |
| **Frontend (portal / `sgm`)** | React + Vite (SPA, base `/sgm-gidas/`) | Interfaz de acceso público (Portal) |
| **Backend** | Python (Flask) | API REST, reglas de negocio, autenticación |
| **API Gateway** | nginx (proxy) | Enrutado por prefijo, límites, headers de seguridad |
| **Base de datos** | PostgreSQL 16.15 | Persistencia (datos, historial, auditoría) |
| **Cache** | Redis 7.4-alpine | Sesiones / caché |

Topología de red: solo el **nginx gateway expone puerto** (`0.0.0.0:8080`).
Backend, frontends, BD y Redis quedan internos en la red de Docker. El nginx
**separa el tráfico por prefijo**:

```
                         ┌────────────────────────────┐
  LAN raíz ─────────────►│                            │──► frontend (raíz) :8080
  :8080 / :80 (host)     │      nginx GW              │
                         │       0.0.0.0:8080         │──► frontend_sgm (subpath)
  Portal / Cloudflare ──►│   /sgm-gidas/*  → _sgm     │        :8080
  (…/sgm-gidas/)         │   /*           → raíz      │──► backend  :5000
                         └────────────────────────────┘──► redis    :6379
                                                            db       :5432
```

**Acceso público (internet):** usuario → **Cloudflare** (TLS público) → **Portal
GIDAS** `192.168.1.43` → reenvía a la VM con prefijo `/sgm-gidas/` → nginx GW →
`frontend_sgm` (SPA) / backend.

---

## 3. Infraestructura

| Dato | Valor |
|---|---|
| Host / VM | `192.168.1.111` (hostname `sgm-gidas.gidas.local`) |
| Sistema operativo | Rocky Linux 10.1 |
| Docker Engine | 29.4.1 |
| Docker Compose | v5.1.3 |
| Repositorio (VM) | `/home/infra/gidas` |
| Repositorio local | `SGM-GIDAS` (copia de gestión) |
| Recursos VM | 3,6 GiB RAM, 2 vCPU |
| Firewall | firewalld activo (abiertos `80/http` y `8080/tcp`) |
| SELinux | Enforcing; boolean `httpd_can_network_connect` activado (requisito del reverse proxy) |

### Versión desplegada

- Commit: `ceee87d5cc2b3748d3691dc41a2d526498a85a20`
- `APP_ENV=staging` (HTTP local; **no usar con datos reales hasta cerrar HTTPS**)
- `APP_VERSION=ceee87d`

---

## 4. Estado de los servicios

Todos los servicios están **Up y Healthy**:

| Servicio | Contenedor | Estado | Puerto |
|---|---|---|---|
| nginx (gateway) | `gidas_prod_proxy` | healthy | `0.0.0.0:8080→8080` |
| frontend (raíz) | `gidas_prod_frontend` | healthy | 8080 (interno) |
| frontend (portal) | `gidas_prod_frontend_sgm` | up | 8080 (interno) |
| backend | `gidas_prod_backend` | healthy | 5000 (interno) |
| db | `gidas_prod_db` | healthy | 5432 (interno) |
| redis | `gidas_prod_redis` | healthy | 6379 (interno) |
| migrate | `gidas_prod_migrate` | one-shot (exit 0) | — |

Verificación funcional: `/` responde `200`, `/sgm-gidas/` responde `200`,
`/sgm-gidas/api/v1/health/ready` responde `200`, `/api/v1/health/ready` responde
`{"database":"ok","redis":"ok"}`, login OPTIONS `200`.

---

## 5. Configuración de acceso y red

### 5.1 Rutas de acceso

| Ruta | Resultado | Detalle |
|---|---|---|
| `http://192.168.1.111:8080` | 200 | IP directa (LAN, raíz) |
| `http://sgm.gidas.local` | 200 | Alias DNS (LAN, vía MikroTik + nginx host :80) |
| `http://localhost:8080` | 200 | Acceso localhost (desarrollo) |
| `…/sgm-gidas/` (Portal + Cloudflare) | 200 | Acceso público desde casas (subpath, TLS por Cloudflare) |

### 5.2 Alias DNS

- **DNS estático MikroTik** (`192.168.1.1`): `sgm.gidas.local` → `192.168.1.111`
  (se conservó además `sgm-gidas.gidas.local` → `192.168.1.111`, preexistente).
- El alias resuelve a la IP; el **nginx del host** escucha en `:80` y reenvía al
  stack (`proxy_pass http://127.0.0.1:8080`). Esto permite abrir la app sin
  escribir el puerto.

### 5.3 CORS / orígenes permitidos

`FRONTEND_URLS` (backend) incluye:
- `http://192.168.1.111:8080`
- `http://localhost:8080`
- `http://sgm.gidas.local`

Esto habilita el login y la cookie de sesión desde los tres orígenes internos.

> **Estado diagnóstico (2026-08-28):** el acceso por el **túnel Cloudflare** usa el
> orígen `https://thickness-assign-reproduced-cheers.trycloudflare.com`, que
> **NO está en `FRONTEND_URLS`**. Por lo tanto el backend **no emite
> `Access-Control-Allow-Origin`** para ese orígen y **el navegador bloquea el login
> por CORS** (funciona con `curl`, NO en navegador). Se lo documentó **por ahora sin
> aplicar el fix** (decisión de coordinación). Acción requerida para habilitar el
> acceso por el túnel:
>
> - **Corto plazo:** agregar el orígen del túnel a `FRONTEND_URLS` (aditivo, con
>   backup del `.env.production` y reinicio del backend). Advertencia: el nombre del
>   *Quick Tunnel* de `trycloudflare.com` es **temporal** y cambia en cada reinicio,
>   por lo que el CORS debería actualizarse cada vez que cambie la URL.
> - **Mediano plazo:** reemplazar el *Quick Tunnel* por un **Named Tunnel** con
>   hostname fijo (ej. bajo `*.frlp.utn.edu.ar`) → CORS estable y acceso HTTPS
>   consistente. Requiere coordinar con Secretaría de TIC / panel Cloudflare.

---

## 6. Configuración de nginx

### 6.1 nginx gateway (contenedor — `nginx/default.conf`)

- Escucha en `8080`, `server_name localhost`, `server_tokens off`.
- `resolver 127.0.0.11` (DNS de Docker) para upstreams internos.
- **gzip** habilitado (JS, JSON, CSS, texto, SVG, fuentes).
- Headers de seguridad: `X-Frame-Options`, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy`, `Content-Security-Policy`.
- **Rate limiting** / límites de conexión por zonas (`api_limit`, `auth_limit`,
  `api_conn`) con respuesta `429` JSON.
- Enrutado (separación por prefijo):
  - `/sgm-gidas/api/*` → backend (quita el prefijo con `rewrite`).
  - `/sgm-gidas/*` → `frontend_sgm` (SPA compilada con base `/sgm-gidas/`).
  - `/` → `frontend:8080` (SPA de la raíz, acceso interno).
  - `/api/v1/auth/*` (login, refresh, register, logout, cambiar-password) →
    backend con `limit_req` específico.
  - `/api/*` → backend.

### 6.2 nginx del host (VM — `/etc/nginx/conf.d/gidas.conf`)

- Escucha en `:80`, `server_name sgm.gidas.local`.
- Reenvía al stack: `proxy_pass http://127.0.0.1:8080`.
- Headers `X-Real-IP`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Request-ID`.

### 6.3 nginx del frontend (`frontend/nginx.conf`)

- Sirve la SPA compilada (`gzip_static` + gzip activos).

---

## 7. Seguridad aplicada

- **Autenticación por usuario y rol** (ADMIN / GESTOR); contraseñas con hash.
- **Primer login con password temporal** y cambio obligatorio (`primer_login`).
- **Auditoría e historial de cambios** por módulo (arquitectura del backend).
- **Soft delete** (`deleted_at`) en entidades.
- **Rate limiting** en endpoints de autenticación y API.
- **Headers de seguridad** y **CORS restringido** a orígenes definidos.
- Endpoints sensibles protegidos; contenedores con `read_only`, `cap_drop`,
  `no-new-privileges` y límites de recursos.

### TLS / cifrado según vía de acceso

El acceso público actual usa un **túnel Quick Tunnel de Cloudflare** (`*.trycloudflare.com`)
montado bajo el **Portal GIDAS** (`https://gidas.frlp.utn.edu.ar/node/40`).

| Vía | URL | Certificado | Estado |
|---|---|---|---|
| **Portal (dominio uni)** | `https://gidas.frlp.utn.edu.ar/node/40` | Wildcard `*.frlp.utn.edu.ar` (DigiCert) | ✅ HTTPS válido, sin aviso |
| **Túnel Cloudflare** | `https://thickness-…trycloudflare.com/sgm-gidas/` | `*.trycloudflare.com` (Google Trust Services) | ✅ HTTPS válido, sin aviso por cert |
| **LAN interna** | `http://192.168.1.111:8080` / `sgm.gidas.local` | — (HTTP puro) | ⚠️ **aviso "conexión no segura" esperado** |

> **Sobre el aviso "Tu conexión con este sitio no es segura":**
> - Por **LAN** (`http://192.168.1.111:8080`) es **HTTP sin cifrar** → el aviso es
>   esperado e inevitable mientras se acceda por HTTP. Para eliminarlo hay que
>   acceder por las vías HTTPS (túnel/portal), no por IP.
> - Por el **túnel/portal** (`https://…`) el certificado es **válido y confiable**
>   (verificado `ssl_verify=0`); el aviso no proviene del certificado. Si aparece,
>   suele deberse a que se accede por HTTP o a inspección SSL del lado del cliente.
> - **No se requiere Let's Encrypt**: los tramos HTTPS ya usan CAs públicas de
>   confianza universal (DigiCert + Google Trust). Let's Encrypt no aplicaría a la
>   LAN interna (dominios privados no validables).
>
> Coordinación pendiente: tramo **Portal `192.168.1.43` → VM `192.168.1.111`** viaja
> por HTTP sin cifrar en la red interna. El **Quick Tunnel de prueba** usa un nombre
> aleatorio que cambia en cada reinicio (afecta CORS y la estabilidad del enlace);
> se recomienda migrar a un **Named Tunnel** con hostname fijo (coordinado con TIC).

---

## 8. Datos cargados (baseline)

| Dato | Cantidad | Detalle |
|---|---|---|
| Usuarios | 8 | 1 ADMIN (`gidas`) + 7 GESTOR |
| Roles | 3 | ADMIN, GESTOR y base |
| UCT / grupo | 1 | `grupo_utn` |
| Personas | 0 | Pendiente de carga por la aplicación |

**Usuarios cargados (gestores activos):**
`lnahuel`, `leorocca`, `penalvam`, `zquiroz`, `jmarchesini`, `errodriguez`,
`aaferrando` (todos con password temporal al primer ingreso).

> Los hashes de contraseña NO se documentan. Los secretos reales viven en los
> archivos `.env.production` (ignorados por Git, permisos 600).

---

## 9. Incidences resueltas durante la puesta en producción

1. **Build 403 de apt (Debian trixie):** apt por `http` al CDN Fastly devolvía 403.
   Fix: forzar fuentes a `https` en el `backend/Dockerfile`.
2. **Optimización Docker/Compose:** límites de recursos, `init: true`,
   `stop_grace_period`, healthchecks, gzip, versiones fijadas (PostgreSQL 16.15,
   Redis 7.4-alpine).
3. **Acceso por alias DNS:** se implementó el acceso por `sgm.gidas.local`
   (nginx host :80 → 8080, DNS estático MikroTik, SELinux, firewalld).
4. **Incidente de subpath + error JS:** un cambio introdujo la exposición por
   subpath `/sgm-gidas/` con un fallo de ejecución del frontend (`Cannot access
   'router' before initialization`, error TDZ). Se **corrigió el orden de
   inicialización del router** en `frontend/src/main.tsx` y se recompiló el
   frontend de la raíz. Posteriormente, para el **acceso por el Portal**, se
   añadió un **segundo frontend** (`frontend_sgm`) compilado con base
   `/sgm-gidas/`, enrutado por el nginx por separado de la raíz. **Sin pérdida de
   datos.**

---

## 10. Respaldo de datos

Se implementó y verificó el **backup semanal automático** de la base de datos con
**envío por mail** (adjunto) a `gidas@frlp.utn.edu.ar` e `infra@frlp.utn.edu.ar`.
Detalle técnico en `docs/backups_semanal_gidas.md`.

- **Backup semanal** (`pg_dump` custom) + **retención de 4 semanas**, programado
  por cron (sábados 03:00).
- **Envío SMTP a Outlook 365** (cuenta `infrait@frlp.utn.edu.ar`, app-password con
  permisos `600`).

Respaldo histórico verificado en la VM (`/home/infra/gidas-backups/`):

| Backup | Descripción |
|---|---|
| `pre-optimizacion-20260827-215743.dump` | Previo a la optimización (419 KB) |
| `pre-reconstruccion-nginx-20260828-092457.dump` | Previo a la reconstrucción (429 KB) |
| `gidas-initial-20260828-113530.dump` | Backup inicial de referencia post-despliegue (388 KB) |
| `gidas-weekly-YYYYMMDD-HHMMSS.dump` | Respaldos semanales automáticos (nuevo) |

> Pendiente (plan de continuidad): realizar un **drill de restauración** periódico
> para validar la integridad de los respaldos, y definir la política de retención
> final + rotación externa (fuera de la VM) si se requiere.

---

## 11. Estado de Git / versionado

- El despliegue corresponde al commit `ceee87d`.
- La VM se actualiza desde el repo local por `scp` (sin acceso de escritura al
  remoto de GitHub; push bloqueado con 403).
- Cambios de configuración y corrección del frontend quedaron en el working tree
  de la VM, **pendientes de commitear** en el repo local (ver
  `docs/estado_repo_commits_pendientes.md`).

---

## 12. Acciones recomendadas (próximos pasos)

1. **Habilitar el login por el túnel (CORS):** agregar el orígen del túnel
   (`https://thickness-…trycloudflare.com`) a `FRONTEND_URLS` para que el navegador
   no bloquee el login por CORS al operar desde el portal/túnel. *(Diferido por
   coordinación; ver sección 5.3.)*
2. **Migrar a Named Tunnel:** reemplazar el *Quick Tunnel* (`trycloudflare.com`,
   nombre temporal) por un **Named Tunnel** con hostname fijo bajo `*.frlp.utn.edu.ar`.
   Esto estabiliza el CORS, el enlace del portal y el acceso HTTPS. Requiere
   coordinar con Secretaría de TIC (panel Cloudflare / DNS).
3. **Cifrar el acceso LAN interno** con el certificado del dominio
   (`*.frlp.utn.edu.ar`) en el nginx de la VM, si se requiere HTTPS en la red
   interna (el acceso público ya está cubierto por Cloudflare). Hoy la LAN sirve
   por HTTP (aviso esperado).
4. **Confirmar el tramo Portal → VM**: decidir si se cifra el tráfico interno
   entre `192.168.1.43` y `192.168.1.111` (extremo a extremo).
5. **Realizar drill de restauración** de los backups semanales (ya automatizados;
   ver `docs/backups_semanal_gidas.md`) para validar integridad antes del go-live.
6. **Commitear y versionar** los cambios de configuración (incluido el nuevo
   servicio `frontend_sgm`) y la corrección del frontend.
7. **Habilitar testing de a 2 responsables** (Coord. M. Peñalva y A. A. Ferrando)
   con los usuarios gestores ya creados, por la vía pública del portal y por LAN.
6. Definir **CI/CD** para futuras versiones (build + deploy automáticos).

---

*Documento de entrega — InfraIT GIDAS. Contacto: Coordinador de InfraIT, Emanuel
Rodríguez.*
