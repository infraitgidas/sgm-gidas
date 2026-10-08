# Producción

## ISS-82: autores de documentación bibliográfica

`Autor` pertenece a una UCT, incorpora auditoría y usa baja lógica. La revisión
`d5a7e9c1b3f2` agrega las columnas de auditoría a los autores existentes sin
reconstruir eventos anteriores. Las lecturas se aíslan por UCT; ADMIN, GESTOR y
LECTURA pueden consultar, mientras que solo ADMIN y GESTOR pueden modificar.

La base de las rutas es `/api/v1/produccion/autores`. `GET /` admite
`activos=true|false|all` (`true` por defecto), `GET /<id>` devuelve el autor y
`GET /<id>/historial` devuelve los cambios del autor. `POST /` recibe
`{ "nombre_apellido": "..." }`; `PUT /<id>` admite ese campo cuando cambia;
`DELETE /<id>` aplica soft delete. Los nombres aceptan letras Unicode y
espacios, se recortan y normalizan; un nombre ya usado en la misma UCT se
rechaza. La respuesta incluye ID, UCT, nombre, estado y marcas de auditoría.
Las entradas inválidas devuelven error de validación, los duplicados y las
bajas no permitidas devuelven conflicto, y los registros de otra UCT no se
resuelven.

Un cambio real de nombre registra una sola entrada `nombre_apellido` con valor
anterior, nuevo, usuario y fecha. Repetir el mismo nombre no registra un evento
ni actualiza las marcas de modificación. La baja registra el cambio de estado.
Solo una vinculación con documentación activa impide dar de baja al autor; los
vínculos con documentación inactiva permanecen y permiten la baja lógica. Las
documentaciones activas muestran el nombre corregido; las versiones cerradas
de Memorias conservan el nombre almacenado en su snapshot.

`POST /<id>/libros` y `DELETE /<id>/libros/<libro_id>` delegan en el servicio
de Documentación. Las vinculaciones y desvinculaciones se auditan únicamente
en `documentacion_bibliografica`, sin duplicarlas en el historial del autor.
El historial de Documentación expone solo sus campos bibliográficos y esos
eventos relacionales; omite cambios de nombre atribuidos por error al documento.

Validación: siete pruebas del flujo de autores, una prueba de upgrade y
downgrade en SQLite, cinco pruebas de historial de Documentación y Memorias y
21 pruebas de aislamiento UCT. La migración se aplicó en la base de desarrollo
y se comprobó el listado y una inserción revertida.

## ISS-39: Documentación y Biblioteca

Las rutas de `documentacion_bibliografica_bp` exponen
`GET /documentacion-bibliografica` con filtro `activos=true|false|all` y orden
opcional `orden=asc|desc`, `GET /documentacion-bibliografica/<id>` y
`GET /documentacion-bibliografica/<id>/historial`.
`POST /documentacion-bibliografica` crea con `titulo`, `editorial`, `anio`,
`fecha` (`YYYY-MM-DD`) y `grupo_id`. `PUT /documentacion-bibliografica/<id>`
acepta diferencias de esos campos; `DELETE /documentacion-bibliografica/<id>`
aplica baja lógica. `POST /documentacion-bibliografica/<id>/autores` recibe
`autor_id` y `DELETE /documentacion-bibliografica/<id>/autores/<autor_id>`
desvincula. Las lecturas admiten ADMIN, GESTOR y LECTURA; las escrituras
requieren ADMIN o GESTOR.

El controller propaga el usuario autenticado al service. El modelo
`DocumentacionBibliografica` conserva los campos bibliográficos, grupo,
autores y marcas de auditoría. La relación con `Autor` usa `autorxlibro`.
El service valida grupo activo, textos obligatorios y fecha institucional; en
el alta exige además un año entero. Rechaza relaciones inexistentes o
duplicadas y registros eliminados. Las
actualizaciones de campos generan auditoría solo ante diferencias reales.
Vincular o desvincular autores registra en el historial un evento `autores` con
`{ accion, detalle: { nombre_apellido } }` y el usuario responsable, preservando
el nombre para interpretar el evento después. El historial se obtiene por
entidad e ID, ordenado del evento más reciente al más antiguo.

