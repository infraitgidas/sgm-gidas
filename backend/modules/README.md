# Backend modular

## Errores accionables (ISS-09)

Se mantiene el contrato `{data: null, error: {code, message, details}}`.
Los manejadores globales y `exception_response` convierten las excepciones de
dominio en 400/401/403/404/409 y las fallas inesperadas en 500. Los errores HTTP
400/422, 401, 403, 404, 409 y 500 usan el mismo sobre seguro.

`details.fields` conserva las claves estables del contrato API con mensajes
públicos en español. `shared/services/error_messages.py` traduce los nombres
internos conocidos de las validaciones heredadas; no infiere campos desde SQL,
claves desconocidas o palabras ambiguas. Los validadores nuevos deben declarar
`details.fields` explícitamente. Se eliminan detalles internos no documentados.
El estado público de dependencias del healthcheck conserva su contrato.

`details.request_id` coincide con `X-Request-ID` y con el identificador registrado
en los logs de petición y error. Una excepción inesperada siempre muestra el
mensaje seguro, sin SQL, trazas ni información de conexión.

## Contrato transversal de fechas institucionales

`modules.shared.services.date_time.validate_institutional_date` establece el
01/01/2010 como límite inferior de los hechos vinculados con la vida del grupo.
Los services deben invocarlo después de parsear el payload y pueden conservar o
restringir fechas futuras según la regla de negocio del dominio.

Este directorio organiza el backend como monolito modular. Cada modulo agrupa
archivos por responsabilidad tecnica interna:

- `models`: modelos SQLAlchemy y relaciones persistentes.
- `services`: reglas de negocio, validaciones, auditoria y consultas.
- `controllers`: adaptacion HTTP, payloads y respuestas.
- `routes`: blueprints Flask, permisos y endpoints.

`modules/__init__.py` expone el registro central de blueprints usado por la
aplicacion. `modules/models_registry.py` importa explicitamente los modelos
modulares para registrar la metadata de SQLAlchemy durante el arranque. La
carpeta legacy previa a la modularizacion fue eliminada; los imports historicos
ya no forman parte del contrato interno del backend.

## Versionado de API

Los blueprints se registran unicamente bajo `/api/v1`. No hay endpoints
publicos legacy sin prefijo.

La nomenclatura versionada se centraliza en
`modules.shared.routes.versioning.VERSIONED_PREFIXES`, agrupando endpoints por
dominio cuando corresponde. Ejemplos:

- `/api/v1/catalogos/fuente-financiamiento`
- `/api/v1/personal/investigadores`
- `/api/v1/recursos/becas`
- `/api/v1/produccion/articulos-divulgacion`
- `/api/v1/proyectos`
- `/api/v1/transferencia/transferencias`
- `/api/v1/grupo/cargos`

Toda respuesta servida desde `/api/v1` debe incluir el header:

```text
API-Version: v1
```

### Contrato temporal

- Las columnas `Date` se serializan como fechas civiles `YYYY-MM-DD`, sin zona
  horaria ni conversion de dia.
- Las columnas `DateTime` de auditoria representan instantes UTC y se serializan
  en ISO 8601 con sufijo `Z`.
- Los datetimes historicos almacenados sin zona se interpretan como UTC al salir
  por la API, de acuerdo con el uso de `datetime.utcnow()` del modelo.
- La serializacion comun reside en
  `modules.shared.services.date_time.serialize_temporal` y debe reutilizarse en
  historiales y nuevos modelos auditables.

Regla de compatibilidad:

- Cambios compatibles permanecen en v1: campos opcionales, endpoints nuevos y filtros nuevos.
- Cambios incompatibles deben ir a una version nueva, por ejemplo v2.
- El frontend debe consumir la API con base versionada, por ejemplo
  `VITE_API_BASE_URL=/api/v1` o una URL equivalente que termine en `/api/v1`.

## Modulos

- `auth`: usuarios, roles, personas asociadas, login, registro y cambio de
  contrasena.
- `catalogos`: catalogos transversales como categorias UTN y fuentes de
  financiamiento.
- `dashboard`: consultas agregadas para vista general.
- `grupo`: grupo UTN, directivos, cargos, planificacion, programas y visitas.
- `memorias`: periodos, versiones, exportacion y reglas de armado de memoria.
- `personal`: investigadores, becarios, personal, tipos de dedicacion,
  formacion y personal.
- `produccion`: produccion academica y cientifica, autores, documentacion,
  registros, distinciones y actividades docentes.
