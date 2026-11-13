# Memorias

## Acciones del listado y confirmaciones (ISS-100)

La fila principal de `MemoriasHome` permite reabrir una memoria activa cuya
versión actual está cerrada, para ADMIN/GESTOR. La confirmación explica que se
crea una nueva versión y que los datos de las versiones cerradas son inmutables.
El cierre también advierte que cualquier modificación requiere una reapertura.
Home y detalle comparten estos textos en `utils/confirmacionesMemoria.ts`, con
opciones Continuar y Volver. Cancelar no persiste cambios; confirmar bloquea
duplicados y actualiza las consultas de listado, detalle e historial.

En el panel desplegable, cada versión cerrada ofrece descarga con icono
`Download`, incluidas las históricas, sin repetir la reapertura. Se reutiliza
`exportarExcelMemoria(memoriaId, versionId)` y sus permisos ADMIN/GESTOR.
Mientras genera el archivo muestra un indicador accesible y bloquea descargas
duplicadas; informa el nombre del archivo al terminar o un error accionable.
Las versiones abiertas y en revisión conservan sus acciones de gestión.

Aceptado visual y funcionalmente el 07/11/2026. Validación: 271 pruebas frontend,
TypeScript, build de producción y regresiones backend de estados, inmutabilidad,
formato Excel y permisos aprobados. Sin cambios de contratos HTTP.

## Filtros desplegables (ISS-47)

MemoriasHome: estado del registro; conserva el filtro independiente de estado de versión.
Los filtros del listado utilizan `TableFilterSelect`, con nombre accesible y
selección mediante teclado. Todos/Todas elimina la restricción del criterio.
La adaptación del selector conserva valores, setters y opciones de consulta;
se mantienen services, permisos, nueve filas por página, contexto de Memoria
y persistencia de filtros de ISS-50. No se modifican campos de formularios.

Aceptado visual y funcionalmente el 06/11/2026. Validación integrada:
269 pruebas frontend, TypeScript y build de producción aprobados.
`tests/homeFilterSelect.test.ts` comprueba selección y limpieza en las cuatro
pantallas principales y ausencia de chips de filtrado en los homes.

## Validacion preventiva de formularios (ISS-33)

`MemoriaForm` y `MemoriaPeriodoForm` reutilizan sus comprobaciones en la
interaccion y al guardar. Seleccionar UCT y completar los extremos del periodo
conserva sus reglas; modificar el inicio revalida que el fin no lo preceda.
Calendar mantiene las comprobaciones de formato y rango. Los errores del otro
extremo o del servidor permanecen visibles hasta que el campo correspondiente
o una dependencia real los modifique. La correccion del periodo sigue enviando
solo diferencias y no hace solicitudes de dominio al validar.

La actualizacion de errores usa `src/lib/liveValidation.ts`, que revalida el
campo editado y las reglas cuyo resultado cambia por dependencia, preservando
los demas errores. No agrega hooks compartidos ni modifica componentes globales.
Las validaciones no disparan escrituras de dominio. Se conservan services,
contratos, permisos, borradores, navegacion y feedback de exito.
La etapa fue aceptada visual y funcionalmente por el usuario el 05/11/2026;
la regresion transversal esta en `tests/liveValidation.test.ts`.

## Moneda en exportaciones de Equipamiento y Transferencias

Las fotos de Equipamiento y Transferencias incluyen `moneda` ARS/USD junto al
importe original. El Excel de una versión usa esos valores históricos y muestra
el código de moneda en el formato de la celda numérica, sin conversiones. Las
fotos anteriores se identifican como ARS; editar la ficha actual no cambia su
importe ni la moneda guardada en una versión anterior.

## Acceso desde el menú ADMIN (ISS-52)