Las respuestas serializadas incluyen datos de auditoría, grupo y autores. Los
errores de validación identificables usan `error.details.fields`; las ausencias
y conflictos conservan sus errores de dominio. Las llamadas de asociación se
confirman por separado tras la creación o actualización del documento, por lo
que el cliente consolida la selección antes de guardarla y envía cada diferencia
al finalizar. Los snapshots de Memorias conservan documento y autores asociados.

Validación: 9 pruebas backend focalizadas sobre historial, snapshots, auditoría
y eventos relacionales, además de las verificaciones frontend de ISS-39.

Los nombres de autores admiten solo letras Unicode y espacios. Los nombres de
revista, reunión y artículo de propiedad requieren alguna letra. ISSN conserva
su validación propia.

Los trabajos de reunión y revista identifican la selección de `autores` inválidos, repetidos o inactivos mediante `error.details.fields`. Un autor inexistente conserva el código `NOT_FOUND` y ofrece corrección junto al selector.

## Contrato de fechas

Las fechas de docencia, publicaciones, reuniones, distinciones, documentación
y propiedad intelectual se validan desde el 01/01/2010. Cada service conserva
su regla vigente respecto de fechas futuras y del orden de sus períodos.

## ISS-12: autoría de integrantes

Trabajos en reuniones científicas y revistas tienen una colección `autores`.
Cada referencia enviada es `{ "rol": "investigador" | "becario", "id": entero }`.
La identidad es `(rol, id)`: los IDs pueden coincidir entre las tablas de personal.
La respuesta agrega `nombre_apellido`, `tipo` y `activo`. Solo Investigador y
Becario pueden ser autores; Personal (PTAA/profesional) y externos se rechazan. No hay dos
colecciones independientes por categoría.

### Endpoints y payloads

Bases: `/api/v1/produccion/trabajos-reunion-cientifica` y
`/api/v1/produccion/trabajos-revistas`.

- `GET /`: lista con `activos`, `orden`, `autor_rol` y `autor_id`; estos dos
  últimos se envían juntos. Se conservan los filtros específicos de cada entidad.
- `GET /<id>`: datos, auditoría y autores, incluidas asociaciones históricas inactivas.
- `GET /<id>/historial`: cambios de campos y eventos `autores` con acción,
  nombre, categoría, origen e ID del integrante.
- `POST /`: payload anterior más `autores: [{rol, id}]`; crea el trabajo y
  vincula autores dentro de una única transacción.
- `PUT /<id>`: solo diferencias reales. `autores`, cuando está presente,
  reemplaza la colección completa con altas/bajas consolidadas. Omitirlo
  conserva la colección. Debe quedar al menos un autor; `[]` y la
  desvinculación del último autor se rechazan. No se auditan cambios inexistentes.
- `DELETE /<id>/autores`: `{ "autores": [{rol, id}] }` elimina únicamente
  esas asociaciones, también si el integrante está inactivo o eliminado.
- `DELETE /<id>` y `PUT /<id>/restore`: conservan soft delete y restauración.

Se retiraron las rutas `/investigadores`, el filtro `investigador_id` y el
campo exclusivo `investigadores`. Los consumidores deben usar el contrato nuevo.
Las lecturas requieren ADMIN/GESTOR/LECTURA; las escrituras ADMIN/GESTOR.

### Responsabilidades e integridad

`trabajo_autores_service.py` valida referencias y sincroniza asociaciones sin
commits; cada service de trabajo administra la transacción y su rollback ante
fallos de persistencia/auditoría. Las altas requieren integrantes existentes,
activos y no eliminados. Se pueden conservar y quitar asociaciones históricas;
no se pueden volver a agregar integrantes inactivos. Se rechazan roles inválidos,
IDs no enteros positivos y duplicados dentro de una misma categoría.

`TrabajoReunionAutor` y `TrabajoRevistaAutor` tienen FK al trabajo y a los dos
orígenes de integrantes. Un CHECK exige exactamente un origen por fila, UNIQUE
por trabajo/origen evita duplicados y los índices cubren todas las FK. La baja
física del trabajo elimina asociaciones; las FK de integrantes usan RESTRICT.
La baja funcional usa soft delete; los eventos relacionales permanecen en auditoría.
La carga `selectin` de autorías y la carga de integrantes evitan una consulta
por cada trabajo al listar o exportar.