- `proyectos`: proyectos de investigacion, tipos de proyecto y participaciones
  relevantes.
- `recursos`: becas, equipamiento, erogaciones y tipos de erogacion.
- `search`: busqueda transversal y registro de entidades buscables.
- `shared`: auditoria, mixins, middleware, validaciones y healthcheck.
- `transferencia`: transferencia socio-productiva, adoptantes y contratos.

## Convenciones

- Las nuevas funcionalidades deben agregarse dentro del modulo de dominio
  correspondiente.
- Los imports deben usar `modules.<modulo>...`.
- No agregar nuevas fachadas legacy; cualquier compatibilidad historica debe
  resolverse migrando el import al modulo correspondiente.
- Los endpoints deben declarar permisos en `routes` y delegar reglas de negocio
  a `services`.
- Todo cambio con historial o auditoria debe reutilizar los servicios de
  `shared` y las reglas existentes de `memorias` cuando corresponda.

## Auth y sesiones refresh

El modulo `auth` emite access tokens JWT de vida corta y refresh tokens de 7
dias. Los refresh tokens se persisten en `refresh_token_session` guardando solo
su hash SHA-256, nunca el token plano.

Contrato operativo:

- Login y registro emiten `access_token` y `refresh_token` y registran la
  sesion refresh con `jti`, usuario, expiracion, user agent e IP cuando estan
  disponibles.
- `/api/v1/auth/refresh` rota el refresh token en cada uso: revoca el token
  usado, crea una sesion nueva y devuelve `access_token` y `refresh_token`.
- Un refresh token revocado, vencido, no registrado o asociado a usuario
  inactivo se rechaza.
- `/api/v1/auth/logout` revoca el refresh token enviado.
- Cambiar contrasena o eliminar un usuario revoca sus sesiones refresh activas.

Retencion recomendada:

- Conservar sesiones vencidas o revocadas durante 90 dias para trazabilidad.
- Purgar registros antiguos con una tarea de mantenimiento futura, filtrando por
  `expires_at` y `revoked_at`.

## Contrato de respuestas API

Las nuevas rutas y las migraciones progresivas deben usar los helpers de
`modules.shared.controllers.responses` para responder con una estructura estable.
El contrato base de exito es:

```json
{
  "data": {},
  "meta": {},
  "error": null
}
```

El contrato paginado agrega metadata estandar:

```json
{
  "data": [],
  "meta": {
    "page": 1,
    "per_page": 9,
    "total": 42,
    "total_pages": 5
  },
  "error": null
}
```

El contrato de error evita exponer detalles internos:

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

Helpers disponibles:

- `success_response(data=None, meta=None, status_code=200)`.
- `paginated_response(data, page, per_page, total, meta=None, status_code=200)`.
- `error_response(code, message=None, details=None, status_code=400)`.

Los endpoints nuevos o versionados deben responder con `data`, `meta` y
`error`.

## Contrato de paginacion de listados

Los listados migrados deben aceptar estos parametros:

- `page`: pagina solicitada, entero positivo. Valor por defecto `1`.
- `per_page`: elementos por pagina, entero positivo. Valor por defecto `9`.
- `activos`: filtro de estado. Valores validos `true`, `false` o `all`.
- `orden`: direccion de ordenamiento. Valores validos `asc` o `desc`.

El limite general se configura con:

- `PAGINATION_DEFAULT_PER_PAGE`: por defecto `9`, alineado a homes.
- `PAGINATION_MAX_PER_PAGE`: por defecto `100`.

Los listados existentes conservan su lista plana si el cliente no envia `page`
ni `per_page`. Cuando envia alguno de esos parametros, cada controlador obtiene
el total con `count` y limita las filas en SQL antes de serializar. Responde con
`data`, `meta` (`page`, `per_page`, `total`, `total_pages`) y `error`. Las rutas
que ya tenian `meta.activos`, `meta.orden` y `meta.source = "legacy-list"`
conservan esas claves por compatibilidad; `source` ya no indica que la pagina
se calcule en memoria. El hook global `after_request` fue retirado. Nuevos
listados deben implementar la paginacion en su propio service.

Esta regla cubre catalogos, grupo, memorias y sus snapshots, personal,
produccion, proyectos, recursos, transferencia, usuarios, selectores UCT,
borradores e historiales. Los permisos y el alcance UCT se aplican antes del
conteo y del limite; el orden estable evita duplicados entre paginas. Los
historiales mantienen tres eventos por pagina donde corresponde. La busqueda
global conserva su payload propio y pagina candidatos mediante una union SQL.
