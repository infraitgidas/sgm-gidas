# Modulo frontend de personal

## Filtros desplegables (ISS-47)

PersonalHome: clase y estado.
Los filtros del listado utilizan `TableFilterSelect`, con nombre accesible y
selección mediante teclado. Todos/Todas elimina la restricción del criterio.
La adaptación del selector conserva valores, setters y opciones de consulta;
se mantienen services, permisos, nueve filas por página, contexto de Memoria
y persistencia de filtros de ISS-50. No se modifican campos de formularios.

Aceptado visual y funcionalmente el 06/11/2026. Validación integrada:
269 pruebas frontend, TypeScript y build de producción aprobados.
`tests/homeFilterSelect.test.ts` comprueba selección y limpieza en las cuatro
pantallas principales y ausencia de chips de filtrado en los homes.

## Resumen seguro del historial de becas (ISS-41)

`utils/personalHistory.ts:formatPersonalHistoryEntry` resume los eventos del
campo `becas` tanto en `PersonalDetalle` como en el historial de `PersonalHome`.
Reconoce vinculación, actualización y desvinculación con `accion`/`detalle`,
incluidos valores almacenados como texto JSON con hasta dos niveles de
serialización y detalles serializados. También resume objetos y colecciones
históricas; muestra valores anteriores y nuevos cuando ambos están disponibles.

La presentación solo usa nombre o referencia de beca, fechas civiles válidas y
monto numérico en ARS. Conserva el cero y distingue monto nulo y fin abierto.
Una entrada inesperada muestra `Se registró un cambio en las becas asignadas.`
en lugar de JSON, valores arbitrarios o `[object Object]`. El parser no modifica
los registros ni completa datos ausentes con valores actuales.

Se mantienen tarjeta compartida, fechas y usuarios del historial, permisos,
navegación y paginación de tres elementos. No cambian services, hooks, contratos
HTTP ni validaciones del formulario. `tests/personalHistory.test.ts` cubre
formatos actuales e históricos, datos inesperados y la tarjeta real mediante
SSR con ambas páginas de resultados. Aceptación del usuario: 05/11/2026.
Validación: 239 pruebas frontend, 12 backend, TypeScript y build aprobados.

## Becarios: detalle y precarga de becas (ISS-40)

`PersonalDetalle` conserva encabezado, permisos, navegación y contexto de memoria.
Para becarios, `components/BecarioDatosSection.tsx` presenta dos tarjetas con
alturas independientes: datos personales y becas asignadas. La grilla usa una
columna flexible y otra de 330 px, con separación de 24 px; una consulta de
contenedor las apila cuando el ancho disponible es menor a 1000 px. Los campos
usan dos columnas desde 480 px disponibles y una en espacios menores.

Los datos muestran nombre, apellido, DNI, CUIL, alta y tipo de formación. Las
horas se separan mediante un borde y conservan el desplegable de su historial.
Las asignaciones muestran nombre, período, estado, monto percibido y enlace
`/becas/<id>`, sin descripción extensa. El monto usa formato monetario ARS,
conserva el cero e informa `Sin registrar` si es nulo o está ausente.
El estado usa fechas civiles locales: próxima antes del
inicio, activa desde el inicio hasta el fin inclusive, finalizada después del
fin; sin fecha de fin continúa activa. Un inicio ausente se informa sin asumir
vigencia. El estado vacío conserva la tarjeta y el texto
`Este becario no tiene becas asignadas`.

El enlace a la beca transporta `becarioReturnTo` con el detalle de origen,
query, hash y contexto de navegación, sin repetir mensajes de éxito anteriores.
Volver desde la beca restaura ese detalle y su contexto de memoria o búsqueda.
El retorno también se conserva al editar la beca, cancelar, guardar sin cambios
o limpiar el mensaje de éxito. El acceso directo a una beca vuelve a `/becas`.
El breadcrumb compartido usa ese origen para mostrar
`Inicio > Personal > Becario > Beca` y agrega `Editar` cuando corresponde;
sus enlaces restauran el estado de cada destino.

