# Produccion

## ISS-82: autores bibliográficos e historial de Documentación

El formulario de Documentación conserva la búsqueda, selección y creación de
autores. Los autores se administran además en Catálogos, donde se editan, dan
de baja y consultan sus cambios; las correcciones de nombre se reflejan en las
documentaciones activas. Los nombres guardados en versiones cerradas de
Memorias no cambian.

`documentacionHistory.ts` presenta solo cambios de los campos de Documentación
(`titulo`, `editorial`, `anio`, `fecha`, `grupo_id`) y eventos `autores` de
vinculación o desvinculación. Omite cambios propios del autor y eventos
técnicos ajenos al documento. Los historiales conservan tres eventos por página
en home y detalle; el historial propio del autor se ve en Catálogos.

## ISS-39: Documentación y Biblioteca

`DocumentacionHome` usa la tabla compartida con un máximo de 9 documentos por
página. Permite buscar por título, editorial, año o autor; filtrar por estado,
autor y año; ordenar por título; y abrir el detalle desde cada fila. Las acciones
de ver, editar y eliminar se muestran según permisos y estado. La eliminación
requiere confirmación y muestra feedback. Se conserva el contexto de Memorias.
El historial se consulta al expandir una fila, con 3 eventos por página,
reintento y estados de carga y vacío. `DocumentacionDetalle` muestra datos,
Auditoría e Historial de cambios, con 3 eventos por página y regreso al origen.

`DocumentacionForm` usa `DocumentacionAutoresField` para buscar autores por
nombre o iniciales, añadir existentes, preparar autores nuevos y quitar
selecciones. La búsqueda omite nombres ya seleccionados y muestra 5 resultados
por página, con navegación Anterior/Siguiente. Los autores seleccionados también
se muestran de a 5. Las altas y bajas se aplican al guardar, no al interactuar con el
selector. El formulario exige al menos un autor, valida nombres y duplicados,
envía solo diferencias en edición y evita la actualización si no hay cambios.
Los borradores anteriores con filas vacías de autor se recuperan sin esas filas.
El alta vuelve al home y la edición al detalle con `successMessage`.

`documentacionServices.ts` define los tipos y adapta listas, detalle, historial y
payloads del backend. `DocumentacionHome` consume la consulta paginada descrita en ISS-94;
`useDocumentacion` conserva el acceso a listas completas para otros consumidores.
`documentacionAutores.ts` concentra la búsqueda y
normalización de nombres; `documentacionHistory.ts` filtra inicializaciones y
valores equivalentes y presenta cambios de campos y eventos de autores sin IDs
internos ni JSON. Las consultas de catálogo e historial tienen estados de error
recuperables. El backend controla definitivamente los permisos: las lecturas
admiten ADMIN, GESTOR y LECTURA; las mutaciones requieren ADMIN o GESTOR.

Validación: aceptación visual y funcional del usuario, 164 pruebas frontend,
`npm run typecheck`, `npm run build:production` y `git diff --check` aprobados.

Los autores nuevos admiten solo letras Unicode y espacios. Revista, reunión y
artículo rechazan nombres exclusivamente numéricos antes de guardar.

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

Las fechas de publicaciones, reuniones, docencia, distinciones, documentación
y registros de propiedad admiten valores desde el 01/01/2010. Cada formulario
mantiene además sus restricciones vigentes sobre fechas futuras y períodos.

## Funcionalidad

El modulo administra actividades de docencia, articulos de divulgacion,
documentacion bibliografica, distinciones, registros de propiedad, trabajos en
reuniones cientificas y trabajos en revistas.

Cada entidad dispone de home, formulario y detalle. Los homes muestran hasta 9
elementos por pagina. Las altas vuelven al home con `successMessage`; las ediciones
vuelven al detalle.

## Servicios y contratos

Los services dedicados concentran las llamadas HTTP, los tipos de payload y la
normalizacion de respuestas. Las listas aceptan el contrato plano heredado y el
contrato `{ data }` sin recurrir a `any`. Los historiales aceptan ambos formatos y
devuelven arreglos tipados.

Los mensajes HTTP se procesan con `getErrorMessage`, compatible con errores tipados
del backend. Los cuerpos de texto o estructuras desconocidas no se reflejan en UI.