El menú ADMIN ofrece Inicio, Administración, Memorias y Búsqueda. El enlace
`/memorias` permanece visible con versiones abiertas, en revisión, cerradas o
sin memorias. Cerrar la única memoria no impide volver al listado, crear otro
período o utilizar la reapertura existente. El ajuste se limita a Sidebar;
no cambia vistas, servicios, validaciones, confirmaciones ni permisos.

## Generación institucional validada (ISS-94)

El operador carga datos en los módulos del sistema, crea una memoria con UCT y
período, cierra su versión y descarga el archivo institucional desde
`MemoriaVersionDetalle`. El formato es fijo y los datos corresponden a la foto
del cierre. Las correcciones posteriores de entidades no cambian ese archivo.
El acceso a la descarga requiere ADMIN o GESTOR y una versión cerrada.

Durante la descarga, el botón `Generar Excel` muestra exclusivamente
`Generando el archivo...` dentro del mismo control y queda bloqueado para evitar
envíos duplicados. Al terminar se muestra éxito o un error que permite reintentar.
El indicador de progreso no introduce porcentajes ni mensajes externos al botón.

## Archivo académico de la versión (ISS-98)

`MemoriaVersionDetalle` y `exportarExcelMemoria` mantienen el flujo de descarga,
el endpoint, los permisos ADMIN/GESTOR y el requisito de versión cerrada. No se
modifican componentes, hooks, tipos, formularios ni validaciones del frontend.

El archivo descargado contiene el formulario institucional en `Hoja1` y los datos
complementarios en `Detalle académico`, incluido el detalle financiero y los
registros sin clasificación suficiente. Ambos usan exclusivamente la información
conservada por esa versión. Los campos institucionales ausentes se indican como
sin información; no se completan con ejemplos del laboratorio ni con fichas actuales.

El backend corrige bordes, ajuste de texto, reservas vacías, fechas, importes y
separación de libros/revistas. El enlace de la cabecera del formulario conduce al
detalle del mismo archivo. El operador puede revisar allí fechas, roles, vigencias
y advertencias por movimientos excluidos del resumen. Se mantienen el feedback
de generación y la posibilidad de reintentar ante errores.

Aceptado visual y funcionalmente por el usuario el 07/11/2026. La validación del
archivo y su procedencia está cubierta por las regresiones backend; no hay cambios
de contrato HTTP ni de navegación.

## Error del programa de actividades (ISS-74)

La etiqueta de descripción se asocia al `textarea`. Cuando falta el texto, el
control se marca con `aria-invalid` y referencia el mensaje mediante
`aria-describedby`; el mensaje se anuncia con `role="alert"`. Los fallos
generales de guardado también se anuncian, sin marcar la descripción como
inválida.

## Programa de actividades modal (ISS-71)

La edición del programa en el detalle de versión abre un diálogo modal con
título y descripción asociados, foco inicial en el texto y retorno al botón al
cerrar. Escape y el fondo lo cierran antes de guardar; mientras el guardado
está pendiente conserva el diálogo y bloquea la cancelación.

## Carga y exportación Excel (ISS-70)

El detalle de versión y sus snapshots muestran skeletons durante la carga.
`exportarExcelMemoria` admite un callback opcional de etapas `generating`,
`receiving` y `saving`. `MemoriaVersionDetalle` utiliza únicamente el estado
pendiente de la mutación para mostrar el texto dentro del botón, bloquea envíos
duplicados y, al terminar, presenta éxito o un error accionable.
Tras un fallo se libera el botón para reintentar. El endpoint y el archivo
descargado conservan su contrato.

La vista de versión muestra los movimientos financieros de su snapshot con tipo,
importe ARS, fuente o categoría y enlace al detalle en `/movimientos/:id`. La
sección interna del contrato de Memorias conserva la clave `erogaciones`.

## Errores por campo (ISS-09)

