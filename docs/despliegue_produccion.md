# Guia operativa de despliegue en servidor

## Escenario confirmado: maquina virtual administrada por SSH

La primera instalacion se realizara en una unica maquina virtual Linux. El operador
ingresara por SSH y ejecutara Docker Compose directamente en el host. No se requiere
por ahora un pipeline de CD, Kubernetes, registro privado de imagenes ni servicios
cloud administrados.

Este alcance permite aprobar la preparacion versionable y el despliegue tecnico de
la aplicacion. No permite dar por aprobados HTTPS, DNS, firewall, backups externos
ni alertas hasta conocer los recursos reales de la VM.

Topologia prevista:

- SSH expuesto solo a las direcciones administrativas autorizadas;
- Nginx como unico servicio HTTP publicado por Compose;
- backend, frontend, PostgreSQL y Redis accesibles solo en la red Docker;
- datos persistentes en el volumen nombrado de PostgreSQL;
- codigo obtenido desde un tag o commit identificable;
- configuracion real en archivos `.env.production` con permiso `600`.

Si el acceso inicial debe limitarse al propio host, definir
`NGINX_BIND_ADDRESS=127.0.0.1` y usar un tunel SSH para las comprobaciones tecnicas.
Para acceso desde una red autorizada, usar `NGINX_BIND_ADDRESS=0.0.0.0` y restringir
`NGINX_PORT` mediante el firewall de la VM. El acceso HTTP no debe exponerse a
Internet ni tratarse como produccion con datos reales.

> Estado de seguridad actualizado el 2026-08-24: antes de habilitar datos reales se
> deben cerrar HTTPS, el aislamiento multi-UCT y la provision segura de secretos.
> Consulte
> [revision_seguridad_despliegue.md](./revision_seguridad_despliegue.md).

Las condiciones de aprobacion por control, incluyendo pruebas y causas de rechazo,
se mantienen en
`tasks/in-progress/security-deployment-acceptance.md`.

## Configuracion de seguridad requerida del servidor

Estos valores no deben incorporarse al repositorio. El responsable del servidor
debe proveerlos mediante archivos con permisos minimos, Docker secrets o el gestor
de secretos disponible. Las plantillas `.env.production.example` solo documentan
los nombres y formatos.

| Configuracion | Requisito |
| --- | --- |
| `APP_ENV` | Valor exacto `production`. |
| `SECRET_KEY` | Aleatorio, exclusivo del ambiente y de al menos 32 caracteres. |
| `JWT_SECRET` | Aleatorio e independiente de `SECRET_KEY` y `REFRESH_SECRET`. |
| `REFRESH_SECRET` | Aleatorio e independiente; su rotacion cierra sesiones. |
| `JWT_ISSUER` | Identificador estable de esta API. |
| `JWT_AUDIENCE` | Audiencia exclusiva del despliegue productivo. |
| `JWT_EXPIRATION_MINUTES` | Valor aprobado; recomendado 15, maximo 60 sin aceptacion de riesgo. |
| `REFRESH_TOKEN_EXPIRATION_MINUTES` | Periodo aprobado junto con retencion y purga de sesiones. |
| `REFRESH_SESSION_RETENTION_DAYS` | Dias de trazabilidad antes de purgar sesiones vencidas o revocadas; default 30. |
| `FRONTEND_URL` / `FRONTEND_URLS` | Origen HTTPS exacto, sin comodines ni URLs de desarrollo. |
| `DATABASE_URL` | Conexion del usuario de aplicacion con privilegios minimos. |
| `MIGRATION_DATABASE_URL` | Conexion separada para migraciones. |
| `POSTGRES_ADMIN_PASSWORD` | Secreto administrativo, no utilizado por el backend en runtime. |
| `POSTGRES_APP_PASSWORD` | Secreto exclusivo del usuario de aplicacion. |
| `RATELIMIT_STORAGE_URI` | Redis interno compartido; nunca `memory://` en produccion. |
| `VITE_API_BASE_URL` | `/api/v1` para mantener frontend y API en el mismo origen. |
| `MAX_CONTENT_LENGTH` | Debe conservar un valor positivo que no supere `NGINX_CLIENT_MAX_BODY_SIZE`. |

