# Modulo backend de personal

## Contrato histórico de becas y presentación (ISS-41)

`GET /api/v1/personal/becario/<id>/historial` mantiene el contrato de auditoría
con `campo`, `valor_anterior`, `valor_nuevo`, fecha y usuario. Los eventos actuales
de `becas` contienen `accion` y `detalle`, con referencia de beca, fechas y monto
cuando corresponden. La compatibilidad con formatos históricos se resuelve en
el frontend; no se reescriben filas ni se alteran modelos, permisos o endpoints.

`tests/test_becario_historial_becas.py` verifica por HTTP los eventos de cambio
de fecha de fin y monto cero, y la conservación exacta de valores serializados
o estructuras anteriores al consultar el historial. La consulta de registros
existentes para la validación del usuario fue de solo lectura. Etapa aceptada
el 05/11/2026: 12 pruebas backend del flujo, 239 frontend, TypeScript y build
aprobados. No hay migración ni cambios de despliegue.

## Becas en el detalle del becario (ISS-40)

`GET /api/v1/personal/becario/<id>` incorpora `becas` mediante
`personal_completo_service.obtener_personal_por_tipo`. Cada asignación contiene
`id` (ID de beca), `nombre_beca`, `descripcion`, `fecha_inicio`, `fecha_fin`
y `monto_percibido`. Las fechas usan `YYYY-MM-DD`; fin y monto pueden ser nulos,
y un monto cero se conserva. Sin asignaciones se devuelve un array vacío.

La consulta hace un join entre `beca_becario` y `beca`, limita por becario y
excluye bajas lógicas de ambas tablas. Ordena por ID de vinculación. Incluye
períodos vencidos que no fueron desvinculados: el frontend deriva la vigencia
desde las fechas y no confunde fin de período con baja de la relación. No altera
los modelos ni amplía el listado combinado; la carga adicional se hace solo
para el detalle de becarios.

El endpoint mantiene permisos ADMIN/GESTOR/LECTURA y errores existentes.
Editar otros campos sin incluir `becas` no sincroniza ni modifica relaciones.
El formulario existente recibe el contrato tipado y compara diferencias antes
de enviar el PUT. No hay migración ni cambios de configuración de despliegue.

`tests/test_becario_edicion_becas.py` prueba el contrato HTTP con SQLite aislado:
colección vacía, varias asignaciones, vencimiento, nulos, monto cero, exclusión
de bajas lógicas y conservación de la relación al modificar horas. La etapa fue
aceptada por el usuario el 05/11/2026, con solicitud expresa de ejecutar commits.
Se aprobaron 27 pruebas backend del flujo y 234 frontend, TypeScript y build.

## Contrato consumido por la validacion preventiva (ISS-33)

Nombre/apellido, identidad DNI/CUIL y horas conservan sus validaciones definitivas en services, sin cambiar payloads, auditoria ni historial.

El frontend reutiliza sus comprobaciones durante la interaccion y muestra
conjuntamente los errores al guardar. Los errores de campo de la API mantienen
`error.details.fields`; los no asociados a un control conservan feedback general.
La etapa no cambia endpoints, payloads, modelos, permisos ni eventos auditados.
Escribir o corregir un campo no genera una mutacion de dominio; la autoridad
definitiva sigue siendo el backend. Aceptado por el usuario el 05/11/2026.

## Nombres, fechas e historial (ISS-34, ISS-35, ISS-36)

Personal, Becario e Investigador incorporan `nombre` y `apellido` independientes.
Las altas en sus endpoints existentes exigen ambos: letras Unicode y espacios,
hasta 60 caracteres por campo y 120 en conjunto, incluido el separador. Por
ejemplo, `{"nombre":"María del Carmen","apellido":"De la Cruz"}` conserva
los nombres y apellidos compuestos. `nombre_apellido` se deriva como
`María del Carmen De la Cruz` para listados y consumidores existentes.
Las lecturas individuales incluyen los dos campos; el listado combinado conserva
su contrato plano. Los PUT admiten modificar uno de los campos, completan el otro
desde el registro y auditan las diferencias. Un nombre compuesto enviado por sí
solo no puede reemplazar los campos de un registro ya estructurado.

