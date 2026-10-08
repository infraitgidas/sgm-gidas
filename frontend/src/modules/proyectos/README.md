# Modulo frontend de proyectos

## Logros y acciones del detalle (ISS-94)

`ProyectosForm` permite cargar `Logros obtenidos` mediante un textarea opcional
de hasta 20000 caracteres. El campo integra validación, errores de backend,
borradores y comparación de diferencias reales en edición. El service mapea
`logrosObtenidos` a `logros_obtenidos` y permite limpiar su contenido enviando null.
`ProyectosDetalle` muestra el texto conservando sus saltos de línea y el historial
lo identifica como `Logros obtenidos`. Los permisos y bloqueos por estado siguen
el contrato del módulo; el dato se incorpora al Excel al cerrar la memoria.

Las acciones superiores del detalle se alinean a la derecha, también si se
distribuyen en varias filas. El botón del gestor se llama `Registrar Informe` y
conserva la navegación a `/informes/pid/nuevo?proyectoId={id}` y el nombre del PID
en el estado de navegación.

## Rutas de edición (ISS-68)

La edición de un proyecto usa `/proyectos/:id/editar` desde el listado, el
detalle y los enlaces internos. `/proyectos/editar/:id` redirige a la ruta
canónica y conserva la búsqueda y el estado de navegación para enlaces previos.
El formulario mantiene el control de permisos y, al guardar, vuelve al detalle
con `successMessage`. El alta sigue volviendo al home.

En Participaciones relevantes, home, detalle y confirmación de baja presentan
el nombre del evento con mayúsculas consistentes mediante `toTitleCase`. El
valor persistido y el formulario conservan la escritura ingresada.

Proyecto y participación rechazan nombres exclusivamente numéricos antes del
envío y muestran el motivo junto al control.

## Errores por campo (ISS-09)

Los formularios del módulo consumen `error.details.fields` mediante
`applyFieldErrors` de `src/lib/httpError.ts`, muestran el mensaje junto al control
y enfocan el primer campo inválido. Los nombres locales de los controles se
vinculan con las claves API, sin cambiar el payload del service ni los permisos.
Los errores sin campo o con campos desconocidos conservan el aviso general;
los errores inesperados muestran un mensaje publico seguro o un fallback accionable, sin identificadores internos.
Se conservan las reglas y el momento de validación existentes. Véase el contrato
transversal en `../README.md`.

## Fechas

En el formulario de proyecto, `Field` muestra el error de fecha de inicio una
sola vez. El texto de ayuda del calendario conserva el formato `DD/MM/AAAA`.

Los períodos de proyectos y de sus participaciones admiten fechas desde el
01/01/2010. Una fecha de finalización no puede preceder a su fecha de inicio;
los cierres conservan la prohibición de utilizar una fecha futura.

## Vistas

El modulo administra proyectos de investigacion y participaciones relevantes.
Los homes muestran hasta 9 elementos por pagina. Los detalles incluyen datos,
auditoria, historial paginado de 3 elementos, `Volver` y acciones condicionadas
por permisos y estado activo.

## Proyectos

### Tabla e historial (ISS-26)

El home utiliza la tabla compartida con hasta 9 proyectos por página, búsqueda,
filtros, ordenamiento y acciones por fila para ver, editar, cerrar o reabrir según
estado y permisos. El historial expandible conserva 3 eventos por página.

Los eventos relacionales `investigadores_ids` y `becarios_ids` se presentan como
vinculaciones o desvinculaciones legibles. Se muestra el nombre conservado por el
backend o, para eventos anteriores, el nombre disponible en el detalle actual;
no se renderizan JSON ni identificadores internos. Las asociaciones incluidas en
el alta son estado inicial y no aparecen como cambios posteriores.

Home y detalle comparten la misma utilidad de presentacion. Los eventos de
investigadores y becarios muestran directamente la accion y el nombre, sin las
etiquetas `Valor anterior` y `Valor nuevo`. La asignacion registrada como
`coordinador_id` se presenta como `Coordinador asignado` seguida del nombre del
investigador; nunca se muestra el ID como descripcion. Fecha y usuario permanecen
visibles y los cambios no relacionales conservan el formato anterior/nuevo.

La presentacion directa usa la opcion optativa de `HistorialCambiosCard`, por lo
que no altera los historiales de otros modulos. Las reglas transversales se
documentan en `frontend/CONVENCIONES_PANTALLAS.md`.

### Coordinador y guardado consolidado (ISS-10)

El coordinador se elige entre investigadores del proyecto. Las nuevas
asignaciones requieren investigador activo sin baja lógica; no se ofrecen
usuarios, becarios ni personas externas como coordinadores.

