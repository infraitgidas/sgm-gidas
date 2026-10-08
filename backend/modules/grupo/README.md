# Modulo backend de grupo

Los nombres de directivos admiten solo letras Unicode y espacios. Facultad
regional y nombre/sigla del grupo requieren alguna letra. Los errores
identifican el campo en `details.fields`.

Las altas de directivos y sus períodos indican `nombre_apellido`, `id_cargo`, `fecha_inicio` o `fecha_fin` mediante `error.details.fields` cuando el control admite corrección.

POST `/api/v1/grupo/directivos/crear-y-asignar` requiere ADMIN o GESTOR y recibe `nombre_apellido`, `id_grupo_utn`, `id_cargo` y `fecha_inicio`. Crea y asigna dentro de una sola transacción: un rechazo revierte ambos pasos. Los endpoints separados permanecen disponibles para otros clientes.

## Contrato de fechas

Visitas y mandatos directivos se validan desde el 01/01/2010. Los mandatos no
admiten fechas futuras y su finalización debe ser igual o posterior al inicio.

## Responsabilidad

Gestiona la UCT, directivos, cargos, programas, planificaciones y visitas
academicas. Todas las rutas de dominio requieren rol.

## Historial de campos de UCT (ISS-80)

`PUT /api/v1/grupo/grupo-utn/` admite diferencias de
`nombre_unidad_academica`, `nombre_sigla_grupo`, `mail` y
`objetivo_desarrollo`. El service recorta espacios, valida los valores y registra
una fila por campo realmente modificado en `auditoria_campo` con entidad
`grupo_utn`, valores anterior y nuevo, autor y fecha. Un guardado sin cambios no
genera eventos ni actualiza la auditoria del registro. El alta conserva los datos
iniciales sin construir un historial retroactivo.

`GET /api/v1/grupo/grupo-utn/{id}/historial` devuelve los eventos ordenados del
mas reciente al mas antiguo. Requiere `ADMIN`, `GESTOR` o `LECTURA` y responde
`NOT_FOUND` si el ID no corresponde a la UCT visible o el grupo fue eliminado.
Los errores de dominio mantienen el contrato `error.code`, `error.message` y
`error.details`. Los periodos de directivos permanecen en su endpoint propio y
no se presentan como cambios de campos del grupo.

## Planificaciones

Endpoints principales:

```text
GET    /api/v1/grupo/planificaciones/?page=1&per_page=9&activos=true
POST   /api/v1/grupo/planificaciones/
GET    /api/v1/grupo/planificaciones/{id}
PUT    /api/v1/grupo/planificaciones/{id}
DELETE /api/v1/grupo/planificaciones/{id}
GET    /api/v1/grupo/planificaciones/{id}/historial
```

El listado conserva compatibilidad sin parametros y adopta el contrato
paginado transversal cuando recibe `page` o `per_page`.

La actualizacion acepta payload parcial, valida unicidad por grupo y año,
registra solamente campos modificados y asigna `updated_by`.

## Visitas y tipos de visita (ISS-37)

Las visitas utilizan el catálogo propio `TipoVisita`. La relación
`tipo_visita_id` ya no depende de `TipoReunion`; el resto de los tipos de
encuentro permanece sin cambios. Las visitas vigentes y los snapshots cerrados
de Memorias referencian `tipo_visita`, y los snapshots conservan además el
nombre congelado para trazabilidad histórica.

Endpoints de visitas:

```text
GET    /api/v1/visitas-academicas/?activos=true|false|all
POST   /api/v1/visitas-academicas/
GET    /api/v1/visitas-academicas/{id}
PUT    /api/v1/visitas-academicas/{id}
DELETE /api/v1/visitas-academicas/{id}
GET    /api/v1/visitas-academicas/{id}/historial
```

El alta recibe `razon`, `fecha`, `procedencia`, `tipo_visita_id` y
`grupo_utn_id`. La edición admite un payload parcial y registra únicamente las
diferencias reales. `tipo_visita_id` debe identificar un tipo activo del
catálogo propio; `procedencia` continúa representando el origen de la visita
como texto.

Endpoints del catálogo:

```text
GET    /api/v1/grupo/tipos-visita/?activos=true|false|all
POST   /api/v1/grupo/tipos-visita/
PUT    /api/v1/grupo/tipos-visita/{id}
DELETE /api/v1/grupo/tipos-visita/{id}
GET    /api/v1/grupo/tipos-visita/{id}/historial
```

El catálogo recibe `{ "nombre": string }`, normaliza espacios, exige un nombre
descriptivo y evita duplicados sin distinguir mayúsculas. Sus registros son
auditables, usan baja lógica y no pueden eliminarse mientras tengan visitas
asociadas. Lectura e historial admiten `ADMIN`, `GESTOR` y `LECTURA`; las
mutaciones requieren `ADMIN` o `GESTOR`.

La revisión `d8f3a6c1b5e2` crea `tipo_visita`, incorpora `Académica` e
`Intercambio`, retira el dataset anterior de visitas de prueba y cambia las
claves foráneas de visitas y snapshots. El seed de testing regenera las visitas
contra el catálogo independiente.

## Directivos

Las relaciones entre directivo, cargo y grupo mantienen periodos de vigencia.
El frontend acumula cambios hasta guardar la UCT; las operaciones backend
continuan protegidas individualmente y registran historial relacional.

