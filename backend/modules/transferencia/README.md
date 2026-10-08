# Modulo backend de transferencia

El nombre de adoptante admite solo letras Unicode y espacios, tanto al crear
como al editar. Denominación y demandante requieren alguna letra. Los errores
identifican el campo en `details.fields`.

## Contrato de fechas

Los períodos de transferencia se validan desde el 01/01/2010 y el fin no puede
ser anterior al inicio, tanto en alta como en edición.

## Responsabilidad

Gestiona transferencias socio-productivas, tipos de contrato, adoptantes y sus
relaciones, incluyendo auditoria, baja logica e historial.

## Adoptantes e historial propio (ISS-83)

`/adoptantes` permite consultar, crear, editar y dar de baja adoptantes. `GET`
acepta `activos=true|false|all`; el valor predeterminado es `true`, para que los
selectores de transferencias reciban solo registros vigentes. `GET /:id/historial`
devuelve cambios del adoptante ordenados por fecha e ID descendentes, incluso si
el adoptante fue dado de baja. Los GET admiten `ADMIN`, `GESTOR` y `LECTURA`;
POST, PUT y DELETE exigen `ADMIN` o `GESTOR`. Todas las consultas y escrituras
respetan el alcance de la UCT asignada al usuario.

El modelo `Adoptante` conserva `nombre`, `grupo_utn_id`, estado y metadatos de
auditoria. POST recibe `{ "nombre": string }`; PUT acepta la diferencia de
`nombre`. El nombre exige letras Unicode y espacios, se recorta y no puede
duplicar otro adoptante activo. PUT sin cambio real no genera historial ni
actualiza la fecha. Al cambiarlo, se registra una fila `auditoria_campo` para
`nombre`, con valor anterior, nuevo, autor y fecha. DELETE realiza baja logica y
registra `activo: true -> false`; responde `CONFLICT` si existe un vinculo
vigente con una transferencia activa. Los errores de nombre incluyen
`error.details.fields.nombre` cuando corresponde.

`AdoptanteTransferencia` conserva las altas y bajas de relaciones. Sus eventos
`vincular` y `desvincular` permanecen exclusivamente en el historial de la
transferencia; no se duplican en el historial de campos del adoptante.

## API y permisos

El blueprint `/transferencias` expone GET `/`, GET `/:id`, GET `/:id/historial`,
POST `/`, PUT `/:id` y DELETE `/:id`. Los GET admiten `ADMIN`, `GESTOR` y
`LECTURA`; las escrituras requieren `ADMIN` o `GESTOR`. El listado acepta
`grupo_utn_id`, `tipo_contrato_id` y `activos`. Los endpoints separados POST y
DELETE `/:id/adoptantes` conservan su contrato `adoptantes_ids` para clientes
existentes. `/adoptantes` expone el catálogo con lectura para los tres roles y
escritura para `ADMIN` y `GESTOR`.

## Número y guardado de adoptantes

El cliente no asigna `numero_transferencia`. En el alta, el service calcula
`max(numero_transferencia) + 1` sobre todos los registros, incluidas las bajas
lógicas; ignora un número enviado por clientes anteriores. En PostgreSQL usa un
bloqueo transaccional consultivo para serializar la asignación concurrente. El
número persiste en `TransferenciaSocioProductiva` y se devuelve en la respuesta.

POST `/transferencias` acepta los campos de transferencia existentes y,
opcionalmente, `adoptantes_ids: number[]` y `adoptantes_nuevos: string[]`.
PUT `/transferencias/:id` acepta solo los campos modificados. Si recibe alguna
de esas dos claves, interpreta ambas listas como la selección final: los IDs
existentes se vinculan, los nombres nuevos se crean en `Adoptante` y se vinculan,
y los vínculos ausentes se dan de baja lógicamente. Una petición sin ambas claves
conserva los vínculos. La creación del catálogo, la actualización de relaciones,
la auditoría y la transferencia comparten la misma transacción; el cliente recibe
éxito solo después del commit.