Historial y auditoría quedan fuera de la grilla y ocupan todo el ancho, en ese
orden, seguidos de Volver. Se conserva el formato de ambas tarjetas y el
historial compartido sigue siendo desplegable y pagina tres elementos. El icono
History se agrega al componente global `HistorialCambiosCard`, autorizado por
el usuario para sus consumidores. Auditoría se compone en `PersonalDetalle` y
agrega ShieldCheck para las clases de Personal; no existe una tarjeta global de
auditoría. User, GraduationCap y CalendarDays completan la sección del becario.
Todos los iconos son decorativos y usan `aria-hidden="true"`.

El detalle consume `GET /personal/becario/<id>`, incluida su colección `becas`.
`PersonalCompleto.tipo_formacion` tipa el nombre que devuelve el backend y sirve
de respaldo cuando no hay un catálogo anidado en `relaciones`. La misma colección
precarga el formulario existente; el guardado sigue enviando solo diferencias,
sin PUT si no hubo cambios ni escrituras de relaciones al editar filas locales.
Editar requiere registro activo y `canEditRecords()`. La carga conserva el
skeleton; errores de consulta e historial tienen aviso accesible y reintento.

Validación técnica: `becarioDetalle.test.ts` comprueba contenido, estados,
vacío, enlaces, orden, permisos, carga, error y paginación con SSR y mocks de
consultas. `becarioEdicionBecas.test.ts` cubre hidratación y diferencias del
formulario real. El usuario aprobó el aspecto y, tras los ajustes de retorno,
monto y breadcrumb, solicitó ejecutar los commits de la etapa el 05/11/2026.
Validación final: 234 pruebas frontend, TypeScript y build de producción
aprobados; 27 pruebas backend del flujo aprobadas. La tarea ISS-40 queda cerrada.

## Validacion preventiva de formularios (ISS-33)

`FormPTAAProfesional`, `FormBecario` y `FormInvestigador` validan Nombre,
Apellido, DNI, CUIL y horas al escribir y al salir del campo. Nombre y apellido
admiten 60 caracteres cada uno y 120 en conjunto; DNI admite 7 u 8 digitos y
CUIL exige formato, coincidencia con DNI y digito verificador. Horas exige
enteros entre 1 y 168. Cambiar Nombre revalida el limite conjunto y cambiar DNI
revalida CUIL. `updatePersonalErrors` conserva los errores ajenos al cambio.
El submit muestra conjuntamente todos los errores vigentes y enfoca el primero.
`tests/personalGuardarFeedback.test.ts` cubre los tres formularios reales.

Se conservan API, permisos, borradores y navegacion. Etapa aceptada por el usuario
el 05/11/2026; las comprobaciones no disparan escrituras de dominio.

## Nombre, apellido, fechas e historial (ISS-34, ISS-35, ISS-36)

Los formularios de Personal, Becario e Investigador muestran exclusivamente
`Nombre` y `Apellido`, ambos obligatorios, mediante el componente del módulo
`NombrePersonalFields`. Cada campo admite letras Unicode y espacios, hasta
60 caracteres, con 120 en conjunto incluido el separador. No existe una variante
de formulario para nombres históricos: el dataset ficticio de desarrollo fue
normalizado mediante una migración controlada y auditada de 112 registros.

`personalServices`, `becarioServices` e `investigadorServices` incluyen los dos
campos en sus contratos; `personalCompletoServices` los recibe para precargar la
edición. Los borradores guardan ambos por separado. La edición envía únicamente
diferencias y omite el PUT si no hubo cambios; alta vuelve al home y edición al
detalle con `successMessage`. Los errores de API de nombre y apellido se asocian
a los controles visibles mediante el manejo existente y `personalFieldErrors`.

`utils/personalValidation.ts` reúne las validaciones de nombre y fecha de alta.
La fecha admite desde 01/01/2010 hasta hoy inclusive: Calendar recibe `maxDate`
y el envío vuelve a comprobar el rango. La API aplica el mismo límite.