Los formularios del módulo consumen `error.details.fields` mediante
`applyFieldErrors` de `src/lib/httpError.ts`, muestran el mensaje junto al control
y enfocan el primer campo inválido. Los nombres locales de los controles se
vinculan con las claves API, sin cambiar el payload del service ni los permisos.
Los errores sin campo o con campos desconocidos conservan el aviso general;
los errores inesperados muestran un mensaje publico seguro o un fallback accionable, sin identificadores internos.
Se conservan las reglas de validacion; ISS-33 incorpora feedback preventivo. Véase el contrato
transversal en `../README.md`.

## Fechas

Los períodos informados por las memorias admiten fechas desde el 01/01/2010, conservan el orden cronológico y pueden abarcar años distintos.

## Funcionalidad

El modulo administra memorias, sus versiones, cambios de estado, reaperturas,
snapshots historicos y exportacion Excel. El home pagina hasta 9 memorias y el
alta vuelve al home con `successMessage`.

## Listado por período y versión (ISS-86)

`MemoriasHome` muestra una fila por Memoria, con período, UCT, versión actual
y estado. Usa la tabla compartida y la barra de búsqueda y filtros de los homes
ABMC. La paginación cuenta Memorias principales; las versiones nunca se
distribuyen entre páginas. Varias filas pueden permanecer expandidas a la vez.
Cada panel carga las versiones de su Memoria al abrirse mediante la consulta de
detalle `GET /api/v1/memorias/{id}`, con caché independiente por ID. La carga,
el error con reintento y la ausencia de versiones se muestran dentro del panel.

La fila y la acción Ver abren el detalle de la Memoria. El panel de versiones
presenta ver detalle (`Eye`), descargar Excel (`Download`) para versiones
cerradas, cerrar (`LockKeyhole`) y enviar a revisión (`Send`). El detalle abre los snapshots de
una versión cerrada o la gestión de la versión vigente abierta/en revisión.
ADMIN y GESTOR pueden reabrir desde la fila principal solo la versión vigente cerrada, cerrar una versión
abierta/en revisión y enviar a revisión una versión abierta. Las acciones de
estado se deshabilitan para versiones históricas y roles sin permiso.
Reapertura, cierre y revisión requieren confirmación; el diálogo queda bloqueado
durante la operación. El resultado permanece visible aunque el nuevo estado
retire la memoria del filtro actual. La baja lógica es
individual, requiere confirmación y solo se ofrece a ADMIN para Memorias
activas. Los filtros de actividad consultan `GET /api/v1/memorias` con
`activos=true|all|false`; el filtro de estado se aplica a la versión actual.
El control de expansión indica su estado mediante `aria-expanded` y funciona
con teclado. Al cambiar los filtros o la página se cierran los paneles visibles.
La prop optativa `isRowExpanded` de la tabla compartida permite esta expansión
independiente sin cambiar los listados que usan `expandedRowId`.

## Vistas y permisos

- `MemoriasHome`: listado y filtros; ADMIN y GESTOR pueden crear memorias y la
  baja lógica continúa reservada a ADMIN. Cada fila abre el detalle y sus
  versiones se consultan al expandirla.
- `MemoriaForm`: alta con validacion de periodos.
- `MemoriaDetalle`: auditoria, versiones y cambios de estado. ADMIN y GESTOR
  pueden enviar a revisión y cerrar; el cierre se presenta como acción explícita.
- `MemoriaVersionDetalle`: consulta de snapshots y exportacion.

Los permisos visuales complementan, pero no reemplazan, los controles del backend.

## Servicios y contratos

`memoriasService.ts` concentra CRUD, estados, reapertura, snapshots y descarga.
Las respuestas de error se interpretan mediante `getErrorMessage`, compatible con
el contrato tipado `{ data, error: { code, message, details } }` y contratos
heredados. Cuerpos de texto no estructurados no se muestran al usuario.

## Validaciones y errores

- El fin del periodo no puede ser anterior al inicio.
- Las exportaciones vacias se rechazan y siempre revocan la URL temporal.
- Los fallos de guardado y eliminacion muestran mensajes accionables.
- El detalle inexistente se representa como ausencia de datos sin exponer detalles
  internos.