Requisitos no expresables solo mediante variables:

- DNS o IP estable y certificado TLS confiable;
- firewall que publique unicamente el proxy HTTPS y administracion autorizada;
- PostgreSQL, Redis, backend y frontend sin acceso directo desde la LAN;
- reloj del host sincronizado;
- volumen de PostgreSQL persistente y backups cifrados con restauracion probada;
- logs restringidos, rotados y sin credenciales, cookies ni tokens;
- scheduler diario para `flask auth purge-refresh-sessions`, validado primero con
  `--dry-run`, segun la retencion aprobada;
- escaneo externo de puertos y validacion funcional desde otro equipo de la red.

La aplicacion no debe considerarse aprobada solo porque inicia. Cada requisito debe
adjuntar la evidencia definida en la tarea de aceptacion.

Esta guia describe el despliegue manual de Sistema GIDAS en un servidor propio
mediante Docker Compose. No implementa CI/CD ni activa HTTPS. La configuracion
TLS se tratara cuando el laboratorio defina DNS, certificados y proxy.

## 1. Arquitectura desplegada

```text
Navegador -> Nginx :NGINX_PORT -> frontend / backend
                                      |        |
                                      |        +-> PostgreSQL
                                      |        +-> Redis
                                      +-> archivos estaticos
```

Solo Nginx publica un puerto del host. PostgreSQL, Redis, backend y frontend
permanecen accesibles unicamente dentro de la red de Compose.

El arranque separa responsabilidades:

- `migrate` usa `gidas_admin`, prepara el rol de aplicacion, aplica migraciones,
  ejecuta el seed y concede permisos; luego termina.
- `backend` usa `gidas_app` durante toda la operacion normal.
- `frontend` sirve el build estatico.
- `nginx` publica frontend y `/api/v1`.

## 2. Requisitos del servidor

- Linux de 64 bits con hora sincronizada.
- Docker Engine y el complemento Docker Compose.
- Git o un mecanismo controlado para copiar una version del repositorio.
- Espacio persistente para imágenes, volumen PostgreSQL, logs y respaldos.
- IP fija o reserva DHCP en la LAN.
- Puerto elegido para `NGINX_PORT` permitido por el firewall de la LAN.
- Acceso administrativo restringido al operador del servidor.

Comprobacion inicial:

```bash
docker --version
docker compose version
git --version
df -h
timedatectl status
```

## 3. Obtener una version identificable

Desplegar una rama, tag o commit conocido. Registrar siempre el identificador:

```bash
git clone <URL_DEL_REPOSITORIO> sistema-gidas
cd sistema-gidas
git checkout <TAG_O_COMMIT_APROBADO>
git rev-parse HEAD
```

No desplegar con modificaciones locales sin registrar:

```bash
git status --short
```

## 4. Crear la configuracion productiva

Partir de las plantillas versionadas:

```bash
cp .env.production.example .env.production
cp backend/.env.production.example backend/.env.production
chmod 600 .env.production backend/.env.production
```

Los archivos reales no deben agregarse a Git ni copiarse a tickets o chats.

### Archivo raiz `.env.production`

Definir como minimo:

```env
COMPOSE_SERVICE_PREFIX=gidas_prod
COMPOSE_NETWORK=gidas_prod_network
POSTGRES_VOLUME=gidas_prod_postgres_data
POSTGRES_DB=gidas_db
POSTGRES_ADMIN_USER=gidas_admin
POSTGRES_ADMIN_PASSWORD=<CLAVE_ADMIN_ALEATORIA>
POSTGRES_APP_USER=gidas_app
POSTGRES_APP_PASSWORD=<CLAVE_APP_ALEATORIA_DISTINTA>
MIGRATION_DATABASE_URL=postgresql://gidas_admin:<CLAVE_ADMIN_URL_ENCODED>@db:5432/gidas_db
NGINX_BIND_ADDRESS=0.0.0.0
NGINX_PORT=8080
BACKEND_ENV_FILE=.env.production
LOG_MAX_SIZE=10m
LOG_MAX_FILES=5
```

`NGINX_BIND_ADDRESS=0.0.0.0` publica el proxy en las interfaces de la VM. Limitar
su acceso mediante firewall a la red autorizada. `127.0.0.1` permite validar por
tunel SSH sin publicar el servicio a la red.