`services/nombre_service.py` concentra normalización, asignación y composición
para memoria; `services/fecha_validation.py` valida `fecha_alta_grupo` entre
2010-01-01 y hoy inclusive en altas y ediciones genéricas o especializadas.
Valores vacíos, inválidos o futuros devuelven HTTP 400 y errores de campo cuando
corresponde. Se mantienen permisos ADMIN/GESTOR de escritura, lectura para
LECTURA, identidad documental, auditoría y baja lógica existentes.

`services/historial_service.py` enriquece las referencias de función de personal,
formación, dedicación, categoría UTN, incentivos y grupo con
`valor_anterior_nombre` y `valor_nuevo_nombre`. Conserva los IDs originales y
resuelve etiquetas en lotes, incluidos catálogos inactivos; una referencia ausente
se presenta como `Referencia no disponible` y un valor vacío como `Sin dato`.
El contrato admite el array anterior y la respuesta paginada con `data`/`meta`.

Migraciones:

- `c2e4a6b8d0f1` agrega las columnas anulables después de `a7c9e2f4b6d8`,
  sin depender de funcionalidades de búsqueda.
- `d3f5a7c9e1b2` normaliza el dataset ficticio revisado mediante correspondencias
  explícitas. Planifica todo antes de escribir y aborta ante un nombre desconocido
  o un valor parcial incompatible. Conserva nombres ya estructurados, IDs,
  relaciones y valores anteriores/nuevos en `auditoria_campo`. Se aplicó a
  112 registros de desarrollo: 41 Personal, 49 Becario y 22 Investigador.
  No es un algoritmo general para dividir nombres reales: otra base con datos
  distintos requiere revisar sus correspondencias antes del despliegue.
  Su downgrade automático se rechaza para no sobrescribir ediciones posteriores;
  una recuperación requiere revisar auditoría o respaldo. Las columnas siguen
  siendo anulables para compatibilidad de esquema; las altas API exigen ambos
  campos.

Pruebas: `test_personal_nombres_fechas_historial.py`,
`test_personal_nombres_migration.py` y regresiones de Personal, auditoría y Excel:
75 casos backend aprobados. Aceptación visual y funcional del usuario el
04/11/2026.

## Baja y reactivacion (ISS-39)

`DELETE /api/v1/personal/:rol/:id` acepta un cuerpo opcional
`{"motivo": "texto"}` de hasta 500 caracteres. Sin cuerpo o con motivo vacio
conserva la baja habitual. Cierra el periodo de horas y registra el cambio de
estado y, cuando existe, el motivo en auditoria, sin borrar identidad ni vinculos.

`PUT /api/v1/personal/:rol/:id/restore` reactiva personal, becario o investigador
para ADMIN/GESTOR; LECTURA no puede ejecutarlo. Devuelve el registro serializado,
404 si no existe y 409 si ya esta activo. Conserva ID, identidad y relaciones,
limpia la baja, registra usuario/fecha de actualizacion y cambio de estado, y abre
un periodo de horas desde hoy si no existe uno activo. El bloqueo PostgreSQL usa
`FOR UPDATE OF` sobre la entidad para admitir relaciones opcionales con LEFT JOIN.
El alias de restauracion de investigador utiliza el mismo servicio.

Los duplicados de DNI activos siguen devolviendo 409. Para identidades inactivas,
`error.details.fields.dni` orienta a buscar por nombre en Personal > Inactivos y
solicitar reactivacion. La unicidad documental permanece vigente tras la baja.
No se requiere migracion; el motivo se conserva en el historial de cambios.

Validacion: 39 pruebas `test_personal_*.py`, incluida colision activa/inactiva
por HTTP, ausencia de duplicacion y permisos; restauracion PostgreSQL verificada
con flush y rollback. Aceptacion funcional del usuario el 04/11/2026.

## Identidad documental (ISS-76)

