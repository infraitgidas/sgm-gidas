# Transferencia frontend

## Filtros desplegables (ISS-47)

TransferenciasHome: estado.
Los filtros del listado utilizan `TableFilterSelect`, con nombre accesible y
selección mediante teclado. Todos/Todas elimina la restricción del criterio.
La adaptación del selector conserva valores, setters y opciones de consulta;
se mantienen services, permisos, nueve filas por página, contexto de Memoria
y persistencia de filtros de ISS-50. No se modifican campos de formularios.

Aceptado visual y funcionalmente el 06/11/2026. Validación integrada:
269 pruebas frontend, TypeScript y build de producción aprobados.
`tests/homeFilterSelect.test.ts` comprueba selección y limpieza en las cuatro
pantallas principales y ausencia de chips de filtrado en los homes.

## Transferencias con monto cero (ISS-46)

`TransferenciasForm` admite el monto explícito cero y distingue un campo vacío
de ese valor antes de convertirlo a número. Mantiene el rechazo de negativos
y valores no finitos. La moneda ARS/USD, la precarga de cero, los borradores,
services, hooks, permisos, relaciones y navegación conservan sus contratos.
Las ediciones envían solo diferencias y no realizan PUT si no hay cambios.
Listado y detalle ya muestran cero con el formato monetario vigente.

`tests/docenciaMontosOpcionales.test.ts` ejecuta el formulario real para cero,
positivos, negativos, vacío, conservación de moneda y edición sin cambios.
Aceptación funcional del usuario: 05/11/2026; 242 pruebas frontend, TypeScript
y build de producción aprobados.

## Validacion preventiva de formularios (ISS-33)

`TransferenciasForm` reutiliza sus reglas de denominacion, demandante,
descripcion, monto, moneda, contrato y fechas al escribir, al salir de los
controles nativos y al guardar. Cambiar el inicio revalida el fin.
`AdoptantesField` informa formato y duplicados durante la carga del nombre y
al perder foco. Preparar adoptantes no crea registros ni vinculos; el guardado
de la transferencia sigue consolidando las altas y bajas existentes.

La actualizacion de errores usa `src/lib/liveValidation.ts`, que revalida el
campo editado y las reglas cuyo resultado cambia por dependencia, preservando
los demas errores. No agrega hooks compartidos ni modifica componentes globales.
Las validaciones no disparan escrituras de dominio. Se conservan services,
contratos, permisos, borradores, navegacion y feedback de exito.
La etapa fue aceptada visual y funcionalmente por el usuario el 05/11/2026;
la regresion transversal esta en `tests/liveValidation.test.ts`.

## Moneda del monto

`TransferenciasForm` permite elegir ARS o USD, con ARS inicial, precarga en
edición y envío de diferencias reales. No convierte el importe ni solicita
cotización; se mantienen validación de monto no negativo, permisos y navegación.
Los errores de moneda se muestran junto al campo. Borradores anteriores sin
moneda recuperan ARS; ese valor predeterminado no crea borradores vacíos.

`transferenciasServices.ts` tipa y transmite `moneda`, usando ARS para respuestas
heredadas. `TransferenciasHome` presenta monto y código de moneda y envía
`filter_moneda` al listado SQL. Detalle utiliza el mismo formato. Los importes
del historial se presentan sin adjudicarles la moneda actual; los cambios de
moneda se muestran como eventos propios. Los permisos y las relaciones con
adoptantes se conservan. `tests/moneda.test.ts` cubre servicios y borradores.

## Historial de adoptantes (ISS-83)

`TransferenciasDetalle` conserva el historial de la transferencia para cambios
de campos y eventos de vinculacion. Ademas muestra un selector de adoptantes
actualmente vinculados y consulta el historial propio del seleccionado mediante
`GET /adoptantes/:id/historial`. La consulta usa `useAdoptanteHistorial` y la
tarjeta muestra tres eventos por pagina, con carga, vacio y reintento ante error.
No mezcla cambios de nombre del adoptante con eventos de relacion.