`ProyectosForm` consulta `/investigadores/` con una clave de React Query propia
(`proyecto-candidatos`) y refresca al montar. Muestra carga, error con reintento,
ausencia de candidatos e instrucciones para agregar investigadores. Las filas
vacías se rechazan antes del envío. Un investigador previamente asociado que
dejó de estar activo se conserva visible; no puede recibir una nueva asignación
como coordinador. El detalle identifica al coordinador inactivo sin ocultar su
nombre ni su historial.

`PersonalProyectoField` busca investigadores y becarios por nombre o apellido.
Presenta hasta cinco candidatos y cinco seleccionados por página, con navegación
Anterior/Siguiente y conteos del filtro. Añadir y quitar modifica únicamente el
estado local; las relaciones se envían juntas al guardar. Las asignaciones previas
mantienen su nombre visible aunque ya no aparezcan entre los candidatos activos.
La lista de candidatos a coordinador también muestra hasta cinco investigadores
por página y conserva la selección al navegar.

`upsertProyectos` envía campos y relaciones en un solo POST o PUT:
`investigadoresIds` pasa a `investigadores_ids`, `becariosIds` a `becarios_ids`
y `coordinadorId` a `coordinador_id`. En alta se envían las selecciones; en
edición únicamente las listas o el coordinador que cambiaron. Omitir una clave
conserva su estado actual. La edición sin cambios no realiza peticiones.
El borrador se limpia y se navega con éxito solo después del guardado completo.

Seguimiento de prueba manual ISS-10: el alta con fecha de fin pasada, de hoy o
futura admite el guardado consolidado; la fecha prevista no cierra por sí sola
el proyecto. Los proyectos cerrados mediante la acción explícita requieren
reapertura antes de editar. Se valida localmente que fin no preceda a inicio.
Guardar muestra un icono animado mientras espera al servidor. Una validación
local o un error de API siempre muestra aviso general, además de los mensajes
por campo y foco en el primero inválido, para evitar un guardado aparentemente
sin respuesta cuando el usuario está al final de la pantalla.

Los permisos ADMIN/GESTOR y los destinos de alta/home y edición/detalle se
conservan. El historial se invalida tras guardar y se presenta con 3 elementos
por página. Prueba automatizada del formulario y service reales:
`tests/proyectoCoordinador.test.ts`. La comprobación visual en Docker queda a
cargo del usuario.

- el service transforma el contrato `snake_case` del backend al modelo de interfaz
- el código de proyecto se maneja como texto alfanumérico, conserva mayúsculas y
  minúsculas y admite hasta 50 caracteres sin conversiones numéricas
- el formulario valida campos obligatorios, coordinador y montos no negativos
- en edicion solo se envian diferencias reales
- altas y bajas de investigadores y becarios se consolidan al guardar
- los cambios de coordinador actualizan las relaciones involucradas en el guardado
- un proyecto cerrado no admite edicion hasta que sea reabierto
- las altas vuelven al home y las ediciones al detalle con `successMessage`
- el formulario conserva un borrador local por usuario y proyecto, solicita
  confirmacion antes de recuperarlo y lo elimina al guardar o descartar

## Participaciones relevantes

- el contrato identifica a la persona mediante
  `participante: { rol: "investigador" | "becario", id }`; IDs iguales de roles
  distintos representan personas diferentes
- el service admite listas planas o envueltas en `data` y conserva compatibilidad
  de lectura con registros anteriores de investigadores
- el formulario permite buscar por nombre, apellido o iniciales sin depender de
  tildes, filtrar por investigadores o becarios y mostrar resultados de a 5
- la búsqueda y el filtro reinician la página; Anterior/Siguiente recorren todas
  las coincidencias sin ampliar indefinidamente el formulario
- la persona elegida se presenta en una tarjeta y la seleccion se consolida al
  guardar; la edicion envia solo diferencias reales y no llama al backend cuando
  no existen cambios
- carga de candidatos, error con reintento, ausencia de opciones y validaciones
  de participante, evento, forma y fecha poseen feedback visible y accesible
- el home usa la tabla compartida con 9 filas por pagina, busqueda, filtros,
  acciones individuales e historial diferido paginado de a 3 eventos
- home y detalle muestran nombre y categoria del participante; el historial
  presenta cambios legibles sin exponer IDs ni JSON
- el detalle consume auditoria e historial y conserva acciones condicionadas por
  permisos y estado activo

## Duracion y prorroga de proyectos (ISS-77)