Personal, Becario e Investigador comparten la tabla `identidad_personal`, con
restricciones `UNIQUE` para `dni` y `cuil`. Cada registro tiene una referencia
opcional y unica a esa tabla; la migracion
`a76d1e2f3b4c_personal_identidad.py` conserva los registros anteriores con
identidad nula. Las altas nuevas requieren ambos campos. Al editar un registro
heredado, se completan juntos; las actualizaciones parciales de un registro que
ya tiene identidad pueden enviar solo el campo modificado.

Los endpoints existentes `POST /api/v1/personal`, `POST /api/v1/becarios` y
`POST /api/v1/investigadores/`, y sus `PUT` de edicion, aceptan `dni` y `cuil`.
Las lecturas de detalle serializan ambos como cadenas o `null`. El service
`services/identidad_service.py` valida DNI de 7 u 8 digitos, CUIL en formato
`XX-XXXXXXXX-X`, coincidencia con el DNI y digito verificador. Antes de guardar
comprueba unicidad sin confundir la identidad del propio registro; las
restricciones de base de datos cubren las escrituras concurrentes. La identidad
se conserva tras la baja logica, de modo que el DNI no se puede reutilizar.

Un formato o digito invalido devuelve HTTP 400 y `error.details.fields.dni` o
`error.details.fields.cuil`; un duplicado devuelve HTTP 409 con el mismo mapa
de campo. Las modificaciones registran cambios de DNI/CUIL en el historial
existente. Los permisos no cambian: `ADMIN` y `GESTOR` escriben;
`ADMIN`, `GESTOR` y `LECTURA` consultan. `tools/seed_testing_data.py` genera
identidades ficticias deterministas de forma idempotente y conserva la
proteccion contra ejecucion en produccion.

Pruebas: `tests/test_personal_alta_ptaa.py` y suites relacionadas de auditoria,
relaciones y memorias.

## Listado combinado y relaciones opcionales (ISS-25)

`GET /api/v1/personal/all` es el listado canonico de Personal, Becarios e
Investigadores. Mantiene compatibilidad: sin `page` ni `per_page` devuelve la
lista plana anterior; con cualquiera de esos parametros devuelve:

```json
{
  "data": [],
  "meta": { "page": 1, "per_page": 9, "total": 0, "total_pages": 0 },
  "error": null
}
```

Parametros paginados admitidos:

- `page`: entero positivo.
- `per_page`: entero entre 1 y 9.
- `search`: busca por nombre, rol, clasificacion o grupo.
- `tipo`: `personal`, `ptaa`, `profesional`, `becario` o `investigador`.
- `activos`: `true`, `false` o `all`.
- `sort`: `nombre`, `clase`, `clasificacion`, `grupo`, `horas`, `estado` o
  `fecha_alta`.
- `direction`: `asc` o `desc`.
- `ids`: lista separada por comas de enteros positivos, usada por el contexto de
  memorias.

La consulta unifica los tres modelos, aplica filtros, conteo, ordenamiento y
paginacion en base de datos, y luego serializa `id`, `rol`, `nombre_apellido`,
`clasificacion`, `grupo`, `horas_semanales`, `activo`, `fecha_alta_grupo` y las
fechas de auditoria. La lectura requiere `ADMIN`, `GESTOR` o `LECTURA`. Los
parametros invalidos devuelven el error de validacion seguro del API.

En Investigador, `categoria_utn_id` y `programa_incentivos_id` son opcionales.
Cuando se reciben valores se validan contra sus catalogos; `null` elimina una
asignacion existente. Altas, asignaciones y eliminaciones quedan registradas en
auditoria. Las relaciones ya eran anulables, por lo que no se agrega migracion.

## Borradores (ISS-22)

Los formularios Personal, Becario e Investigador usan los módulos permitidos
`personal-personal`, `personal-becario` y `personal-investigador` del contrato
compartido `/api/v1/borradores`. El borrador no crea ni modifica una persona;
los endpoints de este módulo vuelven a validar permisos, campos, relaciones y
reglas de negocio al guardar definitivamente. La tabla, vencimiento y
aislamiento por usuario se documentan en `../shared/README.md`.

Los campos `nombre` y `apellido` de Personal, Investigador y Becario admiten solo
letras Unicode y espacios entre palabras. `22`, `Ana 22` y `Ana-María` devuelven
errores asociados al campo correspondiente; `Ana María` es válido.

