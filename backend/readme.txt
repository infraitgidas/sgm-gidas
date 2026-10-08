Backend - Sistema GIDAS

Descripcion general
Este backend implementa la API del sistema GIDAS sobre Flask, SQLAlchemy y PostgreSQL.
Su responsabilidad principal es administrar la informacion academica, administrativa y de produccion del laboratorio, manteniendo trazabilidad operativa, auditoria de cambios, versionado historico de memorias y una base consistente para la exportacion final de Excel.

En el estado actual del proyecto, la memoria es una entidad central del dominio:
- una memoria nace con una version inicial en estado abierta
- puede pasar por los estados abierta, en revision y cerrada
- al cerrarse genera snapshots historicas de las entidades relevantes del sistema
- si debe retomarse el trabajo, no se reabre la version cerrada: se crea una nueva version de la misma memoria

Esta estructura permite que la generacion final del Excel se apoye en una foto historica consistente de la ultima version cerrada de la memoria.

Stack tecnologico
- Python 3
- Flask
- Flask-SQLAlchemy
- Flask-Migrate / Alembic
- PostgreSQL
- PyJWT
- openpyxl

Estructura principal
- app.py
  Punto de entrada de la aplicacion y factory principal.
- config.py
  Configuracion de entorno, base de datos, CORS y JWT.
- extension.py
  Inicializacion compartida de SQLAlchemy y Migrate.
- modules/*/models
  Entidades del dominio, tablas auxiliares de auditoria y tablas snapshot de memoria.
- modules/*/services
  Logica de negocio, validaciones, historiales, snapshots y exportacion.
- modules/*/controllers
  Adaptacion HTTP entre rutas y servicios.
- modules/*/routes
  Blueprints y definicion de endpoints.
- migrations
  Historial de migraciones Alembic.
- tests
  Tests unitarios y de integracion liviana del backend.

Capacidades actuales del backend
- Autenticacion con JWT y control de acceso por rol.
- CRUD y consultas de entidades academicas y administrativas del sistema.
- Auditoria de cambios por campo mediante una tabla generica.
- Registro de eventos sobre relaciones relevantes.
- Modelo de memorias con versionado explicito.
- Snapshots historicas por version cerrada de memoria para entidades consumidas por la memoria y por la futura exportacion.
- Endpoints de historial consumible para frontend en entidades clave.
- Endpoints para consultar snapshots historicas por version de memoria.

Modelo de memorias
La capa de memorias no responde a un CRUD simple. El dominio se organiza de la siguiente manera:
- Memoria
  Representa la identidad persistente del expediente o memoria academica.
- MemoriaVersion
  Representa cada ciclo de trabajo editable de una memoria.
- Estados
  abierta, en revision, cerrada.
- Regla de cierre
  cuando una version se cierra, se persiste una foto historica de las entidades relevantes.
- Regla de reapertura
  una version cerrada no se modifica; si el trabajo continua, se crea una nueva version de la memoria.

Criterio de pertenencia a memoria
La pertenencia de una entidad a una memoria no se decide solo por existir en el sistema ni solo por su fecha de alta.
La regla vigente es:
- un item pertenece a una memoria si estuvo activo en algun tramo del periodo de esa memoria
- esto implica validar solapamiento entre el periodo de la memoria y la vigencia del item

En terminos practicos:
- entra si su fecha de alta o inicio es menor o igual al fin del periodo
- y su fecha de baja, fin o eliminacion es nula o mayor o igual al inicio del periodo

Segun la entidad, el backend usa uno de estos criterios temporales:
- Investigador, Becario, Personal y Beca
  usan fecha_alta_grupo
- Equipamiento
  usa fecha_incorporacion
- ProyectoInvestigacion
  usa fecha_inicio y fecha_fin
- ActividadDocencia
  usa fecha_inicio y fecha_fin
- TransferenciaSocioProductiva
  usa fecha_inicio y fecha_fin
- TrabajoReunionCientifica
  usa fecha_inicio
- TrabajosRevistasReferato
  usa fecha
- ParticipacionRelevante
  usa fecha
- DistincionRecibida
  usa fecha
- Erogacion
  usa fecha
- RegistrosPropiedad
  usa fecha_registro
- ArticuloDivulgacion
  usa fecha_publicacion
- DocumentacionBibliografica
  usa fecha
