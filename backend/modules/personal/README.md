# Modulo backend de personal

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

Los nombres de Personal, Investigador y Becario admiten solo letras Unicode y
espacios entre palabras. `22`, `Ana 22` y `Ana-María` devuelven
`details.fields.nombre_apellido`; `Ana María` es válido.

Las variantes Investigador y Becario identifican nombre, selecciones de catálogo y proyectos inválidos mediante `error.details.fields`. Las validaciones internas del usuario conservan un mensaje general seguro.

El formulario Becario asocia las fechas, montos y selección de becas al campo `becas`; los errores mantienen el rechazo transaccional sin cambios parciales.

## Contrato de fechas

`fecha_alta_grupo` y los períodos de relaciones se validan desde el 01/01/2010.
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

Payload obligatorio: `nombre_apellido` (hasta 120 caracteres), `dni` (7 u 8
digitos), `cuil` (`XX-XXXXXXXX-X` con digito verificador valido),
`horas_semanales` (entero entre 1 y 168), `tipo_personal_id`, `grupo_utn_id` y
`fecha_alta_grupo` (`YYYY-MM-DD`, desde 2010-01-01). Tipo y grupo deben existir
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

Personal acepta cualquier ID activo de TipoPersonal, sin exigir nombres
prefijados. El catálogo disponible excluye tipos con `activo=false` o soft delete.

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