Las contrasenas incluidas en URLs deben codificarse como URL. Para reducir
errores operativos, se recomiendan contrasenas aleatorias compatibles con URI y
almacenadas en un gestor de secretos.

### Archivo `backend/.env.production`

Definir como minimo:

```env
APP_ENV=production
LOG_LEVEL=INFO
LOG_FORMAT=json
SERVICE_NAME=gidas-backend
APP_VERSION=<TAG_O_COMMIT>
SECRET_KEY=<SECRETO_ALEATORIO_DE_32_O_MAS_CARACTERES>
JWT_SECRET=<SECRETO_ALEATORIO_DISTINTO>
REFRESH_SECRET=<SECRETO_ALEATORIO_DISTINTO>
FRONTEND_URL=http://<IP_O_DNS_LAN>:8080
FRONTEND_URLS=http://<IP_O_DNS_LAN>:8080
DATABASE_URL=postgresql://gidas_app:<CLAVE_APP_URL_ENCODED>@db:5432/gidas_db
RATELIMIT_STORAGE_URI=redis://redis:6379/0
```

Mientras el acceso sea HTTP, `SESSION_COOKIE_SECURE` no debe establecerse en
`True`. Al activar HTTPS se actualizaran conjuntamente origen, cookies y proxy.

Para una calificacion tecnica temporal sin TLS usar `APP_ENV=staging`. Este modo
mantiene `DEBUG=False`, CORS restringido al origen configurado y permite la cookie
por HTTP. No debe usarse con datos reales ni como sustituto permanente de HTTPS.
Para produccion real conservar `APP_ENV=production`, usar origenes `https://` y
validar la cookie `Secure`.

El archivo del backend no debe contener la clave administrativa ni
`MIGRATION_DATABASE_URL`.

### Build del frontend

El frontend productivo recibe estas variables como argumentos de build desde el
archivo raiz; no necesita un tercer archivo `.env` en la VM:

```env
VITE_APP_ENV=production
VITE_API_BASE_URL=/api/v1
VITE_SERVER_FILTER_PERSONAL=true
```

Las variables `VITE_*` se incorporan al build y nunca deben contener secretos.

## 5. Validar antes de iniciar

Ejecutar el preflight versionado desde la raiz:

```bash
chmod +x scripts/validate-vm-deployment.sh scripts/smoke-vm-deployment.sh
./scripts/validate-vm-deployment.sh .env.production
```

El script no imprime los archivos renderizados ni sus secretos. Valida Compose,
topologia, ausencia de secretos versionados y sintaxis de Nginx.

Renderizar Compose permite detectar variables y estructura invalidas sin
iniciar contenedores:

```bash
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production config > /tmp/gidas-compose-rendered.yml
```

Revise el archivo renderizado localmente porque contiene valores sensibles y
eliminelo al terminar. Confirme que:

- `backend` usa la URL de `gidas_app`.
- `migrate` usa la URL de `gidas_admin`.
- no se publican puertos de PostgreSQL, Redis, backend ni frontend.
- solo Nginx publica `NGINX_PORT`.
- no quedan textos `replace-with` en los archivos reales.

Validar la configuracion Nginx incluida usando su misma imagen, sin iniciar el
stack:

```bash
docker run --rm -v "$PWD/nginx/default.conf:/etc/nginx/conf.d/default.conf:ro" nginxinc/nginx-unprivileged:1.27-alpine nginx -t
```

## 6. Respaldo previo

Si es el primer despliegue no existe informacion que respaldar. Para toda
actualizacion posterior, crear un directorio fuera del repositorio y generar un
dump antes de modificar servicios o migraciones:

```bash
mkdir -p ../gidas-backups
docker compose --env-file .env.production exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "../gidas-backups/gidas-$(date +%Y%m%d-%H%M%S).dump"
```

Verificar que el archivo exista, no este vacio y pueda ser listado:

```bash
ls -lh ../gidas-backups/
docker compose --env-file .env.production exec -T db pg_restore --list < <ARCHIVO_DUMP> | head
```

Un respaldo no se considera valido hasta probar periodicamente su restauracion
en una base aislada. No restaurar sobre el volumen activo sin una ventana de
mantenimiento y un procedimiento aprobado.