- VisitaAcademica
  usa fecha

Auditoria y trazabilidad
El backend registra informacion de auditoria en dos niveles:
- Auditoria estructural del registro
  created_at, updated_at, deleted_at, created_by, updated_by, deleted_by.
- Auditoria por campo
  cambios de valor registrados en una tabla generica de historial.

Ademas, las relaciones relevantes del dominio tambien pueden generar eventos de auditoria, por ejemplo vinculaciones o desvinculaciones.

Historiales y snapshots
Hay dos conceptos que no deben confundirse:
- Historial consumible
  representa la evolucion de una entidad viva y se expone para frontend.
- Snapshot de memoria
  representa la foto historica persistida al cerrar una MemoriaVersion.

Regla operativa:
- mientras la memoria esta abierta, los datos siguen vivos y editables
- cuando la memoria se cierra, se genera una foto historica
- esa foto queda asociada a una version
- el Excel debe consumir la ultima version cerrada y no las tablas vivas

Variables de entorno
La aplicacion carga variables desde el archivo definido en ENV_FILE. Si no se informa, usa .env.
La clase de configuracion se selecciona con APP_ENV.

Valores de APP_ENV soportados:
- local
- development
- docker
- testing
- production
- prod

Archivos de referencia versionables:
- .env.example
- .env.testing.example
- .env.production.example

Archivos reales esperados:
- .env para desarrollo local y compose de desarrollo
- .env.testing para testing
- .env.production para produccion

El compose de desarrollo toma backend/.env cuando no se informa otro archivo con BACKEND_ENV_FILE.

Variables importantes:
- APP_ENV
- SECRET_KEY
- JWT_SECRET
- REFRESH_SECRET
- JWT_ISSUER
- JWT_AUDIENCE
- DATABASE_URL
- FRONTEND_URL
- FRONTEND_URLS
- JWT_EXPIRATION_MINUTES
- REFRESH_TOKEN_EXPIRATION_MINUTES
- SESSION_WARNING_SECONDS
- RATELIMIT_STORAGE_URI
- RATELIMIT_DEFAULT
- AUTH_LOGIN_LIMIT
- AUTH_REFRESH_LIMIT
- AUTH_REGISTER_LIMIT
- AUTH_CHANGE_PASSWORD_LIMIT
- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

JWT_EXPIRATION_MINUTES controla la duracion real del access token. Debe ser un numero entero entre 5 y 1440 minutos. Si no se define, el backend usa 15 minutos.

REFRESH_TOKEN_EXPIRATION_MINUTES controla la vigencia renovable de la sesion y usa 10080 minutos por defecto. SESSION_WARNING_SECONDS controla la anticipacion del aviso visible de vencimiento y usa 300 segundos por defecto.

JWT_ISSUER identifica al emisor esperado de tokens y por defecto usa auth-service. JWT_AUDIENCE es opcional: cuando se define, el backend la incluye en los access tokens y rechaza tokens destinados a otra audiencia.

RATELIMIT_STORAGE_URI define el almacenamiento usado por Flask-Limiter. En local y testing puede ser memory://, pero en produccion debe apuntar a un almacenamiento compartido como Redis. La aplicacion falla al iniciar en produccion si RATELIMIT_STORAGE_URI queda en memory://. Los endpoints de autenticacion tienen limites dedicados mediante AUTH_LOGIN_LIMIT, AUTH_REFRESH_LIMIT, AUTH_REGISTER_LIMIT y AUTH_CHANGE_PASSWORD_LIMIT. Redis no se usa actualmente como cache de datos de negocio: coordina contadores entre workers/instancias y evita que reinicios del backend restablezcan localmente los limites.

Valor por defecto de base de datos:
postgresql://postgres:postgres@localhost:5432/gidas_db

Ejecucion local
1. Crear y activar entorno virtual.
   python -m venv venv
2. Instalar dependencias:
   pip install -r requirements.txt
3. Configurar variables de entorno en .env.
4. Aplicar migraciones:
   flask db upgrade
5. Ejecutar la aplicacion:
   python app.py

La API se inicia por defecto en:
http://0.0.0.0:5000

Migraciones
El esquema se administra con Alembic a traves de Flask-Migrate.

Comandos habituales:
- flask db upgrade
- flask db migrate -m "mensaje"
- flask db downgrade
- flask db heads