`PersonalHome` y `PersonalDetalle` usan `formatPersonalHistoryEntry`, que muestra
las etiquetas de catálogo resueltas por el backend para el valor anterior y el
nuevo. Las referencias ausentes muestran `Referencia no disponible`; el detalle
ya no necesita cinco consultas auxiliares a catálogos para presentar el historial.
Se conservan nueve registros por home, tres eventos por página de historial,
los hooks existentes, permisos y feedback de guardado.

Verificación: 208 pruebas frontend, TypeScript y build de producción aprobados.
La suite de guardado ejercita los tres formularios; `personalNombresFechas.test.ts`
verifica nombres compuestos, campos obligatorios, límites de fecha y etiquetas.
Aceptación visual y funcional del usuario el 04/11/2026.

## Baja y reactivacion (ISS-39)

`PersonalHome` permite localizar registros mediante Inactivos o Todos y muestra
Reactivar solo para integrantes inactivos y usuarios con permiso de edicion.
La confirmacion conserva identidad y relaciones; `reactivarPersonal` consume
`PUT /personal/:rol/:id/restore`. El exito actualiza listado, detalle e historial
y muestra el aviso correspondiente. Los errores permanecen visibles en el dialogo.

La confirmacion de baja ofrece un motivo opcional con etiqueta, placeholder y
limite de 500 caracteres. `eliminarPersonal` envia el motivo junto al DELETE;
el historial existente muestra el motivo y los cambios de estado, con tres
eventos por pagina. Los filtros y el home mantienen nueve registros por pagina.
El error de DNI inactivo en alta orienta hacia Personal > Inactivos.

Validacion: TypeScript y build de produccion correctos; usuario confirma motivo
en historial y reactivacion visible en Activos el 04/11/2026.

## Error de becas en Becario (ISS-74)

La casilla «Vincular beca existente» referencia el error global de becas mientras está
visible. El mensaje tiene un identificador estable y `role="alert"`; la casilla
expone `aria-invalid` solo cuando corresponde. La validación y el guardado
mantienen el contrato actual del formulario.

Al crear o editar un becario, `PersonalHome` y `PersonalDetalle` anuncian el
`successMessage` recibido tras la navegación mediante una región de estado
oculta visualmente, además de conservar el aviso visible.

## Identidad documental (ISS-76)

Las vistas `PersonalForm` (Personal/PTAA/Profesional, Becario e Investigador)
comparten `components/IdentidadFields.tsx` para DNI y CUIL. Ambos campos son
obligatorios en altas y al completar una identidad heredada en edicion. La
validacion de `utils/identidadValidation.ts` exige DNI de 7 u 8 digitos y CUIL
`XX-XXXXXXXX-X`, con el DNI en sus ocho posiciones centrales y digito
verificador correcto. Los inputs muestran placeholders, errores junto al campo
y referencias accesibles mediante `Field`.

Los tres services dedicados incluyen `dni` y `cuil` en sus tipos TypeScript y
payloads; `personalCompletoServices` los recibe como `string | null` para
registros anteriores a la migracion. Los formularios guardan ambos valores en
su borrador y envian solo diferencias reales al editar. Una colision del DNI o
CUIL, o un valor invalido, se muestra junto al campo a partir de
`error.details.fields`. El detalle presenta ambos datos y el historial muestra
sus modificaciones. `usePersonal` sigue consultando el home con nueve elementos
por pagina; los permisos de lectura y escritura existentes gobiernan estas
vistas sin una ruta adicional.

Pruebas: `tests/identidadPersonal.test.ts`, las suites de formularios de Personal,
`npm run typecheck` y `npm run build:production`.

## Rutas de edición (ISS-68)

El detalle de Personal navega a `/personal/:rol/:id/editar` para personal,
becarios e investigadores. Los alias públicos previos siguen disponibles para
enlaces existentes. El formulario conserva permisos, guardado y retorno al
detalle con `successMessage`.

## Tabla y formularios de Personal (ISS-25)

`PersonalHome` consume el listado paginado de servidor mediante `usePersonal` y
la tabla global controlada. Presenta hasta 9 integrantes por pagina, busqueda,
chips de clase y estado en una sola hilera, y ordenamiento por nombre, clase,
clasificacion, grupo, horas, estado o fecha de alta. Al cambiar criterios vuelve
a la primera pagina. TanStack Query conserva la pagina visible durante el
refetch y la tabla muestra una transicion discreta.