## 7. Primer arranque

Construir e iniciar el stack:

```bash
docker compose --env-file .env.production up --build -d
```

Compose espera PostgreSQL, ejecuta `migrate`, inicia el backend con el rol de
aplicacion y finalmente habilita frontend y Nginx.

Comprobar el resultado del servicio efimero y el estado general:

```bash
docker compose --env-file .env.production ps -a
docker compose --env-file .env.production logs --tail=200 migrate
docker compose --env-file .env.production logs --tail=200 backend nginx
```

`migrate` debe terminar con codigo `0`; no debe permanecer ejecutandose.

## 8. Verificacion tecnica y funcional

Despues del arranque ejecutar:

```bash
./scripts/smoke-vm-deployment.sh .env.production
```

Opcionalmente puede indicarse la URL que realmente usaran los clientes:

```bash
./scripts/smoke-vm-deployment.sh .env.production http://<IP_VM>:8080
```

Desde el servidor:

```bash
curl -i http://127.0.0.1:8080/api/v1/health/live
curl -i http://127.0.0.1:8080/api/v1/health/ready
curl -I http://127.0.0.1:8080/
```

Resultados esperados:

- liveness responde HTTP `200`.
- readiness responde HTTP `200` con PostgreSQL y Redis disponibles.
- el frontend responde HTTP `200`.
- las respuestas de API incluyen `X-Request-ID`.

Si `NGINX_PORT` no es `8080`, reemplazarlo en los comandos.

### Datos ficticios para calificacion de staging

La busqueda global dispone de un seed integral e idempotente para sus 24 modulos.
Solo debe cargarse en una base aislada sin datos reales. En `APP_ENV=testing` se
ejecuta directamente; para una calificacion temporal con `APP_ENV=staging`, la
habilitacion debe limitarse al proceso puntual:

```bash
docker compose --env-file .env.production run --rm --no-deps \
  -e ALLOW_TEST_SEED=true \
  --entrypoint python backend tools/seed_testing_data.py
docker compose --env-file .env.production exec backend \
  python tools/verify_search_retrieval.py
```

El resultado esperado es `Recuperacion validada para 24 modulos.`. No agregar
`ALLOW_TEST_SEED` a archivos `.env`, Compose ni servicios persistentes. Este seed
no se ejecuta en produccion y no reemplaza la validacion posterior con datos reales.

Desde otro equipo autorizado de la LAN, verificar:

```text
http://<IP_O_DNS_DEL_SERVIDOR>:<NGINX_PORT>
```

Prueba funcional minima:

1. Iniciar sesion con un usuario autorizado.
2. Consultar al menos un listado y un detalle.
3. Ejecutar una busqueda.
4. Crear o editar un registro de prueba controlado.
5. Confirmar historial y auditoria cuando correspondan.
6. Cerrar sesion y comprobar que la sesion protegida no siga disponible.

## 9. Comprobar la separacion PostgreSQL

Verificar la identidad operativa del backend:

```bash
docker compose --env-file .env.production exec backend python -c "from app import app; from extension import db; from sqlalchemy import text; app.app_context().push(); print(db.session.execute(text('SELECT current_user')).scalar())"
```

El resultado esperado es `gidas_app`.

Listar roles como administrador:

```bash
docker compose --env-file .env.production exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\\du"'
```

No usar `gidas_admin` como `DATABASE_URL` permanente del backend.

## 10. Operacion cotidiana

Estado y consumo:

```bash
docker compose --env-file .env.production ps
docker stats --no-stream
docker system df
df -h
```

Logs recientes:

```bash
docker compose --env-file .env.production logs --since=30m --tail=200 backend nginx db redis
docker compose --env-file .env.production logs -f backend
```

Reinicio controlado de un servicio:

```bash
docker compose --env-file .env.production restart backend
```

No reiniciar PostgreSQL ni eliminar volúmenes como primera respuesta a una
falla. Conservar el `X-Request-ID` mostrado en una respuesta fallida para buscar
la solicitud asociada en los logs.

## 11. Actualizacion manual