Antes de continuar una linea de desarrollo importante, conviene verificar que exista un unico head activo.

Tests
La carpeta tests contiene tests unitarios y de integracion liviana.
Estos tests validan principalmente:
- reglas de negocio de los services
- auditoria por campo
- transiciones de estado de memoria
- generacion de snapshots por cierre
- criterio de pertenencia por periodo activo
- permisos de rutas y middleware
- contrato HTTP basico entre rutas, controller y service

Ejemplos de ejecucion:
- venv\Scripts\python -m unittest discover -s tests -v
- venv\Scripts\python -m unittest tests.test_memoria_service tests.test_memoria_routes -v

Datos ficticios de testing
Para operar el frontend contra una base de testing con datos minimos, levantar el entorno de testing y ejecutar:
- docker compose --env-file .env.testing -f docker-compose.yml -f docker-compose.dev.yml exec backend python tools/seed_testing_data.py

El script crea usuarios de prueba, catalogos basicos, grupo, personas, proyecto y una memoria abierta.
Credenciales generadas:
- admin.testing / Testing123!
- gestor.testing / Testing123!
- lector.testing / Testing123!

El script esta protegido para no ejecutarse accidentalmente sobre produccion: requiere APP_ENV=testing o ALLOW_TEST_SEED=true.

Para consultar la base con psql desde Docker:
- docker compose --env-file .env.testing -f docker-compose.yml -f docker-compose.dev.yml exec db psql -U postgres -d gidas_testing_db

Si se ejecutan los tests con el Python global, pueden faltar dependencias locales como Flask-Limiter aunque esten declaradas en requirements.txt. Para validar el backend debe usarse el entorno virtual del modulo o instalar previamente requirements.txt en el interprete activo.

Docker y produccion
El backend se construye con Dockerfile multi-stage:
- builder: compila wheels de dependencias.
- runtime: instala dependencias desde wheels, copia la aplicacion y ejecuta con usuario no root.
- development: conserva herramientas minimas para desarrollo local.
- production: imagen final para despliegue.

En produccion el servicio efimero `migrate` aplica migraciones, ejecuta el seed y concede permisos. Gunicorn inicia despues usando solamente `DATABASE_URL` de `gidas_app`, sin recibir credenciales administrativas.

Historial de directivos por grupo

- Endpoint: GET /api/v1/grupo/directivos/grupo/<grupo_id>
- Permisos: ADMIN, GESTOR y LECTURA.
- Devuelve todos los periodos directivos activos en trazabilidad, incluidos los finalizados.
- Orden: fecha_inicio descendente e id descendente.
- Campos: id, id_directivo, nombre_apellido, cargo, fecha_inicio y fecha_fin.
- Las relaciones directivo y cargo se precargan para evitar consultas N+1.

Seed inicial

El entrypoint ejecuta `python seed_roles.py` despues de aplicar migraciones.
El script es idempotente y garantiza los roles base junto con los cargos
`Director` y `Vicedirector`. Si uno de esos cargos existe con soft delete, el
seed lo restaura.

Validacion de busqueda por modulo

Con PostgreSQL y el backend local configurados, ejecutar
`python tools/verify_search_retrieval.py`. El verificador es de solo lectura y
exige recuperar un registro activo con ID, tipo y URL correctos para cada uno de
los 24 modulos incluidos en la busqueda global.

Observabilidad

Produccion utiliza logs JSON en stdout con `X-Request-ID`, servicio, entorno y
version. `/api/v1/health/live` valida el proceso y `/api/v1/health/ready` valida
PostgreSQL y Redis. Los secretos se redactan como `[REDACTED]`. Los detalles de
traceback se omiten en produccion y solo se conserva el tipo de excepcion. El
`X-Request-ID` recibido se acepta unicamente si posee hasta 128 caracteres del
conjunto alfanumerico, punto, guion, guion bajo o dos puntos; en otro caso se
genera un UUID.

No registrar cuerpos completos, query strings, credenciales, cookies, tokens ni
datos personales. Las herramientas de testing tampoco deben imprimir
contrasenas en consola.