## Relaciones

- Documentacion mantiene autores asociados.
- Trabajos en reuniones y revistas mantienen integrantes autores (ISS-12).
- Las altas y vinculaciones se consolidan al guardar el formulario.
- Las desvinculaciones requieren confirmacion y actualizan datos e historial.
- Una edicion sin diferencias reales no llama al endpoint de actualizacion.

## Permisos y seguridad

Las vistas consultan los permisos del usuario para habilitar altas, ediciones y
bajas. Estas restricciones visuales complementan los controles obligatorios del
backend y no se consideran una barrera de seguridad independiente.

Los inputs se recortan, validan y normalizan antes de construir el payload. React
renderiza los valores como texto y el modulo no utiliza HTML no confiable, `eval`,
almacenamiento de credenciales ni llamadas HTTP fuera de services.

## Auditoria e historial

Los detalles presentan datos principales, auditoria e historial de cambios mediante
`HistorialCambiosCard`, cuya paginacion predeterminada es de 3 items. Los eventos
relacionales de autores e investigadores se invalidan junto con el historial despues
de cada operacion.

## Errores y validacion

- Los formularios muestran validaciones junto al campo correspondiente.
- Los errores del servidor usan mensajes seguros y fallbacks accionables.
- Las eliminaciones y desvinculaciones requieren confirmacion y feedback visible.
- La validacion tecnica del modulo comprende pruebas unitarias compartidas,
  `npm run typecheck` y `npm run build`.

## Validaciones de fechas sin duplicados (ISS-09)

Los errores del formulario se muestran una sola vez mediante Field. El
helperText de Calendar/DatePicker contiene exclusivamente ayuda de formato o
rango; no recibe el mensaje de error del formulario. Se conservan los límites,
las reglas de validación y el foco del primer campo inválido.
Docencia tampoco renderiza párrafos manuales para repetir errores de fechas.

## Feedback de acciones (seguimiento ISS-09)

Las acciones asíncronas del módulo usan Button con loading/loadingText
o ConfirmDialog, que espera la promesa devuelta por onConfirm. Durante la
operación se muestra texto de progreso con un icono animado, aria-busy y
role=status. El botón de acción se deshabilita hasta terminar; las
confirmaciones bloquean además cancelar, el fondo y los campos del diálogo.
El estado se libera al resolver o fallar, conservando errores y mensajes de
éxito existentes. Los callbacks basados en React Query deben devolver
mutateAsync para que el diálogo cubra toda la operación.

## ISS-11: feedback del selector de investigadores en trabajos (2026-09-13)

Los formularios de reuniones y revistas distinguen carga inicial, lista vacia y
error de consulta con Reintentar y progreso accesible. El guardado y el selector
se bloquean mientras no existe una respuesta disponible; una actualizacion en
segundo plano con cache conserva opciones y acciones. Las selecciones no se
reinician por fallos o reintentos. No cambian el endpoint, permisos ni payloads.
El componente InvestigadoresQueryFeedback es exclusivo de produccion.

La inspeccion previa del endpoint real devolvio HTTP 200 con dos investigadores
activos; el incidente original de opciones ausentes no se reprodujo. La ampliacion
de autoria queda en ISS-12, independiente de esta mejora.

Validacion: 88 tests frontend (incluidas regresiones de carga, error, reintento y
conservacion de selecciones), typecheck y build:production correctos. La prueba
visual y los guardados en navegador quedan a cargo del usuario.

Validacion backend: 28 tests correctos de historial de trabajos en reuniones/revistas y errores de dominio de produccion (unittest).

## ISS-12: integrantes autores

Las vistas de alta/edición, detalle y home de trabajos en reuniones y revistas
consumen `autores`. Un autor tiene `id`, `rol` (`investigador` o `becario`),
`nombre_apellido`, `tipo` y `activo`. El par `(rol, id)` identifica
al integrante; no se mezclan personas con IDs iguales de categorías distintas.
Se muestran nombres y categorías; no se registran autores externos.