### Memorias y entorno de testeo

Los snapshots almacenan `autores` como JSON con identidad, nombre y categoría
al cierre; cambios posteriores del integrante no alteran esa versión.
La exportación de memoria y la exportación de grupo muestran todos los autores
con su categoría. La plantilla de revistas conserva sus seis columnas y agrega
los autores en la celda de título, con encabezado `Titulo trabajo / Autores`.
La búsqueda global recupera trabajos por cualquier autor y devuelve `extra.autores`.

La revisión `a12b9c4d6e80` mantiene compatibilidad con `flask db upgrade`/Docker.
Por decisión del usuario, reemplaza el esquema sin copiar asociaciones ni textos
anteriores de snapshots; el downgrade solo restaura estructura. Regenerar los
datos de testing y cerrar nuevas versiones de memoria. El seed de testing agrega
autoría mixta a los trabajos sin autores y es idempotente. No se toca la instancia
existente durante las pruebas automatizadas, que usan SQLite temporal.

### Validación

`tests/test_trabajo_autores.py` verifica persistencia real, IDs coincidentes,
investigador/becario/mixtos, rechazo de Personal, datos inválidos, duplicados, CHECK/FK/UNIQUE,
altas/bajas consolidadas, auditoría, permisos, rollback de la transacción, búsqueda
global y exportación XLSX de snapshots inmutables. Las suites de historial,
memorias, errores de producción y exportaciones cubren las regresiones.

### Corrección de alcance

La revisión `b12c8d5e7f90`, posterior a la ya instalada `a12b9c4d6e80`, retira
las asociaciones con Personal, elimina su FK y actualiza el CHECK a exactamente
un investigador o becario. También elimina Personal de los snapshots de testing;
conserva los autores habilitados y la auditoría previa. El downgrade solo
restaura la estructura anterior, sin recuperar esas asociaciones. El seed
genera exclusivamente investigadores y becarios como autores para ambos trabajos.

## ISS-13: fecha de presentación de trabajos en reuniones

TrabajoReunionCientifica y TrabajoReunionCientificaMemoriaVersion usan
fecha_presentacion (Date no nula). POST/PUT y respuestas GET/snapshots usan
fecha_presentacion en YYYY-MM-DD. Solicitudes antiguas pueden enviar
fecha_inicio temporalmente; se normaliza a fecha_presentacion sin alterar
el payload original. Ambos campos iguales se aceptan; distintos se rechazan
con 400 y error de campo, sin cambios persistidos. La respuesta solo expone
el nombre nuevo. Se mantienen permisos y auditoría y la fecha mínima
2010-01-01. Se admiten fechas futuras para registrar presentaciones programadas.
Duplicados y orden asc/desc usan la nueva fecha.
La pertenencia a memoria usa su período inclusivo sobre fecha_presentacion:
31/12 corresponde al año que termina y 01/01 al siguiente. El snapshot congela
la fecha. La revisión c13d7e9a2b40 renombra las columnas de trabajos y snapshots,
conserva valores y admite downgrade que restaura los nombres anteriores.
Los eventos históricos conservan su campo original; nuevos eventos usan
fecha_presentacion. Tests reales: test_trabajo_fecha_presentacion.py verifica
API, alias, rechazo de conflictos, fechas inválidas, auditoría, orden, límites
anuales, XLSX y migración/downgrade preservando filas.

## ISS-14: enlace opcional de trabajos

Congresos/reuniones y revistas aceptan `enlace` opcional en POST/PUT y lo
exponen en GET y snapshots como string o null. Ausente en alta, null o texto
vacío se almacenan como null; ausente en edición conserva el valor previo.
Se recortan espacios exteriores sin alterar mayúsculas ni contenido del DOI.
Admite HTTP/HTTPS con host, hasta 2048 caracteres; rechaza otros protocolos,
URLs incompletas, credenciales, espacios internos, controles, barras inversas
y puertos inválidos. Un DOI debe ingresarse como URL https://doi.org/… .
Error 400 con `error.details.fields.enlace`; no se consulta el destino.
Los cambios reales, incluida la eliminación del enlace, se auditan en `enlace`.
Se conservan permisos, autores y soft delete del trabajo. No modifica duplicados.

