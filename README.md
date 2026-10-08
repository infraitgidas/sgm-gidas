# Sistema de Gestion de Memorias Academicas

Sistema web para registrar, consolidar, versionar y exportar memorias
academicas de unidades cientifico-tecnologicas y grupos de investigacion.
Centraliza la informacion institucional, academica, administrativa y de
produccion cientifica que respalda cada memoria, con trazabilidad y auditoria
de los cambios realizados durante su ciclo de vida.

El sistema esta orientado a uso institucional controlado. No contiene datos
productivos, credenciales ni secretos versionados; la configuracion sensible
debe mantenerse siempre en archivos `.env` locales o de despliegue.

---

## Objetivo

La plataforma permite registrar, consultar, auditar y consolidar informacion
academica para construir memorias por periodo, mantener versiones historicas y
generar entregables exportables.

El dominio distingue tres niveles de informacion:

- datos vivos del sistema
- historial auditable de cambios
- snapshots historicos asociados a memorias cerradas

Una memoria cerrada opera sobre snapshots historicos y no sobre el estado vivo
de las tablas principales. De esta manera, los cambios posteriores no alteran
la informacion ya consolidada y presentada.

---

## Funcionalidades principales

- Autenticacion con roles `ADMIN`, `GESTOR` y `LECTURA`.
- Sesiones con access tokens de vida corta y refresh tokens rotativos.
- Gestion de usuarios, perfil y cambio de contrasena.
- Gestion de memorias academicas por periodo, version y estado.
- Generacion de snapshots historicos y exportacion a Excel.
- Registro institucional de UCT, directivos, cargos, programas,
  planificaciones y visitas academicas como fuentes de cada memoria.
- Registro de personal, investigadores, becarios y personal asociado.
- Registro de proyectos de investigacion y participaciones relevantes.
- Registro de recursos: becas, equipamiento, erogaciones y tipos asociados.
- Registro de produccion academica y cientifica:
  - actividades de docencia
  - documentacion bibliografica
  - trabajos en reuniones cientificas
  - trabajos en revistas
  - distinciones
  - registros de propiedad
  - articulos de divulgacion
- Gestion de transferencia socio-productiva, adoptantes y contratos.
- Catalogos transversales.
- Busqueda global.
- Panel visual de administracion para usuarios, organizacion y catalogos.
- Carga diferida de paginas por modulo con recuperacion ante fallos de chunks.
- Historial de cambios por entidad cuando el modulo lo expone.

---

## Arquitectura

El proyecto funciona como un monolito modular desacoplado entre frontend y
backend.

```text
Usuario
  |
  v
Nginx proxy
  |
  +--> Frontend React estatico
  |
  +--> Flask API /api/v1
          |
          +--> PostgreSQL
          |
          +--> Redis
```

Componentes:

- `frontend`: React, TypeScript y Vite.
- `backend`: Flask, SQLAlchemy, Flask-Migrate y servicios de dominio.
- `db`: PostgreSQL.
- `redis`: almacenamiento compartido exclusivamente para los contadores de rate
  limiting. Actualmente no se utiliza como cache de datos funcionales.
- `nginx`: proxy reverso y publicacion de frontend/API.

---

## Stack tecnologico

Backend:

- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Migrate / Alembic
- PostgreSQL
- Flask-CORS
- Flask-Limiter
- PyJWT
- openpyxl

Frontend:

- React
- TypeScript
- Vite
- React Router
- React Query
- TailwindCSS
- Recharts
- Lucide React

Infraestructura:

- Docker
- Docker Compose
- Nginx
- Redis

---

## Estructura del repositorio