`ProyectosForm` valida el intervalo inicial inclusivo de 12 a 36 meses con
`validateDuracionProyecto`. El error se presenta junto a fecha fin; en edicion
solo se valida de nuevo cuando cambia una fecha, para conservar proyectos
historicos fuera del rango. El formulario envia solo diferencias reales y no
permite cambiar fechas de un proyecto prorrogado. El alta vuelve al home y la
edicion al detalle con `successMessage`.

`proyectosServices` tipa y transforma `fecha_fin_original`,
`fecha_fin_prorrogada`, `prorroga_motivo`, `prorroga_by_nombre` y
`prorroga_at`. La accion del detalle envia `POST /proyectos/{id}/prorroga` con
`{ motivo }`, exige 10 a 2000 caracteres, muestra errores de campo y evita
envios duplicados. Solo ADMIN y GESTOR pueden verla para proyectos activos sin
prorroga y con fecha final definida; backend aplica los permisos definitivos.
Tras el exito se invalidan lista, detalle e historial y aparece un mensaje de
confirmacion. El evento de historial muestra fin nuevo y justificacion, con
paginacion de tres items.

El detalle muestra fecha de inicio, fecha final original y fecha final vigente
con prórroga; después del cierre distingue la fecha aprobada por prórroga de
la fecha de cierre real. Presenta el motivo y `Decisión de Prorrogación` con
quién la aprobó y cuándo. El home identifica los proyectos prorrogados y usa
el estado de cierre explícito, sin cerrarlos por vencimiento de la fecha
prevista. El cierre con fecha usa
`POST /proyectos/{id}/cerrar`; PUT de solo `fecha_fin` queda reservado para
editar el periodo inicial. El modal exige una fecha cubierta por la Memoria de
un informe PID vinculado, muestra el error sin cerrar el diálogo y ofrece a
GESTOR un botón pequeño `Generar Informe`. La reapertura no se ofrece si la
prórroga venció.

Las consultas y mutaciones siguen React Query mediante los hooks y servicios
del modulo; los errores HTTP se muestran con los helpers compartidos. Las
pruebas de limites y presentacion estan en
`tests/proyectoDuracion.test.ts` y `tests/proyectoCoordinador.test.ts`.

## Services, hooks y contratos

Los services concentran HTTP, conversion de datos y payloads tipados. Los hooks
encapsulan React Query e invalidan listas, detalles e historiales despues de cada
mutacion. No existen fallbacks mock ante errores: los fallos de permisos, sesion o
conectividad se propagan para mostrar feedback real y accionable.

`ProyectoPayload.codigoProyecto` y `ProyectoApiResponse.codigo_proyecto` utilizan
`string`. La validación compartida del código exige un valor no vacío, con máximo
50 caracteres y patrón `[A-Za-z0-9]+`; el formulario envía el valor recortado y
muestra el error junto al campo.

## Seguridad y permisos

Las acciones de alta, cierre, reapertura, edicion y baja se condicionan con las
capacidades del usuario, sin considerar la interfaz como unica barrera. Los errores
se normalizan mediante el helper compartido y no se reflejan estructuras desconocidas
del servidor. No se utiliza HTML inyectado, storage del navegador ni `fetch` directo.

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
El cierre usa ConfirmDialog con fecha de cierre y texto Cerrando; la
reapertura de una selección bloquea nuevas acciones hasta finalizar.

## Indicadores de campos obligatorios (ISS-21)

En proyectos son obligatorios codigo, nombre, tipo, fecha de inicio y fecha de
fin inicial. El coordinador se indica como obligatorio cuando se seleccionan
investigadores. Las relaciones y los demas datos opcionales no llevan marca.
Participaciones marca participante, evento, forma y fecha.

## Errores de Participaciones (ISS-19)

ParticipacionesForm aplica `error.details.fields` mediante `applyFieldErrors`.
`participante`, `nombre_evento`, `forma_participacion` y `fecha` se vinculan a
los controles visibles. Los conflictos y campos desconocidos mantienen un aviso
general; alta y edicion indican como reintentar.

## Borradores de formularios (ISS-22)

En proyectos y participaciones, los cambios no se guardan como borrador mientras se escribe.
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

En ProyectosDetalle y ParticipacionesDetalle, las etiquetas de datos y los encabezados de tarjetas
usan peso seminegrita y color pizarra oscuro para distinguirse del contenido.
La disposición, los textos, las acciones y el contrato permanecen iguales.

## Rendimiento de la consulta PID (ISS-94)

ProyectosHome conserva su paginacion del servidor de nueve elementos y
los contratos de services, filtros y permisos. El backend precarga
distinciones y limita relaciones/columnas de participantes al contenido
del listado, manteniendo los datos usados por las vistas.
La mejora fue validada tecnicamente junto con el flujo de Memorias y
aceptada por el usuario como parte de la etapa de rendimiento.