La revisión d14e8f0a3c51 añade String(2048) nullable a ambos trabajos y sus
snapshots. Registros existentes quedan con null. Downgrade elimina las cuatro
columnas y sus valores, conservando las filas; no reconstruye URLs eliminadas.
Tests test_trabajo_enlace.py cubren API, rechazo atómico, historial sin duplicados,
snapshot inmutable, XLSX y upgrade/downgrade con registros existentes.

La validación también rechaza hosts inválidos; admite dominios internacionalizados
y hosts IPv6 válidos mediante los analizadores de URL de cada plataforma.

## Pertenencia a memorias (ISS-16)

Los generadores filtran por la UCT. Publicaciones, documentación, registros, distinciones y trabajos usan su fecha puntual dentro del rango inclusivo; docencia usa el intervalo completo y conserva los grados que estuvieron vigentes. Las bajas se interpretan históricamente.

## Errores de formularios (ISS-19, en curso)

Los servicios de artículos, distinciones, trabajos, docencia, documentación y registros de propiedad devuelven `error.details.fields` cuando una validación identifica texto, fecha o selección editable. Las claves son las del payload HTTP, entre ellas `fecha_publicacion`, `proyecto_investigacion_id`, `titulo_trabajo`, `nombre_reunion`, `tipo_reunion_id`, `curso`, `fecha_inicio`, `nombre_articulo` y `fecha_registro`. Los duplicados conservan `CONFLICT` y un mensaje general accionable.

## Historial y acciones de Docencia (ISS-27)

El historial de grados omite la asociacion inicial creada junto con la actividad,
porque forma parte del alta y no representa una modificacion. Los cambios
posteriores exponen `valor_anterior` y `valor_nuevo` como `{ id, nombre }` para su
presentacion legible.

Las pruebas de regresion verifican que `PUT /actividades-docencia/<id>` y
`DELETE /actividades-docencia/<id>` propagan el usuario autenticado y responden
200 en operaciones correctas. La eliminacion aplica `soft_delete` y confirma la
transaccion.

## Contrato de Registros de propiedad (ISS-28)

`RegistrosPropiedad.serialize()` expone las relaciones de lectura como valores
planos: `tipo_registro` contiene el nombre del tipo y `grupo` la sigla de la UCT.
Los identificadores permanecen en `tipo_registro_id` y `grupo_utn_id`; los
consumidores no deben depender de la representacion interna de SQLAlchemy.

El alta no registra inicializaciones como cambios de campos. En edicion,
`RegistrosPropiedadService.update` construye y persiste auditoria unicamente
cuando existe una diferencia real; enviar el mismo valor no actualiza la marca
de modificacion ni genera historial. El endpoint de historial conserva valores
JSON para compatibilidad con registros anteriores, por lo que el frontend debe
presentarlos mediante el contrato tipado y no por coercion a texto.

`tests/test_registro_propiedad_memoria_historial.py` cubre las garantias de alta
sin inicializaciones, edicion sin diferencias, lectura del historial y snapshots
de memorias.

## ISS-32: contrato de Trabajos en revistas

Trabajos en revistas usa el catálogo independiente `TipoRevista`, sin compartir
clasificaciones con reuniones científicas. El catálogo se administra en
`/api/v1/produccion/tipos-revista`; las lecturas y el historial admiten
ADMIN/GESTOR/LECTURA, mientras que las mutaciones requieren ADMIN o GESTOR.
Los datos iniciales de testing son `Nacional` e `Internacional`.

`TrabajosRevistasReferato` y sus snapshots usan `fecha_publicacion` no nula y
`tipo_revista_id` no nulo. POST y PUT reciben esos nombres; GET devuelve además
`tipo_revista: { id, nombre }`. La fecha admite valores desde 2010-01-01 hasta
la fecha actual y determina orden, duplicados, pertenencia a memorias, búsqueda y
exportaciones. Los eventos nuevos de auditoría usan `fecha_publicacion` y
`tipo_revista_id`.