Las variantes Investigador y Becario identifican nombre, selecciones de catálogo y proyectos inválidos mediante `error.details.fields`. Las validaciones internas del usuario conservan un mensaje general seguro.

El formulario Becario asocia las fechas, montos y selección de becas al campo `becas`; los errores mantienen el rechazo transaccional sin cambios parciales.

## Contrato de fechas

`fecha_alta_grupo` se valida entre el 01/01/2010 y hoy inclusive. Los períodos
de relaciones mantienen sus reglas propias y el mínimo institucional de 2010.
El límite no corresponde a datos biográficos ajenos a la actividad del grupo.

## Responsabilidad

Gestiona investigadores, becarios, PTAA, profesionales, tipos asociados,
pertenencia al grupo, carga horaria, proyectos y relaciones con becas.

## Estructura

- `routes`: endpoints bajo `/api/v1/personal`.
- `controllers`: traduccion HTTP y errores seguros.
- `services`: validacion, transacciones, auditoria e historial.
- `models`: entidades, relaciones, soft delete y snapshots de memorias.

## Contratos modificados

### Alta de PTAA y profesional (ISS-08)

`POST /api/v1/personal` sin barra final crea una entidad `Personal` para ambas
categorías. El catálogo `tipo_personal_id` determina el tipo; no se requieren
formación, dedicación, categoría UTN ni incentivos de otros subtipos.

Payload obligatorio: `nombre` y `apellido` (hasta 60 caracteres cada uno y
120 en conjunto, incluido el espacio), `dni` (7 u 8
digitos), `cuil` (`XX-XXXXXXXX-X` con digito verificador valido),
`horas_semanales` (entero entre 1 y 168), `tipo_personal_id`, `grupo_utn_id` y
`fecha_alta_grupo` (`YYYY-MM-DD`, desde 2010-01-01 hasta hoy). Tipo y grupo deben existir
y estar activos. El alta establece `activo=true` y registra `created_by`.

Devuelve 201 con la entidad serializada y su historial inicial de horas.
Inserción, flush, historial y commit se protegen con rollback completo.
Validaciones y referencias inválidas devuelven 400 con
`error.details.fields` (mapa de campo de payload a mensaje seguro).
ISS-19: nombre, fecha de alta, horas y selecciones de catálogos conocidas devuelven claves HTTP concretas en `error.details.fields`. Las condiciones sin dato editable, como registros inactivos o inconsistencias del historial, conservan mensajes generales seguros.
Errores inesperados conservan el contrato compartido 500.

Listado: `/api/v1/personal/all`; detalle e historial:
`/api/v1/personal/personal/{id}` y su sufijo `/historial`. La búsqueda de
personal enlaza a `/personal/personal/{id}`. Profesional se persiste en la
misma tabla y utiliza el rol técnico `personal` para actualizarlo.

Pruebas: `tests/test_personal_alta_ptaa.py`, con SQLite aislado y autenticación
simulada; cubre alta, referencias, obligatorios, rollback, consulta, búsqueda,
permisos y regresión de los otros tipos.

### Actualizar becario

```http
PUT /api/v1/personal/becarios/{id}
```

Acepta campos parciales. `becas`, cuando se envia, representa el estado final
deseado de relaciones activas:

```json
{
  "nombre_apellido": "Nombre Apellido",
  "becas": [
    {
      "beca_id": 3,
      "fecha_inicio": "2026-04-01",
      "fecha_fin": "2027-03-31",
      "monto_percibido": 150000
    }
  ]
}
```

El service valida todas las relaciones y aplica altas, bajas y cambios en la
misma transaccion que los campos del becario. No realiza commits intermedios.
Una lista vacia desvincula todas las relaciones activas.
Cada vínculo nuevo o actualizado exige fecha de inicio y fecha de fin. El
service rechaza la ausencia de fin con `error.details.fields.becas`; los
vínculos históricos sin fin permanecen legibles hasta su próxima edición.

## Reglas y validaciones