Variables obligatorias en produccion:
- APP_ENV=production
- SECRET_KEY
- JWT_SECRET
- REFRESH_SECRET
- JWT_ISSUER
- JWT_AUDIENCE
- DATABASE_URL
- FRONTEND_URL
- FRONTEND_URLS
- RATELIMIT_STORAGE_URI

Las claves SECRET_KEY, JWT_SECRET y REFRESH_SECRET deben tener al menos 32 caracteres y no pueden usar placeholders. La aplicacion falla al iniciar si detecta una configuracion insegura para produccion, CORS con comodin o ausencia de DATABASE_URL.

Controles de seguridad de API:

- las reglas funcionales nuevas usan excepciones tipadas de dominio
  (`ValidationError`, `NotFoundError`, `ConflictError`, `ForbiddenError`). Solo
  sus mensajes se exponen al cliente; las excepciones inesperadas responden
  `INTERNAL_ERROR` con `request_id` y se registran únicamente por tipo.
- el modulo de memorias aplica este contrato a consultas, snapshots,
  transiciones, versionado y exportaciones, preservando estados 400, 404, 409 y
  500 según la naturaleza del error.
- produccion migra por subdominios. Autores y documentacion bibliografica ya
  diferencian validaciones, inexistencias, conflictos relacionales y fallas
  internas sin exponer excepciones de persistencia.
- CORS restringido por FRONTEND_URLS en produccion.
- rate limit global y limites especificos para autenticacion.
- almacenamiento de rate limit en Redis interno para evitar contadores aislados por worker.
- headers defensivos: X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy y HSTS cuando DEBUG esta desactivado.
- cookies de sesion con HttpOnly, SameSite y Secure en produccion.
- el refresh token se entrega exclusivamente en la cookie `gidas_refresh`, con
  `HttpOnly`, `SameSite=Lax`, `Path=/api/v1/auth` y `Secure` en produccion.
- login, registro inicial y refresh devuelven el access token y el usuario seguro,
  pero nunca incluyen el refresh token en JSON. Las respuestas usan
  `Cache-Control: no-store`.
- refresh y logout solo leen la cookie y validan `Origin` o, si esa cabecera no fue
  enviada, `Referer`, contra `FRONTEND_URLS` antes de rotar o revocar sesiones.
- logout es idempotente y, en solicitudes de origen confiable, siempre expira la
  cookie incluso si falta o es invalida. Un origen hostil se rechaza sin modificarla.
- ejecucion en contenedor no root, filesystem read-only desde Compose y capacidades Linux reducidas.
- autenticacion no refleja excepciones internas, detalles de persistencia ni la
  existencia de usuarios, correos o tokens en sus respuestas de error.

No se deben versionar archivos .env reales. Los archivos .env.example y .env.production.example son plantillas y sus valores deben reemplazarse antes de desplegar.

Alcance actual de los tests
Los tests estan orientados a logica de backend y contratos del sistema. No reemplazan:
- la validacion final sobre base real
- la verificacion funcional completa de snapshots de memoria
- la validacion integral de la exportacion Excel

Eso debe hacerse una vez cerrada la integracion funcional del modulo de memorias y del flujo de exportacion.

Consideraciones de mantenimiento
- Los models deben contener solo entidades y relaciones.
- Las transiciones de estado y reglas del dominio viven en services.
- Toda nueva entidad que participe del contenido final de memoria debe evaluarse en dos planos:
  1. historial consumible para frontend
  2. snapshot historica al cierre de MemoriaVersion
- La exportacion Excel debe consumir la ultima version cerrada de memoria y no las tablas vivas.
- Los catalogos del sistema no requieren el mismo tratamiento historico que las entidades de negocio, salvo que el dominio lo exija explicitamente.

Estado funcional del backend
El backend ya representa una base estable para:
- evolucion del modulo de memorias
- consolidacion de historiales consumibles
- armado de snapshots historicas
- control de pertenencia por periodo activo
- futura integracion final de exportacion Excel basada en version cerrada

Proximo foco recomendado
El siguiente bloque natural del sistema es la exportacion Excel.
La implementacion final debe apoyarse en:
- la ultima version cerrada de memoria
- las snapshots historicas persistidas para cada entidad relevante
- el criterio de pertenencia temporal ya definido por el dominio

Este archivo debe actualizarse cuando cambie la arquitectura de memorias, la estrategia de auditoria, el criterio de pertenencia temporal o el contrato principal de exportacion.