Una fila completa abre el detalle. Las acciones con iconos permiten ver, editar
o eliminar segun rol y estado; los controles internos no activan el click de la
fila. La flecha izquierda expande el historial y lo consulta solo al abrirlo. La
cache se separa por `rol + id` y cada historial muestra 3 eventos por pagina,
con carga, error recuperable y estado vacio propios. Los eventos relacionales de
becas se formatean como informacion legible y no exponen el JSON de auditoria.

`Agregar nuevo` navega a `/personal/nuevo` y conserva la clase seleccionada en
la URL. El alta permite elegir Personal, Becario o Investigador mediante opciones
visibles. En edición puede corregirse la clase de un alta errónea, según las
reglas de reclasificación. El catálogo se presenta como `Tipo de Personal`.

Categoria UTN y Programa de Incentivos son opcionales para investigadores. Los
selectores ofrecen valores explicitos sin relacion y el payload envia `null`
solo al quitar una asignacion existente. Todos los formularios de edicion envian
unicamente diferencias reales. `Volver` navega directamente cuando no hubo
cambios y conserva la confirmacion de borrador cuando existen modificaciones.

Las altas, ediciones y bajas invalidan las consultas de Personal necesarias para
que el home y el detalle se actualicen al navegar.

## Borradores (ISS-22)

`PersonalForm` abre la clase indicada por `?tipo=PERSONAL|BECARIO|INVESTIGADOR`
al seguir un enlace desde la lista de borradores. Cada formulario especializado
usa `useFormDraft` con una clave distinta: `personal-personal`,
`personal-becario` o `personal-investigador`, y el ID del registro en edición.
Las fechas se serializan como fechas civiles; al recuperar un becario también
se reconstruyen las fechas de sus becas. Se conserva un solo borrador por
usuario, clase y registro. En Personal, Becario e Investigador no hay guardado
automático: Volver detiene la navegación hasta que el usuario elige guardar el
borrador, descartarlo o seguir editando. Guardar el registro elimina su borrador.
La lista del perfil actualiza inmediatamente el elemento al guardar o descartar.

Los tres formularios permanecen separados. Esta funcionalidad no cambia sus
contratos de alta y edición ni sus validaciones de nombre y relaciones.

Los tres formularios de personas admiten solo letras Unicode y espacios en
nombre y apellido. Rechazan números y signos antes de guardar y muestran el
error junto al campo.

## Errores por campo (ISS-09)

Los formularios del módulo consumen `error.details.fields` mediante
`applyFieldErrors` de `src/lib/httpError.ts`, muestran el mensaje junto al control
y enfocan el primer campo inválido. Los nombres locales de los controles se
vinculan con las claves API, sin cambiar el payload del service ni los permisos.
Los errores sin campo o con campos desconocidos conservan el aviso general;
los errores inesperados muestran un mensaje publico seguro o un fallback accionable, sin identificadores internos.
Se conservan las reglas de validacion; ISS-33 incorpora feedback preventivo. Véase el contrato
transversal en `../README.md`.

ISS-19: los errores de nombre, fecha de alta y catálogos del backend se asocian a los controles existentes mediante `applyFieldErrors`. Los formularios conservan el borrador y el aviso general cuando la respuesta no identifica un campo visible.

## Fechas

Seguimiento ISS-08: ingresar 2008 en una fecha de alta no cambia el valor
confirmado; Calendar explica el límite 01/01/2010 junto al campo y lo resalta.

Las altas al grupo admiten fechas desde el 01/01/2010 hasta hoy; los períodos
de sus relaciones conservan sus reglas propias. Esta regla describe actividad institucional y no debe extenderse a
fechas biográficas o de identidad.

## Vistas

- `PersonalHome`: listado con hasta 9 elementos por pagina.
- `PersonalForm` y formularios especializados: alta y edicion por tipo.
- `PersonalDetalle`: datos, auditoria e historial de cambios.

## Capas