`adoptantesServices.ts` define el tipo `HistorialAdoptanteItem` y adapta el
arreglo del backend; `useAdoptantes.ts` encapsula la consulta y las mutaciones
del catalogo. Las mutaciones invalidan las consultas de adoptantes. El selector
de transferencias lista solo adoptantes activos. El formulario permite crear
uno nuevo al guardar la transferencia; editarlo o darlo de baja corresponde a
Gestion de Catalogos, sujeto a permisos y validaciones del backend.

## Error accesible en adoptantes (ISS-73)

El alta inline de adoptantes vincula el error de nombre al input con
`aria-describedby="adoptante-nombre-error"` solo mientras el mensaje existe.
El input conserva `aria-invalid` y el mensaje visible tiene `role="alert"`.
La validación y el guardado consolidado de la transferencia no cambian.

El listado consulta `/transferencias/?activos=...` con la barra final exigida
por la ruta GET del backend. Así el proxy de desarrollo no recibe un 308 hacia
el nombre interno `backend`, inaccesible desde el navegador.

El alta de adoptantes desde el formulario exige solo letras Unicode y espacios.
El nombre queda pendiente hasta guardar la transferencia. El formulario rechaza
denominación y demandante exclusivamente numéricos y conserva los datos para
corregirlos ante un error.

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

Los períodos de transferencias socio-productivas admiten fechas desde el
01/01/2010 y la fecha de fin no puede ser anterior a la fecha de inicio.

## Alcance

El modulo administra transferencias socio-productivas, sus adoptantes y los tipos
de contrato. Incluye home, alta, edicion, detalle, auditoria e historial de cambios.

## Vistas y navegacion

- `TransferenciasHome` usa la tabla compartida, con 9 registros por página,
  búsqueda, orden por denominación y filtros horizontales de estado, tipo de
  contrato, grupo y año. Cada fila abre el detalle; las acciones individuales
  respetan estado y permisos. La baja lógica requiere confirmación. El historial
  de fila se consulta al expandirla y muestra 3 eventos por página.
- `TransferenciasForm` valida los datos, consolida altas y bajas de adoptantes y en
  edición envía solo diferencias reales. El número de transferencia no se muestra
  ni se envía: lo asigna el backend. Un alta vuelve al home y una edición al
  detalle, siempre con `successMessage`.
- `TransferenciasDetalle` presenta datos, auditoria e historial. El componente de
  historial pagina 3 eventos y contempla cambios de campos y relaciones. Muestra
  `Volver` y permite `Editar` solo con permiso y si la transferencia está activa.

`AdoptantesField` es el componente local del formulario. Busca adoptantes
disponibles, permite añadir o quitar vínculos en la grilla y crear nombres nuevos
sin persistirlos de inmediato. Enter en «Nombre del adoptante» equivale a
«Añadir al formulario» y evita el envío anticipado de la transferencia. Los
botones «Quitar» usan el formato secundario pequeño de los formularios de
referencia. Las tablas de disponibles y seleccionados muestran hasta cinco
adoptantes por página, con navegación Anterior/Siguiente; la búsqueda reinicia
la página de disponibles y el conteo indica el filtro vigente. Las vinculaciones
pendientes se conservan al cambiar de página. `transferenciaHistory.ts` presenta nombres legibles y omite eventos
técnicos del historial.

## Services y contratos

- `transferenciasServices.ts` define los tipos TypeScript y adapta el contrato
  snake_case del backend. POST `/transferencias` y PUT `/transferencias/:id`
  reciben `adoptantes_ids` y `adoptantes_nuevos` para guardar catálogo y vínculos
  junto con la transferencia. Los endpoints separados POST y DELETE
  `/transferencias/:id/adoptantes` siguen disponibles para otros clientes, pero
  el formulario usa una sola petición de guardado.
- `adoptantesServices.ts` consume el CRUD del backend, incluida la baja logica con
  `DELETE /adoptantes/:id`.
- `tiposContratoService.ts` obtiene el catalogo desde `/tipo-contrato/`.
- `useTransferencias.ts` y `useAdoptantes.ts` encapsulan consultas y mutaciones;
  después del guardado se invalidan transferencia, historial y adoptantes.