Seguimiento ISS-08: `services/horas_validation.py` centraliza `horas_semanales`
como entero de 1 a 168 inclusive (7 días por 24 horas). Rechaza booleanos,
fracciones y cadenas sin coerción. Se aplica al crear/editar Personal, Becario e
Investigador, incluida la ruta genérica de actualización por rol. En edición
se valida antes de mutar campos o historiales. Una carga parcial sin horas no
reescribe valores históricos; no hay migración/corrección masiva de datos.
Devuelve HTTP 400 con `error.details.fields.horas_semanales`.

Personal acepta IDs activos de TipoPersonal compatibles con su clase, sin exigir
nombres prefijados para las funciones de apoyo. El catálogo disponible excluye
tipos con `activo=false` o soft delete.

- IDs positivos y sin duplicados.
- Fechas en formato `YYYY-MM-DD` y fin no anterior al inicio.
- Monto numerico no negativo.
- Becario, beca, tipos y grupo deben existir y estar activos.
- Las actualizaciones aceptan payload parcial.
- Las bajas funcionales usan soft delete.

## Permisos

- lectura e historial: `ADMIN`, `GESTOR`, `LECTURA`
- alta, actualizacion, relaciones y baja: `ADMIN`, `GESTOR`

## Auditoria

- cambios de campos se registran por atributo
- vincular, actualizar o desvincular becas genera eventos relacionales sobre
  la entidad `becario`
- el historial de carga horaria conserva sus periodos propios
- los snapshots de memorias cerradas no dependen del estado vivo posterior

## Errores

Los errores de validacion se devuelven como 400. Los errores inesperados no
deben exponer secretos ni detalles internos. La transaccion debe revertirse
completa ante cualquier fallo.

## Pruebas relacionadas

- `tests/test_personal_relaciones_consolidadas.py`
- `tests/test_auditoria_personal_services.py`
- pruebas `*_memoria_historial.py` de personal

## Datos ficticios de testing

El seed integral crea doce registros deterministas para cada categoria visible:
Tecnico administrativo y de apoyo, Profesional, Becario e Investigador. Varia
fecha de alta y carga horaria para habilitar pruebas manuales de filtros,
ordenamiento y paginacion. La carga es idempotente y mantiene la proteccion que
impide ejecutarla accidentalmente en produccion.
# Candidatos de proyectos (ISS-10)

Seguimiento ISS-08: el listado combinado `/personal-all` (ruta canónica
`/api/v1/personal/all`) ordena todos los subtipos por `created_at` descendente,
con ID y rol como desempate determinista. Las altas recientes aparecen primero
en el home paginado. No se modifica el contrato de creación ni se requiere
migración. Regresión de orden entre subtipos y más de nueve registros:
`tests/test_personal_alta_ptaa.py`.

GET `/api/v1/investigadores/` conserva permisos ADMIN/GESTOR/LECTURA.
El listado por defecto y `activos=true` requieren `activo=true` y ausencia
de baja lógica. `activos=false` incluye inactivos o dados de baja; `all`
conserva todos. Esto evita ofrecer investigadores inactivos como candidatos
de coordinador sin alterar el hook compartido del frontend.

## ISS-12: autoría de integrantes

Las relaciones inversas de investigadores con trabajos se obtienen de autorias_reunion/autorias_revista. Se mantienen los datos de trabajos en la serialización de investigadores sin depender de tablas de asociación exclusivas. Investigadores y becarios son los únicos orígenes válidos de la colección común de autores de Producción; no se fusionan las tablas de personal.

Corrección de alcance ISS-12: los autores de trabajos son únicamente investigadores y becarios. Personal (PTAA/profesional) no puede vincularse como autor. Se mantiene la etiqueta Autores.

## Snapshots de memorias (ISS-16)

Personal, investigadores y becarios se seleccionan por UCT y solapamiento entre alta, baja y período. La foto conserva `fecha_alta_grupo`. `horas_semanales` representa el historial vigente al final del período y queda null cuando no hay evidencia, sin copiar horas actuales. Las becas usan sus intervalos completos.
# Paginacion SQL (ISS-89)