- `services`: contratos HTTP y tipos TypeScript.
- `hooks`: consultas reutilizables con React Query.
- `pages`: estado de formulario, validacion y navegacion.
- `components`: piezas internas del modulo.

## Formularios

### Seguimiento ISS-08: listado actualizado y feedback de guardado

Las altas y ediciones de Investigador invalidan las consultas `personal`,
`investigadores` y `proyecto-candidatos` antes de navegar; la edición también
invalida su detalle y datos iniciales. Los tres formularios especializados
mantienen `isSaving` durante el envío y la actualización de consultas,
deshabilitan Guardar/Actualizar y muestran un icono de carga y `Guardando...`.
Un error libera el botón y conserva los datos para corregir o reintentar.

Las validaciones locales y los errores del servidor producen un aviso general
visible mediante la notificación existente. Los campos inválidos conservan
sus mensajes y se enfoca el primero con `focusFieldErrors`, haciendo visible
el problema aunque el usuario esté al final de un formulario extenso. Una
validación local no envía una petición al servidor.

El listado combinado de Personal muestra primero las altas más recientes,
sin cambiar el máximo de nueve elementos por página. Pruebas de formulario,
estado de carga, errores y actualización con React Query real:
`tests/personalGuardarFeedback.test.ts` y `tests/personalCatalogForm.test.ts`.

En edicion, investigador, becario, PTAA y profesional comparan el estado
normalizado con los datos iniciales y envian solo las diferencias reales. Si no
hay cambios no ejecutan el `PUT`, pero conservan la navegacion al detalle.

Las becas de un becario se editan localmente y se envian juntas en `becas` al
guardar. El frontend no desvincula ni vincula cada fila individualmente. El
formulario permite seleccionar becas existentes, buscar por beca y muestra hasta cinco vínculos por
página, con navegación Anterior/Siguiente. Los índices reales de los campos se
conservan al filtrar para editar, quitar y validar la beca correcta.
El plazo se registra en el becario: inicio y fin son obligatorios, fin no puede
ser anterior al inicio y el monto sigue siendo opcional. La beca se crea y
administra por separado en Personal > Becas.

La selección inicial define la clase de registro: Personal, Becario o Investigador.
Las dos últimas requieren campos y relaciones especializados. Personal selecciona
`tipo_personal_id` desde todos los tipos activos del catálogo, con sus nombres e IDs
reales, sin filtrar por textos ni resolver automáticamente "Profesional".
`FormPTAAProfesional` conserva su nombre de archivo por compatibilidad, pero sirve
a cualquier tipo del catálogo. Las rutas existentes de edición se mantienen.

Todos los formularios usan las validaciones controladas por React, conservan los
valores ingresados cuando una validacion o peticion falla y muestran el mensaje
junto al campo correspondiente. Los errores no asociados a un campo se anuncian
como feedback general accionable.

## Navegacion

- alta: vuelve a `/personal` con `successMessage`
- edicion: vuelve al detalle del registro con `successMessage`

## Permisos y errores

La UI respeta permisos provistos por auth; el backend sigue siendo la autoridad.
Los formularios especializados informan sus fallos al contenedor `PersonalForm`,
que obtiene un mensaje seguro mediante `getErrorMessage` y lo presenta en un toast
visible. Una operacion fallida detiene la navegacion y nunca muestra exito.

Las cargas usan el mensaje accionable del proyecto. Los contratos aceptan el error
tipado `{ error: { code, message, details } }` y formatos heredados estructurados;
no se reflejan cuerpos de texto desconocidos ni se silencian fallos relacionales.

## Contratos y seguridad

`PersonalCompleto`, becas, catalogos, relaciones e historiales tienen tipos
explicitos. Los services declaran el resultado de altas, actualizaciones, consultas
y bajas. El modulo no usa `any`, HTML no confiable, storage ni `fetch` directo.

## Validaciones

### Corrección del alta PTAA (ISS-08)

`upsertPersonal` usa `POST /personal` sin barra final, conforme al endpoint
vigente. Todos los registros Personal seleccionan un tipo real del catálogo.
No se envían campos de investigador ni becario. Las horas deben ser enteras
entre 1 y 168 y el grupo debe estar disponible.