```text
sistema-memorias-academicas/
|-- backend/
|   |-- modules/
|   |-- migrations/
|   |-- tests/
|   `-- tools/
|-- frontend/
|   |-- src/
|   |   |-- modules/
|   |   |-- components/
|   |   |-- context/
|   |   |-- lib/
|   |   `-- layouts/
|-- docs/
|-- nginx/
|-- tasks/
|-- docker-compose.yml
|-- docker-compose.dev.yml
`-- README.md
```

Carpetas clave:

- `backend/modules`: modulos backend por dominio, con modelos, rutas,
  controladores y servicios.
- `frontend/src/modules`: implementacion modular frontend por dominio.
- `frontend/src/components`: componentes reutilizables entre modulos.
- `frontend/src/context`, `frontend/src/lib` y `frontend/src/layouts`:
  infraestructura transversal de la aplicacion.
- `docs`: documentacion tecnica complementaria.
- `tasks`: seguimiento operativo de tareas del agente.
- `nginx`: configuracion del proxy reverso.

---

## Modulos del sistema

Los modulos actuales existen tanto en backend como en frontend:

- `auth`: login, registro, perfil, usuarios, roles, cambio de contrasena y
  refresh tokens.
- `catalogos`: categorias UTN, fuentes de financiamiento y catalogos de apoyo.
- `dashboard`: consultas agregadas para la vista principal.
- `grupo`: UCT, directivos, cargos, programas, planificaciones y visitas.
- `memorias`: periodos, versiones, estados, snapshots y exportacion.
- `personal`: investigadores, becarios, personal y tipos asociados.
- `produccion`: publicaciones, docencia, documentacion, distinciones,
  registros y articulos.
- `proyectos`: proyectos de investigacion, tipos y participaciones relevantes.
- `recursos`: becas, equipamiento, erogaciones y tipos.
- `search`: busqueda transversal.
- `shared`: auditoria, respuestas, paginacion, middleware y utilidades.
- `transferencia`: transferencias socio-productivas, adoptantes y contratos.

---

## API

La API publica se registra bajo el prefijo versionado:

```text
/api/v1
```

Todas las respuestas servidas desde `/api/v1` deben incluir el header:

```text
API-Version: v1
```

Prefijos principales:

```text
/api/v1/auth
/api/v1/catalogos/categoria-utn
/api/v1/catalogos/fuente-financiamiento
/api/v1/dashboards
/api/v1/grupo
/api/v1/memorias
/api/v1/personal
/api/v1/produccion
/api/v1/proyectos
/api/v1/recursos
/api/v1/search
/api/v1/transferencia
```

Healthchecks:

```http
GET /api/v1/health
GET /api/v1/health/live
GET /api/v1/health/ready
```

`/health` y `/health/live` confirman que el proceso responde. `/health/ready`
comprueba ademas PostgreSQL y Redis y es el endpoint utilizado por Compose para
decidir si el backend esta listo para recibir trafico.

Respuesta esperada:

```json
{
  "data": {
    "status": "ok"
  },
  "error": null,
  "meta": {}
}
```

Contrato recomendado de exito:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

Contrato recomendado de error:

```json
{
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Lo sentimos, no pudimos guardar los cambios. Verifique los datos e intente nuevamente.",
    "details": {}
  }
}
```

Los listados migrados aceptan paginacion con `page` y `per_page`. La convencion
del frontend es mostrar hasta 9 elementos por pagina en homes y 3 elementos por
pagina en historiales de cambios.

---

## Rutas frontend principales

El router usa rutas protegidas bajo `/` y rutas publicas para autenticacion:

Publicas:

```text
/
/login
/registro
```

Protegidas:

```text
/busqueda
/mi-perfil
/cambiar-password
/usuarios
/catalogos
/uct/nueva
/personal
/proyectos
/docenciaInvestigador
/documentacion
/trabajos-reunion
/trabajos-revistas
/articulos-divulgacion
/registros-propiedad
/erogaciones
/equipamiento
/objetosfinanciamiento
/transferencias
/distinciones
/participaciones
/visitantes
/memorias
```

Las rutas de alta, edicion y detalle siguen el patron funcional del modulo,
por ejemplo:

```text
/<modulo>/nuevo
/<modulo>/:id
/<modulo>/:id/editar
```

Algunas rutas historicas se mantienen como redirecciones o fachadas de
compatibilidad para no romper enlaces existentes.

---

## Autenticacion y seguridad

El modulo `auth` implementa:

- access tokens JWT de vida corta.
- refresh tokens rotativos.
- persistencia de sesiones refresh guardando solo hash del token.
- revocacion de refresh token en logout.
- revocacion de sesiones activas al cambiar contrasena o eliminar usuarios.
- control de permisos por rol en rutas protegidas.
- mensajes de error seguros y orientados a la accion del usuario.

Medidas operativas:

- CORS configurable por ambiente.
- rate limiting en backend, con Redis como storage compartido.
- rate limiting y headers defensivos en Nginx.
- validacion de secretos obligatorios en produccion.
- rechazo de placeholders y claves debiles en produccion.
- backend servido por Gunicorn en produccion.
- frontend servido como estatico por Nginx no privilegiado.
- contenedores con restricciones como `read_only`, `tmpfs`,
  `no-new-privileges`, `cap_drop` y limites de procesos cuando aplica.

La revisión de seguridad para despliegue, actualizada el 2026-08-24, mantiene como
pendientes bloqueantes la activación de HTTPS, la definición del aislamiento
multi-UCT y la provisión operativa de secretos. Los controles versionables de
límites de solicitudes, topología, JWT/refresh, CORS, headers, errores seguros e
inventario IDOR/BOLA ya están implementados, pero deben verificarse nuevamente
sobre el servidor final.

Documento de referencia:

- [Revisión final de seguridad para despliegue](./docs/revision_seguridad_despliegue.md)

No deben versionarse:

- archivos `.env` reales
- claves secretas
- tokens
- backups de base de datos
- datos productivos
- archivos exportados con informacion sensible

---

## Memorias academicas

El modulo de memorias es el nucleo funcional del sistema. Los demas modulos
registran y organizan la informacion que luego se incorpora a cada memoria
academica.

Conceptos:

- `Memoria`: identidad persistente del expediente.
- `MemoriaVersion`: ciclo editable o cerrado de una memoria.
- Estados principales: `abierta`, `en revision`, `cerrada`.

Reglas:

- cada memoria nace con una version inicial.
- una version cerrada no debe modificarse.
- si el trabajo continua, se crea una nueva version.
- al cerrar una memoria se generan snapshots historicos.
- la exportacion Excel debe usar los datos congelados de la version cerrada.

Permisos generales:

- `ADMIN`: administra usuarios; consulta, agrega, edita y elimina registros; crea
  memorias, cambia estados, reabre y exporta.
- `GESTOR`: consulta, agrega, edita y elimina contenido operativo; puede exportar
  cuando corresponde, pero no administra usuarios ni sus roles.
- `LECTURA`: consulta listados, detalles, auditorias e historiales disponibles. No
  puede agregar, editar ni eliminar registros, administrar usuarios o ejecutar
  exportaciones reservadas.

`LECTURA` es el identificador canonico del rol lector en base de datos, API y
frontend. El nombre heredado `LECTOR` se normaliza mediante migracion y no debe
utilizarse en seeds ni contratos nuevos.

Cada usuario puede consultar en `Mi perfil` una tarjeta con el rol de la sesion
activa, sus acciones disponibles y sus restricciones. La ausencia de botones en
una pantalla previene errores de uso, pero el backend siempre conserva la
autorizacion definitiva.

---

## Entornos y variables

El proyecto usa plantillas versionables para configurar entornos sin exponer
datos sensibles.

Archivos de referencia:

```text
.env.example
.env.testing.example
.env.production.example
backend/.env.example
backend/.env.testing.example
backend/.env.production.example
frontend/.env.example
frontend/.env.testing.example
frontend/.env.production.example
```

Archivos reales esperados:

```text
backend/.env
frontend/.env
.env.testing
backend/.env.testing
frontend/.env.testing
.env.production
backend/.env.production
frontend/.env.production
```

Variables relevantes del backend:

```text
APP_ENV
SECRET_KEY
JWT_SECRET
REFRESH_SECRET
DATABASE_URL
FRONTEND_URL
FRONTEND_URLS
JWT_EXPIRATION_MINUTES
REFRESH_TOKEN_EXPIRATION_MINUTES
SESSION_WARNING_SECONDS
RATELIMIT_STORAGE_URI
```

Variables relevantes del frontend:

```text
VITE_APP_ENV
VITE_API_BASE_URL
VITE_API_URL
VITE_SERVER_FILTER_PERSONAL
```

`VITE_API_BASE_URL` debe apuntar a la API versionada. Ejemplos:

```text
http://localhost:5000/api/v1
/api/v1
```

Las variables `VITE_*` son publicas y quedan embebidas en el build del
frontend. No deben contener secretos.

---

## Ejecucion con Docker

Desarrollo local con Compose:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

`docker-compose.dev.yml` es un override y no debe ejecutarse solo. Si se omite
`docker-compose.yml`, Redis no se crea y los servicios pueden quedar en redes
distintas, provocando respuestas `502 Bad Gateway` desde Nginx.

Produccion o entorno integrado:

```bash
docker compose --env-file .env.production up --build -d
```

Servicios esperados:

- Nginx publica la aplicacion.
- Frontend sirve archivos estaticos o Vite segun el compose usado.
- Backend expone la API internamente.
- PostgreSQL y Redis quedan dentro de la red Docker en produccion.

Para despliegues con HTTPS se usa un proxy Nginx externo del servidor, con
certificados administrados fuera del repositorio, que reenvia el trafico al Nginx
interno de Compose enlazado a `127.0.0.1`. La plantilla comentada se encuentra en
`nginx/gidas.external.conf.example` y el procedimiento de activacion, validacion,
renovacion y rollback esta documentado en `docs/despliegue_produccion.md`.

---

## Ejecucion local sin Docker

Backend:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
flask db upgrade
python app.py
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Scripts frontend utiles:

```bash
npm run typecheck
npm run build
npm run build:testing
npm run build:production
```

---

## Base de datos y migraciones

El esquema se administra con Alembic mediante Flask-Migrate.

Comandos habituales desde `backend/`:

```bash
flask db heads
flask db current
flask db upgrade
flask db migrate -m "descripcion"
flask db downgrade
```

Antes de aplicar cambios estructurales, conviene verificar el estado de heads y
current. El objetivo operativo es mantener un historial de migraciones claro y
evitar divergencias no documentadas.

---

## Testing y validacion

Backend:

```bash
cd backend
venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