1. Anunciar la ventana y confirmar espacio disponible.
2. Crear y verificar el respaldo.
3. Registrar el commit actualmente desplegado.
4. Obtener el nuevo tag o commit aprobado.
5. Revisar cambios de plantillas y actualizar los `.env` reales manualmente.
6. Renderizar y revisar Compose.
7. Construir e iniciar la nueva version.
8. Revisar `migrate`, healthchecks y logs.
9. Ejecutar la prueba funcional minima.
10. Registrar version, fecha, operador y resultado.

Comandos base:

```bash
git fetch --tags
git checkout <NUEVO_TAG_O_COMMIT>
docker compose --env-file .env.production config --quiet
docker compose --env-file .env.production up --build -d
docker compose --env-file .env.production ps -a
```

No ejecutar `docker compose down -v`: `-v` elimina el volumen persistente de
PostgreSQL.

## 12. Recuperacion ante una actualizacion fallida

Si la migracion no comenzo o no cambio el esquema:

1. Conservar logs y mensaje de error.
2. Volver al commit anterior.
3. Restaurar las variables compatibles con esa version.
4. Reconstruir y validar.

```bash
git checkout <COMMIT_ANTERIOR>
docker compose --env-file .env.production up --build -d
```

Si se aplicaron migraciones o hubo escrituras incompatibles, no improvisar un
rollback. Detener el acceso, conservar el volumen y los logs, y decidir entre
una migracion correctiva o restaurar el dump verificado en una base/volumen
aislado. Documentar el incidente antes de reabrir el servicio.

## 13. Seguridad operativa minima

- Restringir SSH, Docker y archivos `.env` a operadores autorizados.
- Permitir en firewall solo SSH administrativo y `NGINX_PORT` desde la LAN.
- No publicar PostgreSQL, Redis, backend ni frontend.
- Mantener credenciales administrativas y operativas distintas.
- Rotar secretos de forma planificada y uno por vez.
- Mantener respaldos cifrados, con retencion y prueba de restauracion.
- Aplicar actualizaciones del sistema y Docker en ventanas controladas.
- No cargar datos reales hasta completar prueba funcional y respaldo.
- Tratar HTTP en LAN como una etapa temporal; no exponerlo a Internet.

### Rate limiting en el gateway

Nginx aplica limites de solicitudes y conexiones antes de ejecutar
`proxy_pass`. Cuando se supera un limite, responde directamente con `429`, un
cuerpo JSON uniforme y `Retry-After: 30`. El campo `retry_after` del cuerpo usa
el mismo valor en segundos y la respuesta incluye `Cache-Control: no-store`.

Flask-Limiter se conserva como defensa adicional para accesos que pudieran
evitar el gateway o para limites funcionales mas especificos. En produccion,
PostgreSQL, Redis, frontend y backend no publican puertos; solo Nginx debe ser
alcanzable desde la LAN. Por lo tanto, el rechazo normal por volumen se realiza
en el gateway y no consume un worker de la aplicacion.

## 14. HTTPS y entrega

La entrega seleccionada es manual por SSH: obtener un tag o commit aprobado,
ejecutar preflight, respaldar, levantar Compose y correr el smoke test. Un pipeline
de CD queda diferido hasta que exista una necesidad operativa y se definan runner,
aprobaciones y secretos del host.

HTTPS permanece como etapa obligatoria antes de habilitar datos reales para
usuarios remotos. La arquitectura elegida termina TLS en el Nginx instalado en la
VM Ubuntu y mantiene el Nginx de Docker Compose en `127.0.0.1:8080`. PostgreSQL,
Redis, backend y frontend permanecen sin puertos publicados.

La plantilla versionada se encuentra en:

```text
nginx/gidas.external.conf.example
```

El bloque HTTPS y la redireccion HTTP estan comentados deliberadamente. No deben
activarse hasta que el laboratorio provea y confirme:

- nombre DNS definitivo;
- certificado, cadena completa y clave privada correspondiente al DNS;
- autoridad certificadora publica o institucional;
- puertos permitidos por el firewall;
- mecanismo y responsable de renovacion.

### 14.1 Preparacion del host

Instalar Nginx en Ubuntu y copiar la plantilla fuera del repositorio:

```bash
sudo install -m 0644 nginx/gidas.external.conf.example /etc/nginx/sites-available/gidas.conf
sudo ln -s /etc/nginx/sites-available/gidas.conf /etc/nginx/sites-enabled/gidas.conf
```