Personal, investigadores, becarios y sus catalogos de tipos obtienen `total`
de la consulta filtrada y cargan solo la pagina con `LIMIT/OFFSET`. Las
relaciones necesarias se precargan para esas filas. Sin `page`/`per_page` se
conserva el array anterior; con ellos se mantiene `data`/`meta`/`error`, el
orden, los filtros y el aislamiento UCT. Los historiales conservan tres
eventos por pagina.

## Precarga de listados auxiliares (ISS-94)

Las consultas completas y paginadas de Investigadores y Becarios comparten
opciones ORM de lectura. Investigadores precarga identidad, horas,
categorias, dedicacion, grupo, proyectos, participaciones y autorias de
reunion utilizadas al serializar. Desactiva la precarga de publicaciones
no consumidas. Becarios precarga identidad, formacion, grupo e historial
de horas, evitando una consulta de horas por integrante.

Se conservan campos, permisos, auditoria, reglas de alta/edicion y alcance
UCT. El listado raiz sigue ordenado por ID; las colecciones relacionadas
sin order_by explicito no ofrecen garantia de orden fisico y deben
ordenarse en el consumidor cuando requieran una presentacion estable.
El home combinado de Personal mantiene su endpoint paginado y contrato.

Las pruebas de paginacion e aislamiento permanecen en
`tests/test_personal_sql_pagination.py` y `tests/test_tenant_scope.py`.
Las mediciones locales comparables de endpoints completos pasaron de
71 a 10 consultas para Investigadores y de 48 a 7 para Becarios;
son cantidades observadas con el escenario local, no limites universales.

## Corrección de clase por alta errónea

La reclasificación permite corregir la clase elegida por error al dar de alta
un integrante y advertirlo en ese momento. No define una transición de carrera
ni un cambio de categoría laboral posterior: esos casos no fueron especificados
y quedan fuera del alcance aprobado. No hay un límite temporal automático;
el uso previsto es la corrección del alta, sujeta a las dependencias existentes.

`PUT /api/v1/personal/{rol}/{id}/reclasificar` admite ADMIN/GESTOR dentro de su
UCT. `rol` y `clase_destino` usan `personal`, `becario` o `investigador`, con un
destino diferente del origen. El JSON incluye `clase_destino`, las diferencias
de campos comunes y los campos de la clase destino: `tipo_personal_id` para
Personal, `tipo_formacion_id` para Becario o `tipo_dedicacion_id`,
`categoria_utn_id` y `programa_incentivos_id` para Investigador, respetando la
obligatoriedad de sus altas. Becario admite además la colección `becas`.
Se rechazan campos ajenos, catálogos inactivos y registros inactivos o dados de
baja. Deben reactivarse antes de corregirlos.

El traslado conserva la misma `IdentidadPersonal`, DNI/CUIL, nombres, UCT,
fecha de alta, creación, intervalos de horas e historial de cambios. Se auditan
la clase anterior/nueva y los campos exclusivos retirados o incorporados. El ID
numérico puede cambiar porque cada clase tiene su propia tabla. La respuesta
HTTP 200 devuelve el registro serializado con `rol` e `id` efectivos. Todo se
persiste en una transacción; un error revierte el traslado completo.

Las becas, proyectos, autorías y demás antecedentes referenciados desde otras
tablas bloquean la reclasificación, incluso si tienen baja lógica. Un conflicto
HTTP 409 conserva todos los vínculos; no se eliminan, cierran ni trasladan
automáticamente. Desvincular con baja lógica no garantiza habilitar la operación.
Las fotos existentes de Personal/Becario/Investigador en memorias son la
excepción histórica: mantienen su contenido y se vinculan a la identidad estable.

La migración `e4a6c8f0b2d3`, posterior a `d3f5a7c9e1b2`, agrega `identidad_id`
nullable, índice, FK restrictiva y unicidad por versión/identidad en cada tabla
de fotos. Los IDs de clase quedan como procedencia congelada, sin FK al registro
vivo. Se completa la identidad disponible sin modificar contenido histórico.
El aislamiento UCT contempla tanto fotos con identidad como fotos heredadas sin
ella. El downgrade rechaza una reversión cuando el origen ya no existe o su
identidad cambió; requiere restaurar un respaldo coherente previamente.