Cobertura actual mas fuerte:

- reglas de negocio de servicios backend
- autenticacion y refresh tokens
- auditoria
- snapshots de memorias
- pertenencia temporal de entidades a memorias
- contratos HTTP principales
- recuperacion de busqueda para 24 modulos mediante fixtures ficticios idempotentes
- carga diferida de rutas y manejo accesible de espera/error

El seed integral de busqueda vive en `backend/tools/seed_testing_data.py`. Solo se
habilita en testing o de forma efimera en una base aislada de staging; no debe
ejecutarse contra datos productivos.

La validacion manual sigue siendo importante para flujos completos de UI:
login, logout, refresh, cambio de contrasena, navegacion entre modulos,
formularios, historiales y exportacion.

---

## Documentacion adicional

Documentos disponibles:

- [Guia operativa de despliegue en servidor](./docs/despliegue_produccion.md)
- [Documentacion tecnica de memorias](./docs/memorias_tecnica.md)
- [Resumen tecnico de plantilla Excel](./docs/excel_memoria_template_summary.md)
- [Backend modular](./backend/modules/README.md)
- [Frontend modular](./frontend/src/modules/README.md)
- [Frontend](./frontend/README.md)

---

## Estado actual

El sistema esta funcional como plataforma de gestion de memorias academicas
para laboratorios, unidades cientifico-tecnologicas y grupos de investigacion.
La arquitectura contempla modularidad, API versionada, auditoria, historial,
roles, autenticacion con refresh token rotativo, compatibilidad Docker,
healthchecks y separacion frontend/backend.