En `.env.production`, conservar el proxy de Compose limitado al host:

```env
NGINX_BIND_ADDRESS=127.0.0.1
NGINX_PORT=8080
```

Antes de habilitar TLS se puede validar HTTP desde la propia VM o mediante un
tunel SSH. Si se permite HTTP desde la LAN durante la puesta en marcha, debe ser
temporal y estar restringido por firewall.

### 14.2 Activacion cuando exista DNS

1. Reemplazar `gidas.laboratorio.example` en la copia instalada de la plantilla.
2. Instalar el certificado y la clave fuera del repositorio, por ejemplo bajo
   `/etc/nginx/tls/gidas/`. La clave debe ser legible solo por root y el proceso
   autorizado.
3. Reemplazar las rutas `ssl_certificate` y `ssl_certificate_key`.
4. Descomentar el bloque `server` que escucha en 443, sin habilitar todavia HSTS.
5. Configurar en `backend/.env.production` el origen exacto, sin slash final:

```env
APP_ENV=production
FRONTEND_URL=https://gidas.laboratorio.example
FRONTEND_URLS=https://gidas.laboratorio.example
HSTS_ENABLED=False
```

Si HTTPS utiliza un puerto distinto de 443, ese puerto debe aparecer tambien en
`FRONTEND_URL` y `FRONTEND_URLS`. `VITE_API_BASE_URL=/api/v1` se mantiene relativo
para que frontend y API compartan origen.

Validar y recargar el proxy externo:

```bash
sudo nginx -t
sudo systemctl reload nginx
```

Primero comprobar directamente HTTPS. Solo despues de confirmar certificado,
cadena, DNS, frontend, API y autenticacion se debe comentar el `location` HTTP y
descomentar `return 301 https://$host$request_uri;`.

### 14.3 Validacion de aceptacion

Desde un equipo cliente de la LAN:

```bash
curl -I https://gidas.laboratorio.example/
curl -fsS https://gidas.laboratorio.example/api/v1/health/live
curl -fsS https://gidas.laboratorio.example/api/v1/health/ready
```

Ademas se deben comprobar manualmente login, refresh, navegacion, logout, descarga
de exportaciones y errores del proxy. La cookie de refresh debe incluir `Secure`,
`HttpOnly`, `SameSite=Lax` y el path previsto. HTTP debe redirigir sin servir la
aplicacion ni la API en claro.

Luego de validar HTTPS en todos los clientes se puede habilitar HSTS en backend y
en el proxy externo. `includeSubDomains` no debe utilizarse sin confirmar primero
que todos los subdominios afectados funcionan exclusivamente por HTTPS.

Cuando se use una autoridad certificadora institucional, su certificado raiz debe
estar instalado como confiable en todos los clientes. Un certificado autofirmado
solo es aceptable para una validacion temporal controlada, nunca como cierre de
produccion con datos reales.

### 14.4 Renovacion y rollback

El laboratorio debe definir responsable y mecanismo de renovacion. Despues de cada
renovacion se debe ejecutar `sudo nginx -t`, recargar Nginx y volver a comprobar la
fecha, hostname y cadena desde un cliente. La clave y los certificados reales no
se copian al repositorio, a la imagen ni a los logs.

Si la activacion falla antes de habilitar HSTS:

1. volver a comentar la redireccion HTTP;
2. volver a comentar el bloque HTTPS defectuoso o restaurar la configuracion previa;
3. ejecutar `sudo nginx -t` y recargar Nginx;
4. limitar nuevamente el acceso a la LAN autorizada o a un tunel SSH;
5. corregir DNS, cadena o permisos antes de reintentar.

Si HSTS ya fue entregado a los navegadores, volver a HTTP no constituye un rollback
seguro. Por ese motivo HSTS permanece desactivado hasta completar la aceptacion
extremo a extremo.

## 15. Registro recomendado de cada despliegue

Conservar fuera del repositorio:

```text
fecha y hora:
operador:
servidor:
tag o commit:
respaldo verificado:
resultado de migrate:
resultado de health/live:
resultado de health/ready:
prueba funcional:
incidencias y vuelta atras:
```