`trabajoAutoresServices.ts` define los contratos, etiquetas, claves y comparación
de colecciones. `useIntegrantesAutores` consulta integrantes activos mediante
`GET /personal-all?activos=true` (normalizado a `/api/v1/personal/all`). El service
filtra ese listado combinado y ofrece únicamente investigadores y becarios;
Personal (PTAA/profesional) queda excluido. La etiqueta visible sigue siendo Autores.

La regla `esAutorSeleccionable` se aplica en el service y en el selector para
excluir categorías no habilitadas e inactivos incluso frente a opciones antiguas.
La caché usa `integrantes-autores / investigadores-becarios`, separada del
listado anterior. Los autores históricos inactivos permanecen en la selección
existente y pueden quitarse, pero no aparecen como nuevas opciones.
Desde los detalles de congresos y revistas, Editar abre el formulario común de
autores de ese trabajo; ambos permiten agregar investigadores y becarios.
En Docker de desarrollo, si Vite conserva módulos anteriores tras editar
archivos del volumen, reiniciar el servicio frontend y comprobar los módulos
servidos por HTTP antes de dar el ajuste por aplicado al entorno.
`IntegrantesAutoresField` permite selección múltiple sin duplicados y bajas
locales. Los autores históricos inactivos siguen visibles y se pueden quitar.
`AutoresQueryFeedback` reemplaza el feedback exclusivo de investigadores:
conserva carga/error/vacío/reintento y mantiene selecciones frente a refetch.

Los services de trabajos envían `autores: [{rol, id}]` junto a los campos del
trabajo en POST/PUT, en una única operación. En edición solo se envía la colección
si cambió realmente, sin considerar cambios de orden; las altas y bajas se
consolidan al pulsar Actualizar. Si no hay cambios no se llama al backend.
Un refetch no sobrescribe el borrador. El formulario requiere al menos un autor,
la UCT configurada y los permisos de alta/edición del usuario. Los detalles
solo habilitan Editar si el registro está activo y el rol lo permite.

Alta vuelve al home y edición al detalle con `successMessage`. El guardado
bloquea el selector, muestra progreso y conserva errores seguros/accionables.
Las fallas al cargar un registro ofrecen reintento; una lista cacheada utilizable
mantiene las acciones habilitadas. Las búsquedas locales admiten nombres de
cualquier autor; el filtro de reuniones usa claves compuestas y categorías.
Homes conservan 9 items y el historial 3 items por página.

Los detalles muestran nombres y tipos de autor y eventos de alta/baja dentro
del historial existente. La búsqueda global usa `extra.autores`. Los snapshots
de memoria reciben autores congelados y el Excel incluye todas las categorías.
El cambio de esquema requiere regenerar el dataset de testing; no hay adaptación
temporal del contrato exclusivo de investigadores.

Pruebas: `tests/trabajoAutores.test.ts` ejecuta selector y formularios reales
mediante SSR/harness de hooks para IDs coincidentes, conservación de inactivos,
altas/bajas locales, guardado único, navegación, refetch y edición sin cambios.
`tests/investigadoresFeedback.test.ts` conserva las regresiones de ISS-11,
actualizadas a integrantes autores. Validación técnica: npm test, typecheck
y build:production; validación del navegador contra backend temporal.

## ISS-12: buscador de autores con confirmación explícita

IntegrantesAutoresField, compartido por congresos y revistas, filtra localmente
por fragmentos de nombre/apellido o prefijo de iniciales, sin distinguir tildes
ni mayúsculas. Permite categoría Investigador/Becario y muestra hasta cinco
resultados por página con navegación Anterior/Siguiente. Cambiar búsqueda o
categoría reinicia la página. El listado excluye seleccionados, personal e
inactivos. La selección muestra hasta cinco autores por página.
Cada resultado tiene Añadir; escribir, perder foco o pulsar Enter en el buscador
no añade ni envía el formulario. Autores seleccionados permite Quitar;
las relaciones se persisten únicamente al guardar el formulario. Los controles
se bloquean durante guardado según el formulario. Etiquetas asociadas, botones
con type=button y estado de resultados anunciado. Sin cambio de API: se reutiliza
la consulta cacheada de integrantes; la búsqueda y paginación son locales,
no paginación de servidor. La validación visual queda a cargo del usuario.