El alta valida textos, fecha, catálogo, enlace y al menos un autor antes de
persistir. Trabajo y autorías se confirman en una sola transacción, por lo que
una petición sin autor no deja una fila parcial ni genera un conflicto de
duplicado al reintentar con datos corregidos. En edición puede agregarse y
quitarse autores en una sola petición, pero nunca dejar el trabajo sin autor.

La revisión `b4e7c1d9a320` crea `tipo_revista`, reemplaza las referencias
anteriores a Tipo de reunión y renombra la fecha de trabajos y snapshots. El
entorno de prueba fue regenerado después de aplicar la revisión.

Validación: 50 pruebas backend focalizadas cubren catálogo, fechas, autorías,
rollback, historial, snapshots y errores de dominio.

## ISS-34: Artículos de divulgación

`ArticuloDivulgacionService` administra alta, listado, detalle, actualización,
baja lógica, historial y snapshots de Memorias. El payload de escritura requiere
`titulo`, `descripcion`, `fecha_publicacion` y `grupo_utn_id`; las fechas respetan
el rango institucional, el grupo debe existir y las validaciones identificables
se devuelven mediante `error.details.fields`.

El título no posee una restricción de unicidad en el modelo, las migraciones ni
el service. Dos artículos pueden compartir el mismo título porque cada registro
se identifica por su ID y conserva auditoría e historial independientes. La
regresión de servicio cubre expresamente dos altas con el mismo valor de
`titulo`.

El endpoint `GET /articulos-divulgacion/<id>/historial` entrega los cambios de
campo del artículo. El frontend consume este contrato en el home de forma
diferida y en el detalle, con paginación visual de 3 eventos.
# Paginacion SQL (ISS-89)

Los listados de docencia, documentacion, publicaciones, trabajos, distinciones,
registros, autores y tipos cuentan y limitan la consulta filtrada antes de
serializar. Los historiales de Documentacion y Docencia aplican sus filtros
de eventos antes del limite SQL; el de Docencia combina auditoria y grados en
una consulta paginada. Se conservan filtros, orden, permisos, UCT y el
contrato plano o `data`/`meta`/`error` segun se envien parametros.

## Docencia y Biblioteca: paginacion SQL (ISS-94)

Los listados de `/api/v1/produccion/actividades-docencia` y
`/api/v1/produccion/documentacion-bibliografica` admiten `view=table`.
Devuelven `data` y `meta` con pagina, tamano, total, paginas y
`options` (pares `value/label`). Los homes solicitan nueve filas.
Sin ese parametro se conservan los contratos de lista anteriores.

Ambos aceptan `activos`, `page`, `per_page`, `q` (hasta 200
caracteres), `direction=asc|desc` e `ids` positivos separados por
coma. IDs vacios producen cero registros; la UCT protege filas, totales,
opciones y busquedas relacionales. Los parametros invalidos responden
`VALIDATION_ERROR` (400) con el contrato compartido.

- Docencia: orden por curso, institucion, investigador, rol, grado,
  fecha_inicio o estado. Filtros `filter_curso`, `filter_institucion`,
  `filter_investigador`, `filter_rol`, `filter_grado`.
  El grado es el historial vigente mas reciente por fecha e ID, igual que
  en la serializacion. Un investigador eliminado permanece oculto en
  busqueda y opciones. Se precargan investigador reducido, rol e historiales
  completos de grados.
- Biblioteca: orden por titulo, editorial o anio; el home usa titulo.
  Filtros `filter_autor` por nombre y `filter_anio`.
  La busqueda incluye titulo, editorial, anio y autores vigentes. Los
  filtros de autores usan EXISTS para que varias autorias no dupliquen
  documentos ni alteren LIMIT/OFFSET. Se precargan autores y grupo.

Las opciones corresponden al alcance de estado/memoria antes de aplicar
busqueda o filtros individuales, por lo que incluyen registros de paginas
no visibles. Se mantienen permisos ADMIN/GESTOR/LECTURA de lectura y los
contratos de mutaciones, auditoria e historial existentes.
Las regresiones estan en `tests/test_tenant_scope.py` y se complementan
con `tests/test_produccion_list_sql_pagination.py`.