Estado observado en el repositorio:

- backend y frontend estan organizados por los mismos dominios principales.
- las rutas backend estan registradas bajo `/api/v1`.
- el frontend consume la API versionada mediante cliente HTTP centralizado.
- las paginas se entregan mediante chunks diferidos; el bundle inicial validado es
  de aproximadamente 338 kB minificado y no existen chunks mayores a 500 kB.
- el stack aislado de staging supera migraciones, healthchecks y smoke HTTP.
- la busqueda global recupera correctamente los 24 modulos con datos ficticios
  idempotentes de testing.
- los modulos principales tienen pantallas de home, formulario y detalle cuando
  aplica.
- los endpoints de historial existen en la mayoria de entidades operativas
  relevantes y se consumen progresivamente desde los detalles.
- las memorias mantienen su propio flujo de versiones, estados, snapshots y
  exportacion.

Puntos a seguir monitoreando:

- mantener un unico head efectivo de Alembic antes de nuevas migraciones.
- completar documentacion tecnica especifica por modulo a medida que se
  estabilicen contratos.
- revisar periodicamente que todos los detalles consuman historial cuando el
  endpoint exista.
- sostener pruebas manuales de flujos completos antes de un despliegue real.
- configurar en el servidor la ejecucion diaria de la purga de sesiones refresh
  vencidas o revocadas luego del periodo de retencion definido.
- no habilitar datos reales hasta cerrar los bloqueantes de la revisión de seguridad:
  HTTPS, aislamiento multi-UCT y gestión de secretos del servidor.

---

## Licencia y uso

Página desarrollada por Briones Benjamín, Falco Valentina y Quiroz Zoe. Como proyecto de Seminario Integrador para la facultad UTN-FRLP.

El uso, despliegue y carga de datos reales deben realizarse conforme a las politicas internas de la organizacion responsable.