Los nombres nuevos se normalizan con espacios simples y deben contener letras
Unicode y espacios. Se rechazan IDs inválidos o repetidos, adoptantes inactivos y
nombres nuevos vacíos, repetidos o ya disponibles en el catálogo. Las relaciones
usan `AdoptanteTransferencia`; vincular y desvincular registran eventos de
historial con ID y nombre. La edición del tipo de contrato valida un tipo activo
y registra el cambio de campo. La baja de transferencias sigue siendo lógica.

## Contrato de errores

Los services distinguen validaciones (`VALIDATION_ERROR`), recursos inexistentes
(`NOT_FOUND`) y conflictos (`CONFLICT`). Los controladores usan el serializador
central y las fallas inesperadas responden `INTERNAL_ERROR` con `request_id` sin
exponer datos internos.

ISS-19: número, denominación, demandante, descripción, monto, fechas y tipo de contrato devuelven `error.details.fields` cuando identifican un dato editable. Las claves corresponden al payload HTTP; las fallas de grupo o relación sin control inequívoco permanecen como aviso general seguro.

Las altas y bajas de la relación de adoptantes responden con `error.details.fields.adoptantes_ids` si la selección no es válida. Un adoptante que ya no está disponible conserva `NOT_FOUND` y señala el selector.

El guardado consolidado señala errores de `adoptantes_ids` también cuando un
nombre nuevo o la selección final no es válida. El número automático no produce
errores de validación de entrada. Los controladores devuelven respuestas seguras
sin exponer excepciones internas.

El alta y la edición de un adoptante indican `nombre` si falta o está duplicado.

## Pruebas relacionadas

- `tests/test_transferencia_domain_errors.py`
- `tests/test_transferencia_memoria_historial.py`
- `tests/test_transferencia_autonumero.py`: asignación automática, descarte del
  número del cliente y persistencia conjunta de catálogo y vínculos.

## Snapshots de memorias (ISS-16)

Las transferencias se filtran por UCT y por solapamiento entre inicio, finalización, baja y período. Los adoptantes y vínculos vigentes quedan congelados con el snapshot padre; una baja posterior al inicio del período no borra la relación histórica.
# Paginacion SQL (ISS-89)

Adoptantes, tipos de contrato y transferencias consultan el total filtrado y
limitan las filas en SQL antes de serializar. Se mantienen el array sin
`page`/`per_page`, el contrato paginado `data`/`meta`/`error`, los filtros,
permisos y el alcance UCT. Los historiales conservan tres eventos por pagina.

## Listado paginado y carga de relaciones (ISS-94)

`GET /api/v1/transferencia/transferencias/?view=table&page=1&per_page=9`
ejecuta busqueda, filtros, conteo y orden en SQL. Acepta `activos`, `q`,
`direction`, `ids` y `filter_tipo`, `filter_grupo`, `filter_anio`.
El home ordena por `sort=denominacion`; el service tambien admite numero,
demandante, descripcion, tipo, grupo y anio. El anio corresponde al inicio
de la transferencia. La busqueda incluye adoptantes vinculados sin baja,
con el mismo alcance UCT que los registros serializados.

La respuesta contiene `data` y `meta` de paginacion, con
`options.tipo`, `options.grupo` y `options.anio` como pares
`value/label`. Las opciones abarcan todo el alcance activo/memoria,
independientemente de la pagina o filtros de busqueda seleccionados.
Sin `view=table` se conserva la lista anterior y su paginacion opcional.

El service precarga participaciones/adoptantes, contrato y grupo, evitando
consultas por cada transferencia. En snapshots usa la relacion ORM para
asignar la FK del adoptante al persistir, sin flush por transferencia.
Se mantienen permisos, auditoria, bajas logicas y validacion UCT.
Las pruebas de tablas y ausencia de consultas por registro estan en
`tests/test_tenant_scope.py`; la suite completa conserva las pruebas
de relaciones, snapshots y paginacion anteriores.