## ISS-13: fecha de presentación

TrabajosReunionForm, Detalle y Home consumen fecha_presentacion. El formulario
usa Fecha de presentación, mantiene Calendar institucional y envía solo
diferencias; alta vuelve al home y edición al detalle con successMessage.
El service tipa la fecha nueva y admite fecha_inicio únicamente al normalizar
respuestas antiguas; no envía ese nombre anterior. Home filtra el año civil
y muestra la fecha de presentación. Detalle etiqueta la fecha y adapta
eventos históricos fecha_inicio/fecha_presentacion a Fecha de presentación
con valores formateados, conservando paginación de tres y permisos de edición.
No se modifica el flujo de revistas, cuya fecha ya tiene otro contrato.
No se modifican hooks compartidos ni componentes globales.

## ISS-14: enlace al trabajo o DOI

Formularios de congresos/reuniones y revistas ofrecen un input URL opcional,
con placeholder DOI y máximo 2048 caracteres. `utils/trabajoEnlace.ts` valida
HTTP/HTTPS y longitud al guardar; el backend valida de manera independiente.
El DOI debe ser una URL completa https://doi.org/… . Vaciar elimina el enlace
mediante null; edición envía solo diferencias y no solicita cambios si no hay.
Los errores API `enlace` se muestran en el campo. No se normalizan mayúsculas.
Services dedicados tipan `enlace?: string | null` y normalizan ausentes a null.

Detalle muestra la URL como enlace solo cuando pasa `enlaceSeguro`, con
target=_blank, rel=noopener noreferrer y aviso accesible de pestaña nueva.
Mantiene permisos, navegación e historial de tres items; home conserva nueve.
No hay consultas adicionales ni previsualización remota del destino.
Regresiones SSR/harness en trabajoAutores.test.ts verifican apertura segura,
validación, carga/edición, alta, eliminación y diferencias reales.

La validación también rechaza hosts inválidos; admite dominios internacionalizados
y hosts IPv6 válidos mediante los analizadores de URL de cada plataforma.

## ISS-17: presentaciones programadas y errores seguros

TrabajosReunionForm admite fechas de presentación futuras para registrar trabajos
ya programados y mantiene como límite inferior el 01/01/2010. La ayuda del campo
explicita ambos comportamientos. Los errores de guardado conservan el mensaje
seguro y accionable del contrato o el fallback del formulario, pero no muestran
la referencia interna de seguimiento. ISS-18 extiende esa regla a todos los
formularios mediante el helper común.

## Indicadores de campos obligatorios (ISS-21)

Los formularios de produccion muestran el indicador en los datos obligatorios, incluidos los autores de documentacion y trabajos. Los enlaces opcionales permanecen sin marca.

## Errores de formularios (ISS-19, en curso)

Los formularios no infieren campos inválidos a partir de palabras del mensaje del servidor. Solo `error.details.fields` se asocia a controles mediante `applyFieldErrors`; los demás errores conservan el aviso general. Los servicios de artículos, distinciones, trabajos, docencia, documentación y registros identifican campos conocidos de texto, fecha, catálogos y relaciones. Los formularios de docencia, documentación y registros usan fallbacks distintos para alta y edición.

## Borradores de formularios (ISS-22)

En formularios de producci?n, los cambios no se guardan como borrador mientras se escribe.
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

## ISS-27: grilla de Actividades en Docencia

El home de Actividades en Docencia usa la tabla compartida con Personal y
Proyectos. Presenta hasta 9 filas por pagina, busqueda local, filtros por estado,
curso, institucion, investigador, grado y rol, ordenamiento y navegacion desde la
fila. Ver detalle, Editar y Eliminar se muestran por registro segun permisos;
editar y eliminar solo estan disponibles para actividades activas.

El service normaliza `grado_academico` y `rol_actividad`, compatibles con texto
heredado y con el contrato `{ id, nombre }`. El historial se consulta al expandir
una fila y muestra 3 eventos por pagina. El desplegable y la tarjeta del detalle
son informativos, omiten campos heredados de acciones y presentan los cambios de
grado con nombres legibles. El grado asignado durante el alta no se considera un
cambio.