`utils/personalFieldErrors` interpreta `error.details.fields` solo para campos
conocidos. El formulario muestra errores junto a nombre, horas, tipo y fecha,
o como alerta local para el grupo; mueve el foco al campo afectado. Fallos sin
campo siguen el toast seguro del contenedor. No navega ni informa éxito si falla.
PTAA y Profesional usan `personal` como rol técnico de actualización y detalle,
ya que comparten entidad backend. Se mantienen la navegación de alta al home
y el envío exclusivo de diferencias en edición.

Pruebas automatizadas: `tests/personalAlta.test.ts` (contrato de ruta, mapeo de
errores y invariantes condicionales). No reemplazan la prueba manual del navegador.

- campos obligatorios y horas enteras entre 1 y 168
- fechas y tipos seleccionados
- becas existentes sin duplicados, con fechas de inicio y fin y monto válido cuando se informa
- no realizar peticiones al modificar filas hasta guardar

### Seguimiento ISS-08: horas y catálogo

`utils/weeklyHours` comparte la regla semanal entre Personal, Becario e Investigador
en alta/edición. Los inputs declaran mínimo 1, máximo 168 y paso 1; el submit
controlado impide valores vacíos, fraccionarios, no positivos o superiores a 168.
Los errores de horas devueltos por backend se muestran junto al campo y con foco.
Los datos anteriores no se corrigen automáticamente: al editar una carga inválida
se exige corregirla antes de guardar. No se reescriben historiales ni snapshots.

`useTiposPersonal` refresca al montar el formulario para reflejar altas y cambios
del catálogo; carga, fallo con reintento y catálogo vacío tienen feedback visible.
Un tipo anterior no disponible se muestra deshabilitado al editar, sin sustituir
su ID silenciosamente; para guardar debe seleccionarse un tipo disponible.

Pruebas: `weeklyHours.test.ts`, `personalCatalogForm.test.ts` (formulario real
con harness de hooks/JSX, no navegador), `personalAlta.test.ts` y
`formValidation.test.ts`. Comprobar manualmente en Docker altas/ediciones de las
tres clases, límites 168/169/220 y un tipo con nombre arbitrario del catálogo.

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

## Indicadores de campos obligatorios (ISS-21)

La clase de registro y los campos obligatorios de investigadores y becarios muestran el indicador. Al vincular una beca, la selección, fecha de inicio y fecha de fin son obligatorias; el monto es opcional.

## Paginación de listados (ISS-23)

Los resultados paginados muestran controles centrados de anterior, números
de página y siguiente, inmediatamente debajo de las tarjetas o resultados.
El máximo de resultados por página conserva el contrato del módulo.

## Títulos de detalle (ISS-88)

En PersonalDetalle, las etiquetas de datos y los encabezados de tarjetas
usan peso seminegrita y color pizarra oscuro para distinguirse del contenido.
La disposición, los textos, las acciones y el contrato permanecen iguales.

## Lecturas auxiliares de personal (ISS-94)

Los services de Investigadores y Becarios conservan sus tipos y contratos.
El backend precarga las relaciones que devuelve, por lo que formularios y
selectores mantienen los mismos datos con menos peticiones SQL internas.
Las colecciones relacionadas sin orden contractual deben ordenarse en el
consumidor si la vista lo necesita. PersonalHome conserva la paginacion
combinada del servidor de nueve filas, sus filtros, permisos e historial.

La validacion de la etapa incluyo 648 pruebas backend, 197 frontend,
TypeScript y build de produccion, con aceptacion funcional del usuario.

## Corrección de clase por alta errónea

El selector de clase está disponible en edición para corregir una clase
seleccionada por error al dar de alta al integrante. Este flujo no define el
paso posterior de Becario a Investigador u otra categoría durante su trayectoria.
No se implementa un plazo automático: la finalidad aprobada es corregir el alta,
y la API determina si las dependencias permiten hacerlo.