`Directivo` contiene el nombre y la UCT propietaria; `DirectivoGrupo` contiene
el cargo y las fechas de cada mandato. `POST /api/v1/grupo/directivos/crear-y-asignar`
recibe `nombre_apellido`, `id_grupo_utn`, `id_cargo` y `fecha_inicio` (`YYYY-MM-DD`).
`PUT /api/v1/grupo/directivos/{id}` recibe `nombre_apellido`; solo registra una
diferencia si el valor cambia. `PUT /api/v1/grupo/directivos/finalizar` recibe
`id_directivo`, `id_grupo_utn` y `fecha_fin`. Una asignacion de un directivo sin
UCT fija su propietaria despues de descartar vinculos vigentes con otra UCT; una
asignacion de un directivo propiedad de otra UCT se rechaza.

`GET /api/v1/grupo/directivos/grupo/{id}` devuelve los periodos con nombre,
cargo, fecha de inicio y fin. `GET /api/v1/grupo/directivos/grupo/{id}/actuales`
devuelve solo los mandatos sin fecha de fin. Estas listas representan periodos,
no eventos de auditoria.

`GET /api/v1/grupo/directivos/grupo/{id}/cambios?page=1` responde
`{ items, page, per_page: 3, total }`, con eventos del mas reciente al mas antiguo.
Cada item contiene `entidad`, `campo`, `valor_anterior`, `valor_nuevo`,
`fecha_cambio` y `usuario_nombre`. El cambio de nombre pertenece a `directivo`;
la asignacion y finalizacion pertenecen a `directivo_grupo`, con `campo: mandato`
y `valor_nuevo: { accion, detalle }`. `detalle` incluye nombre, cargo y fechas.
La consulta exige que la UCT exista y no este eliminada; solo incluye mandatos
de esa UCT y nombres de directivos cuya UCT propietaria coincide. No reconstruye
eventos de mandatos anteriores a esta auditoria. Los tres endpoints de lectura
requieren ADMIN, GESTOR o LECTURA; las mutaciones requieren ADMIN o GESTOR.
Una pagina invalida responde `VALIDATION_ERROR`; una UCT inexistente o fuera
del alcance responde `NOT_FOUND`.

Cada UCT puede tener activos como maximo un `Director` y un `Vicedirector`. La
asignacion rechaza cargos diferentes, cargos inactivos, un cargo institucional ya
ocupado o un equipo que ya tenga cubiertos ambos cargos. Los periodos finalizados
se conservan para trazabilidad y no consumen el cupo activo.

La serializacion de la UCT incluye solamente participaciones vigentes y sin baja
logica cuyos directivo y cargo tambien permanezcan activos. El endpoint especifico
de directivos actuales mantiene el mismo criterio para el formulario y la home.

## Permisos

- lectura e historial: `ADMIN`, `GESTOR`, `LECTURA`
- altas, cambios, asignaciones, finalizaciones y bajas: `ADMIN`, `GESTOR`

## Auditoria y baja

- las entidades auditables usan `AuditMixin`
- las planificaciones registran historial bajo `planificacion_grupo`
- las bajas aplicables son logicas y preservan trazabilidad
- el historial se ordena desde el cambio mas reciente

## Pruebas relacionadas

- `tests/test_planificacion_historial.py`
- `tests/test_directivo_cargos.py`
- `tests/test_pagination.py`
- pruebas de auditoria de relaciones y visitas
- `tests/test_grupo_domain_errors.py`
- `tests/test_tipo_visita_catalog.py`
- `tests/test_catalog_name_validation.py`

## Contrato de errores

Los services distinguen validaciones (`VALIDATION_ERROR`), recursos inexistentes
(`NOT_FOUND`) y conflictos de estado (`CONFLICT`). Los controladores serializan
unicamente errores de dominio conocidos; una falla inesperada responde
`INTERNAL_ERROR` con `request_id` y no expone detalles internos.

## Integración con memorias (ISS-16)

GET `/api/v1/grupo/grupo-utn/opciones` devuelve `{id, nombre}` de las UCT activas a ADMIN, GESTOR y LECTURA. Al cerrar una memoria se congelan la UCT, sus autoridades vigentes durante el período y la planificación del año siguiente; cambios actuales no alteran esa versión ni su Excel.

## Validaciones de Visitas (ISS-19)

El service de visitas responde VALIDATION_ERROR con error.details.fields para razon, procedencia, fecha, tipo_visita_id y grupo_utn_id cuando identifica el dato inválido. Las validaciones ocurren antes de persistir y conservan el rollback existente.

UCT identifica los campos obligatorios `nombre_unidad_academica`, `nombre_sigla_grupo`, `mail` y `objetivo_desarrollo`. Planificaciones identifica `descripcion` y `anio`, incluido un año ya planificado; los errores sin un control inequívoco mantienen un mensaje general.
# Paginacion SQL (ISS-89)

Programas, planificaciones, tipos de visita, visitas y directivos limitan las
filas en SQL antes de serializar. Directivos actuales y por grupo conservan
sus filtros de vigencia y grupo. El selector de UCT y los historiales mantienen
el alcance autorizado; las respuestas planas sin `page`/`per_page` y los
metadatos paginados existentes siguen disponibles.