Pruebas: `test_personal_reclasificacion.py`, `test_personal_snapshot_migration.py`
y `test_personal_snapshot_postgres.py` (optativa con rol migrador, en esquemas
efímeros). Cubren identidad, traslado atómico, rechazo de dependencias,
conservación de fotos y Excel, aislamiento UCT y reversión de la migración.

## Duplicados y depuración de tipos de personal

Las altas y ediciones de Tipo de Personal comparan nombres sin diferencias de
tildes, mayúsculas, espacios repetidos o puntuación. El nombre guardado conserva
su escritura y normaliza espacios. Un equivalente existente, incluso inactivo,
produce HTTP 409. En PostgreSQL un bloqueo transaccional serializa estas
mutaciones; el commit o rollback libera el bloqueo. Los endpoints, permisos y
la paginación SQL conservan sus contratos.

`tools/depurar_tipos_personal.py` permite retirar opciones de una configuración
existente sin eliminar registros ni reasignar personas. Desde `backend`, ejecutar
primero una vista previa con `--conservar` repetido por cada nombre vigente, por
ejemplo Técnico, Administrativo, De Apoyo y Profesional. Para aplicar se repite
el comando con `--aplicar --ids-esperados` y los IDs devueltos por la vista previa,
separados por comas. Si el plan cambió o falta una opción, se rechaza la operación.
`--usuario-id` identifica al responsable; sin él la auditoría corresponde al sistema.

La herramienta conserva una opción por nombre normalizado, audita la baja lógica
de las demás y normaliza las etiquetas elegidas cuando corresponde. Comprueba
cantidades y huellas de Personal y sus fotos antes de confirmar una transacción
única. Las asignaciones históricas permanecen; los tipos inactivos dejan de ser
seleccionables en altas y nuevas asignaciones. Repetir un plan vacío es idempotente.
El catálogo sigue siendo administrable. Las cargas de prueba utilizan Técnico
y Profesional sin generar variantes agregadas de técnico, administrativo y apoyo.

`tests/test_tipo_personal_catalogo.py` cubre vista previa, confirmación del plan,
duplicados normalizados, preservación de referencias, idempotencia y rollback.

## Compatibilidad de funciones por clase (ISS-43)

`services/tipo_personal_compatibilidad.py` centraliza una regla pura sobre la
denominación normalizada del catálogo: los nombres que comienzan con Docente,
Investigador o Becario, incluido el prefijo Personal y variantes de género o
plural, corresponden a otras clases. La comparación ignora tildes, mayúsculas,
espacios y puntuación. Las funciones de apoyo y las denominaciones propias del
catálogo siguen admitidas, sin depender de IDs de una instalación.

`TipoPersonal.serialize()` agrega el booleano `compatible_con_personal` en las
lecturas existentes del catálogo: listado completo o paginado, detalle y demás
respuestas que serializan el tipo. El catálogo administrativo conserva sus
opciones; el consumidor decide cuáles mostrar para la clase Personal.

`POST /api/v1/personal`, `PUT /api/v1/personal/personal/{id}` y la reclasificación
a `clase_destino=personal` validan la misma regla. Una función incompatible
devuelve HTTP 400 con `error.details.fields.tipo_personal_id`, antes de modificar
campos de la persona. Una asignación heredada incompatible exige corregir la
función al guardar, aunque el payload parcial no incluya ese campo. No se
reasignan personas ni se modifican fotos históricas automáticamente.

La edición de TipoPersonal devuelve HTTP 409 si el nuevo nombre es incompatible
y tiene personas asignadas, para evitar introducir la inconsistencia mediante
el catálogo. Se mantienen roles, aislamiento UCT y auditoría de las operaciones
válidas. No cambia el modelo de almacenamiento ni se requiere migración.

`tests/test_personal_funciones_clase.py` cubre metadata de catálogo, altas,
ediciones sin cambios parciales, reclasificación con preservación de identidad,
renombrados y asignaciones heredadas. La validación conjunta con alta PTAA,
reclasificación y catálogo completó 42 pruebas backend; frontend completó 242
pruebas, TypeScript y build de producción. Aceptación del usuario: 05/11/2026.