`PersonalForm` confirma el cambio de clase, descarta cambios sin guardar y
precarga los campos comunes del registro guardado. Los formularios
`FormPTAAProfesional`, `FormBecario` y `FormInvestigador` solicitan los campos del
destino y conservan sus validaciones. El cambio se persiste al pulsar Actualizar,
mediante `services/reclasificacionService.ts`, con `clase_destino` y diferencias
reales. No se usa el endpoint de alta ni se crean duplicados inactivos.

El service tipa la clase y el callback de reclasificación. Los formularios
reutilizan sus hooks existentes y borradores por combinación origen/destino,
sin compartirlos con altas o con otro integrante de igual ID numérico. Durante
el guardado se bloquea el selector. El éxito limpia el borrador, invalida las
consultas relacionadas y navega al detalle del `rol`/`id` devuelto con
`successMessage`. Los errores de API permanecen visibles y conservan el formulario.

Los permisos siguen siendo ADMIN/GESTOR y requieren un integrante activo y UCT
válida. Becas, proyectos, autorías y antecedentes existentes, incluso históricos
o con baja lógica, pueden impedir la corrección. No deben eliminarse para forzar
el cambio. Las versiones anteriores de memoria conservan sus fotos; las nuevas
toman la clase corregida al cerrarse. El contrato histórico se documenta también
en el módulo Memorias.

`personalGuardarFeedback.test.ts` cubre guardado, navegación y errores;
`personalSnapshot.test.ts` cubre consulta histórica.

## Nombres de catálogos y opciones vigentes

Los formularios, detalles e historiales usan Tipo de Personal, Nivel de Formación,
Tipo de Dedicación, Categoría UTN y Programa de Incentivos, en correspondencia
con Gestionar Catálogos. Los selectores y las validaciones usan esos mismos
conceptos. Las claves API y los IDs de los campos permanecen iguales.

Tipo de Personal consume las opciones activas del servidor sin IDs ni listas
fijas en el formulario. La configuración depurada conserva Técnico,
Administrativo, De Apoyo y Profesional. Si una ficha existente referencia una
opción retirada, conserva su valor como no disponible e informa que debe elegir
uno vigente para guardar. No se reasigna automáticamente su categoría.

## Funciones compatibles con la clase Personal (ISS-43)

`GET /api/v1/tipo-personal/` informa `compatible_con_personal` para cada opción.
`tiposServices.ts` tipa esa metadata y `FormPTAAProfesional` excluye las opciones
marcadas como incompatibles tanto del selector como de la validación al guardar.
La decisión pertenece al backend; el formulario no replica nombres ni IDs de
clases reservadas. Se conservan las funciones de apoyo y las opciones propias
del catálogo, como Especialista de laboratorio.

El flujo mantiene `useTiposPersonal`, carga, error con reintento y estado vacío.
Una asignación heredada incompatible aparece como no disponible y requiere
seleccionar una función vigente. Un borrador con un ID incompatible no puede
guardarse. Al cambiar de clase, `PersonalForm` reinicia los campos exclusivos
y usa el formulario del destino; la reclasificación a Personal aplica el mismo
selector y las mismas validaciones que su alta y edición.

Los permisos ADMIN/GESTOR, el envío de diferencias y la navegación de éxito no
cambian. Los rechazos de API se asocian a `tipo_personal_id` y se muestran junto
al selector. `tests/personalCatalogForm.test.ts` verifica el formulario real,
el filtrado, las funciones personalizadas y el bloqueo de un ID incompatible.
Aceptación funcional del usuario: 05/11/2026.


## Recuperacion del contexto de consulta (ISS-50)

PersonalHome conserva texto, clase, estado, orden y pagina. La URL con tipo mantiene un ambito propio. El texto aplicado se inicializa con el recuperado para evitar que el debounce borre la pagina.

Los homes con estado local usan `shared/hooks/useHomeState.ts`; Busqueda conserva
su contrato de URL. La persistencia validada se limita a la pestana y al usuario,
sin guardar filas ni acciones pendientes. Se mantienen services, permisos,
validaciones y paginacion vigentes. Contrato y pruebas en `../shared/README.md`.
Aceptado funcionalmente por el usuario el 06/11/2026.