## Validaciones de fechas sin duplicados (ISS-09)

Los errores del formulario se muestran una sola vez mediante Field. El
helperText de Calendar/DatePicker contiene exclusivamente ayuda de formato o
rango; no recibe el mensaje de error del formulario. Se conservan los límites,
las reglas de validación y el foco del primer campo inválido.

## Feedback de acciones (seguimiento ISS-09)

Las acciones asíncronas del módulo usan Button con loading/loadingText
o ConfirmDialog, que espera la promesa devuelta por onConfirm. Durante la
operación se muestra texto de progreso con un icono animado, aria-busy y
role=status. El botón de acción se deshabilita hasta terminar; las
confirmaciones bloquean además cancelar, el fondo y los campos del diálogo.
El estado se libera al resolver o fallar, conservando errores y mensajes de
éxito existentes. Los callbacks basados en React Query deben devolver
mutateAsync para que el diálogo cubra toda la operación.

## ISS-12: autoría de integrantes

Los snapshots de trabajos reciben autores congelados (id, rol, nombre_apellido, tipo, activo), y el Excel de la versión incluye investigadores y becarios. La navegación hacia homes y detalles mantiene el contexto de memoria y el contrato de las secciones.

Corrección de alcance ISS-12: los autores de trabajos son únicamente investigadores y becarios. Personal (PTAA/profesional) no puede vincularse como autor. Se mantiene la etiqueta Autores.

## ISS-13: fecha de presentación de trabajos

Los snapshots de trabajos en reuniones exponen fecha_presentacion y sus enlaces
apuntan al flujo de reuniones con esa fecha. Excel identifica Fecha de
presentación y clasifica ponencias según el rango configurado de la memoria.
Se conserva contexto de navegación y el resto del contrato de snapshots.

## ISS-14: enlaces de trabajos en snapshots

El contrato de entradas de snapshot admite `enlace` string o null para ambos
tipos de trabajo mediante MemoriaSnapshotEntry. La descarga Excel incluye el
valor congelado. La vista conserva contadores y navegación vigente hacia los
registros del módulo; esos destinos muestran los datos actuales del trabajo.
La revisión de pertenencia y presentación histórica permanece planificada en
ISS-16, sin implementación dentro de ISS-14.

## ISS-16: períodos configurables por UCT

ADMIN y GESTOR crean memorias seleccionando UCT, inicio y fin, incluso entre años, con un atajo para año calendario. El detalle permite corregir solo diferencias reales antes del primer cierre, vuelve con `successMessage` y muestra cambios de período, estado y reapertura paginados de 3 ítems. Home, detalle y Excel identifican la memoria por rango y UCT.

El período delimita el contenido pero no cierra automáticamente la memoria.
ADMIN y GESTOR pueden pasarla a revisión, cerrarla y reabrirla desde el detalle;
eliminar continúa reservado a ADMIN. El historial rotula la relación como UCT
y muestra su sigla en lugar del identificador técnico.

La ruta de alta usa la misma protección `ADMIN/GESTOR` que el botón `Nueva`, para
evitar que un gestor autorizado sea redirigido al inicio al abrir el formulario.

Las versiones conservan el flujo visual anterior: cada sección informa su cantidad
y abre el módulo correspondiente filtrado por los elementos incluidos en la
memoria. Los snapshots históricos siguen respaldando el alcance y el Excel, sin
desplegables adicionales dentro de las tarjetas. La planificación actual se
presenta como una acción separada y no modifica los datos congelados ni el Excel
de la versión.

## Indicadores de campos obligatorios (ISS-21)

El alta y la correccion de periodos muestran el indicador en UCT e inicio y fin del periodo. La fecha de apertura sigue siendo opcional.

## ISS-19: errores de formularios