La baja sigue siendo logica y conserva confirmacion, invalidacion de consultas y
mensajes seguros. La barra horizontal de filtros usa un scrollbar compacto local,
sin modificar estilos globales.

## ISS-28: grilla de Registros de propiedad

El home de Registros de propiedad usa la tabla compartida con Proyectos,
Personal y Actividades en Docencia. Presenta hasta 9 filas por pagina, busqueda
local, chips de estado y selectores de tipo y fecha dentro de una barra con
desplazamiento horizontal cuando el ancho disponible lo requiere.

Cada fila permite ver el detalle y, para registros activos, editar o eliminar
segun los permisos vigentes. La baja conserva su confirmacion individual, el
soft delete, los mensajes seguros y la invalidacion de la consulta.

El historial se consulta de forma diferida al expandir una fila y muestra 3
eventos por pagina, con estados de carga, error recuperable y vacio. Home y
detalle omiten campos de acciones, inicializaciones y valores sin diferencias.
Los valores estructurados se presentan mediante nombres conocidos y nunca por
coercion implicita, evitando `[object Object]`.

El contrato normal de lectura entrega `tipo_registro` y `grupo` como cadenas. La
presentacion aplica una normalizacion defensiva compatible con respuestas
heredadas que incluyan objetos con nombre, sin alterar el payload de escritura.

## ISS-30: grilla de Trabajos en reuniones

El home de Trabajos en reuniones usa la tabla compartida con 9 filas por pagina,
busqueda y filtros por estado, tipo, procedencia, autor y anio. La barra mantiene
chips y selectores alineados y usa el scrollbar horizontal compacto local del
patron aprobado. Cada fila navega al detalle y ofrece acciones individuales segun
estado y permisos; se retiraron la seleccion masiva y el panel lateral anterior.

El historial se carga al expandir una fila y muestra 3 eventos por pagina con
estados de carga, error recuperable y vacio. Se omiten acciones tecnicas,
inicializaciones y valores equivalentes; los valores estructurados se normalizan
para evitar IDs, JSON y `[object Object]`.

Los eventos de autor usan presentacion directa tanto en home como en detalle:
`Autor vinculado` o `Autor desvinculado`, nombre y categoria, fecha y usuario. No
muestran `Valor anterior` ni `Valor nuevo`. El detalle utiliza la opcion optativa
de presentacion de `HistorialCambiosCard`; los demas consumidores mantienen su
formato ordinario.

El hook del listado expone carga inicial, actualizacion y reintento. Se conservan
el contrato de autores investigadores/becarios, la fecha de presentacion, el
contexto de Memorias, la baja logica y los permisos vigentes.

Validacion: 135 pruebas frontend, prueba focalizada 5/5, typecheck, build de
produccion, 46 pruebas backend focalizadas y `git diff --check` correctos.

## ISS-32: contrato y grilla de Trabajos en revistas

El formulario obtiene los tipos desde el service y hook dedicados de
`tipos-revista`; presenta `Nacional` e `Internacional` sin reutilizar el
catálogo de reuniones. El payload usa `tipo_revista_id` y
`fecha_publicacion`, visible como `Fecha de publicación`. La selección de al
menos un autor es obligatoria y los errores del backend se asocian al selector
sin perder los datos cargados.

El home usa la tabla compartida con 9 filas por página, búsqueda por trabajo,
revista, editorial, ISSN, país, tipo o autor, filtros horizontales y acciones
individuales según estado y permisos. Conserva el contexto de Memorias, el
feedback de carga/error y la baja lógica. El hook del listado expone carga
inicial, actualización y reintento.

El historial se consulta al expandir una fila y muestra 3 eventos por página.
Home y detalle comparten `trabajoRevistaHistory.ts`: omiten acciones técnicas,
inicializaciones y valores equivalentes; presentan el catálogo por nombre, las
fechas en formato civil y las vinculaciones o desvinculaciones de autores como
acciones legibles.

El alta vuelve al home y la edición al detalle con `successMessage`. Los
services normalizan el contrato tipado y mantienen las escrituras dentro de las
rutas de Producción.

Validación: aceptación visual y funcional del usuario, 140 pruebas frontend,
`typecheck`, build de producción, 50 pruebas backend focalizadas y
`git diff --check` correctos.