Las respuestas de listas e historiales admiten tanto arreglos planos como envoltorios
`{ data }`, sin recurrir a `any`. Los errores se interpretan con el helper seguro
compartido y se muestran con mensajes accionables sin exponer detalles internos.

## Validaciones y relaciones

- Número de transferencia asignado automáticamente por el backend; no es un
  campo editable ni una validación de entrada del formulario.
- Denominacion y demandante con al menos 3 caracteres luego de recortar espacios.
- Descripcion con al menos 10 caracteres.
- Monto finito y mayor que cero.
- Fecha de inicio obligatoria y fecha final no anterior.
- Tipo de contrato y grupo UTN obligatorios.
- Las altas y bajas de adoptantes se calculan antes de guardar y no se persisten al
  seleccionar o quitar elementos del formulario.

## Permisos y seguridad

La UI respeta los permisos de creacion, edicion y eliminacion provistos por auth; el
backend sigue siendo la autoridad final y protege los endpoints por rol. Las bajas
son logicas y quedan auditadas. El detalle oculta la edicion de registros inactivos.

El flujo de Transferencias usa siempre el backend, también en desarrollo, para
mantener coherentes el catálogo de adoptantes, sus vínculos y el detalle.

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

El formulario de transferencias indica los datos obligatorios; la fecha de fin permanece opcional.

ISS-19: las validaciones del backend se muestran junto a los controles mediante `applyFieldErrors`; alta y edición usan fallbacks propios. Los errores sin campo visible conservan el aviso general y los cambios de adoptantes permanecen consolidados hasta guardar.

La sección de adoptantes muestra los errores estructurados de `adoptantes_ids`
junto a la selección. La validación local del nombre nuevo muestra el error junto
al control y conserva el valor para corregirlo. Los errores generales del servidor
mantienen un mensaje visible y accionable.

## Borradores de formularios (ISS-22)

En transferencias, los cambios no se guardan como borrador mientras se escribe.
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

En TransferenciasDetalle, las etiquetas de datos y los encabezados de tarjetas
usan peso seminegrita y color pizarra oscuro para distinguirse del contenido.
La disposición, los textos, las acciones y el contrato permanecen iguales.

## Paginacion del servidor (ISS-94)

`TransferenciasHome` consume `getTransferenciasPage` mediante TanStack
Query y la clave `["transferencias", "table", params]`. El service solicita
nueve filas, transmite busqueda, orden por denominacion y filtros de
estado, tipo, grupo y anio, y normaliza con el adaptador existente.
Las opciones de filtro y el total provienen de `meta`, no de las nueve
filas visibles. La cache de cada combinacion tiene `staleTime=60_000`.

Desde Memorias se envian sus IDs y `activos=all`; un conjunto vacio
conserva el resultado vacio. Cambiar filtros u orden reinicia la pagina;
cambiar de pagina no se revierte mientras llega la nueva metadata.
Se clonan las opciones antes de ordenarlas para no modificar la cache.

La consulta distingue carga inicial, actualizacion y error con reintento.
Se conservan permisos, acciones, confirmacion de baja, contexto de retorno,
feedback e historial de tres eventos. Las mutaciones existentes invalidan
el prefijo `transferencias`, incluyendo las consultas nuevas.
`getTransferencias` y `useTransferencias` conservan sus consumidores
de formularios y detalle. Las regresiones del contrato y cambios de pagina
estan en `tests/transferenciasTable.test.ts`.


## Recuperacion del contexto de consulta (ISS-50)

TransferenciasHome conserva texto, filtros de estado/tipo/grupo/anio/moneda, direccion y pagina. El contexto de Memoria permanece separado del listado general.

Los homes con estado local usan `shared/hooks/useHomeState.ts`; Busqueda conserva
su contrato de URL. La persistencia validada se limita a la pestana y al usuario,
sin guardar filas ni acciones pendientes. Se mantienen services, permisos,
validaciones y paginacion vigentes. Contrato y pruebas en `../shared/README.md`.
Aceptado funcionalmente por el usuario el 06/11/2026.