El alta y la corrección del período muestran `details.fields` junto a UCT e inicio/fin del período. El alta también asocia errores de `fecha_apertura` con su control opcional. Se conserva el borrador y se impide un segundo envío durante el guardado. Los errores sin campo identificable permanecen en el aviso general.

## Borradores de formularios (ISS-22)

En memorias, los cambios no se guardan como borrador mientras se escribe.
Al pulsar Volver con cambios, el dialogo permite guardar el ultimo estado en
el servidor, descartarlo o seguir editando. La navegacion externa al formulario
queda sujeta a la misma confirmacion. La lista global muestra el tipo, un dato
identificable del borrador cuando esta disponible, y la fecha de guardado.
Al abrirlo se puede recuperar o descartar; un guardado exitoso elimina el
borrador. El contenido no se almacena en localStorage ni sessionStorage.

## Paginación de listados (ISS-23)

Los resultados paginados muestran controles centrados de anterior, números
de página y siguiente, inmediatamente debajo de las tarjetas o resultados.
El máximo de resultados por página conserva el contrato del módulo.

## Títulos de detalle (ISS-88)

En MemoriaDetalle, las etiquetas de datos y los encabezados de tarjetas
usan peso seminegrita y color pizarra oscuro para distinguirse del contenido.
La disposición, los textos, las acciones y el contrato permanecen iguales.

## Actualizacion despues de transiciones (ISS-94)

MemoriaDetalle invalida en paralelo listado, detalle e historial al
cambiar estado o reabrir. Espera todas las invalidaciones antes de
finalizar la operacion, conservando feedback y bloqueo de duplicados.

Los accesos de seccion hacia Docencia, Transferencias y Biblioteca
transmiten sus IDs al nuevo listado paginado del servidor, con nueve
filas y `activos=all`. Los filtros y totales se aplican a todo el
conjunto de la seccion, no solo a la pagina visible. Los IDs vacios
mantienen el listado vacio y la UCT se valida en el backend.
No cambian las versiones, acciones, snapshots ni la exportacion Excel.

## Consulta histórica de Personal

En `MemoriaVersionDetalle`, las secciones Personal, Becarios e Investigadores
ofrecen «Ver datos de esta versión». `components/PersonalSnapshotDialog.tsx`
recibe la colección ya capturada por la versión y muestra los datos congelados
con nueve filas por página; no consulta ni edita la ficha actual del integrante.
Los campos ausentes se muestran como «Sin dato». Se conserva el acceso existente
a la versión y sus permisos, sin agregar endpoints ni hooks compartidos.

El diálogo tiene título y descripción accesibles, cierre por Escape y clic
exterior, foco inicial y retorno al botón que lo abrió. Las demás secciones
mantienen sus accesos. El Excel continúa utilizando las fotos de esa versión.

La corrección de una clase elegida erróneamente durante el alta no modifica una
versión anterior. Al cerrar una nueva versión se captura la clase corregida.
Los cambios posteriores de categoría laboral no forman parte del alcance
definido. Los bloqueos por vínculos operativos se conservan en Personal.
`personalSnapshot.test.ts` cubre las tres clases, campos ausentes y paginación.

Los encabezados históricos usan Tipo de Personal, Nivel de Formación y Tipo de
Dedicación, alineados con los catálogos de los formularios. Los valores guardados
en cada foto conservan su contenido; corregir una etiqueta no reescribe versiones.


## Recuperacion del contexto de consulta (ISS-50)

MemoriasHome conserva estado de actividad, estado de version, texto y pagina. La carga inicial no reinicia la pagina recuperada.

Los homes con estado local usan `shared/hooks/useHomeState.ts`; Busqueda conserva
su contrato de URL. La persistencia validada se limita a la pestana y al usuario,
sin guardar filas ni acciones pendientes. Se mantienen services, permisos,
validaciones y paginacion vigentes. Contrato y pruebas en `../shared/README.md`.
Aceptado funcionalmente por el usuario el 06/11/2026.