## ISS-33: grilla de Distinciones recibidas

El home de Distinciones recibidas usa la tabla compartida con 9 filas por
página, búsqueda por descripción, proyecto o fecha y filtros horizontales por
estado, proyecto y año. Cada fila conserva la navegación al detalle y ofrece
acciones individuales de edición y baja lógica según el estado y los permisos.

El historial se consulta al expandir una fila y muestra 3 eventos por página,
con estados de carga, error recuperable y vacío. Home y detalle comparten
`distincionHistory.ts`: omiten acciones técnicas, inicializaciones y valores
equivalentes, y presentan las fechas y los proyectos con etiquetas legibles sin
exponer IDs ni estructuras serializadas.

El formulario mantiene las altas con retorno al home y las ediciones con retorno
al detalle mediante `successMessage`. En edición envía únicamente diferencias
reales; las validaciones de fecha, descripción y proyecto se muestran una sola
vez junto al control correspondiente.

Validación: aceptación visual y funcional del usuario, prueba focalizada 5/5,
145 pruebas frontend, `typecheck`, build de producción, 28 pruebas backend
focalizadas y `git diff --check` correctos.

## ISS-34: grilla de Artículos de divulgación

El home de Artículos de divulgación usa la tabla compartida con 9 filas por
página, búsqueda por título, descripción, UCT o fecha y filtros horizontales por
estado, UCT y año. Cada fila navega al detalle y ofrece acciones individuales de
edición y baja lógica según el estado y los permisos vigentes. Se retiraron las
tarjetas, la selección masiva y el panel lateral de filtros.

El historial se consulta al expandir una fila y muestra 3 eventos por página,
con estados de carga, error recuperable y vacío. Home y detalle comparten
`articuloDivulgacionHistory.ts`: omiten acciones técnicas, inicializaciones y
valores equivalentes, y presentan fechas, UCT y objetos con etiquetas legibles
sin exponer IDs ni estructuras serializadas.

El formulario mantiene las altas con retorno al home y las ediciones con retorno
al detalle mediante `successMessage`. En edición envía únicamente diferencias
reales, asocia `fecha_publicacion` al control visible y muestra cada error una
sola vez. El título identifica al artículo, pero no es único: se admiten varios
artículos con el mismo título.

Validación: aceptación visual y funcional del usuario, prueba focalizada 5/5,
150 pruebas frontend, `typecheck`, build de producción, 5 pruebas backend de
Artículos de divulgación y `git diff --check` correctos.

## Títulos de detalle (ISS-88)

En los detalles de producción, las etiquetas de datos y los encabezados de tarjetas
usan peso seminegrita y color pizarra oscuro para distinguirse del contenido.
La disposición, los textos, las acciones y el contrato permanecen iguales.

## Docencia y Biblioteca: consultas paginadas (ISS-94)

`DocenciaHome` usa `getActividadesDocenciaPage` y
`DocumentacionHome` usa `getDocumentacionPage`, con tipos de parametros
dedicados y los adaptadores de sus services actuales. Cada llamada solicita
nueve registros y envia busqueda, filtros y orden al backend. Los totales
y opciones completas se consumen de `meta`; no se filtra una pagina
localmente como si fuera el listado completo.

Las claves son `["docencia", "table", params]` y
`["documentacion", "table", params]`, con `staleTime=60_000`.
Las altas, ediciones y bajas siguen invalidando esos prefijos. Desde
Memorias se transmiten IDs y `activos=all`, incluidos conjuntos vacios,
y se conserva el contexto para navegar al detalle y regresar.

Los cambios de filtros/orden reinician la pagina. Durante la consulta de
otra pagina se espera la nueva metadata antes de corregir un numero fuera
de rango. Se mantienen la grilla, los permisos, mensajes, reintento,
confirmaciones y el historial de tres eventos. Los services de listas
completas y `useDocumentacion` siguen disponibles para otros consumidores.
Las pruebas de transicion y contrato se encuentran en
`tests/transferenciasTable.test.ts`; la grilla e historial de Docencia
siguen cubiertos por `tests/docenciaTable.test.ts`.
