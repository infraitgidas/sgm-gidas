# Recursos

## Becas (ISS-93)

La gestión de Becas está en Personal > Becas, fuera de Catálogos. `BecasHome`
usa la tabla común con búsqueda por nombre o descripción en el servidor, filtros
de estado y hasta nueve filas por página. Muestra nombre, descripción, fuente,
cantidad de becarios, fecha de alta y estado. Las acciones de alta, edición y
baja lógica aparecen para `ADMIN` y `GESTOR`; `LECTURA` conserva la consulta.

`BecasForm` crea o edita nombre, descripción, fecha de alta en el grupo y fuente
de financiamiento. Nombre y fecha de alta son obligatorios; la descripción
tiene un máximo de 2000 caracteres y la fuente es opcional. En edición envía
solo diferencias reales; el alta vuelve al listado y la edición al detalle con
`successMessage`. Los errores del servidor se muestran junto al campo cuando
hay datos de validación y con un aviso accionable en los demás casos.

`BecasDetalle` presenta los datos, becarios vinculados en tarjetas sin enlace,
Auditoría e Historial de cambios de a tres. Muestra los plazos que pertenecen
al vínculo becario-beca, sin editarlos desde la ficha de la beca. El service
`services/becasService.ts` tipa contratos y HTTP; `hooks/useBecasPage.ts` pagina
la tabla y `hooks/useBecas.ts` carga las opciones del formulario de Becarios.

En Inicio, `components/BecasVencimientoModal.tsx` consulta vencimientos solo
cuando el usuario tiene rol `GESTOR`. Muestra becario, beca, fecha final y días
restantes destacados. El modal es informativo y se descarta por sesión para
el día y conjunto de vencimientos observado; no modifica el plazo.

El contrato vigente de pantallas, rutas, services, hooks, permisos y validaciones
del historial financiero está en [MOVIMIENTOS.md](MOVIMIENTOS.md).

El formulario de equipamiento muestra el error junto a la denominación cuando
se ingresan solo números.

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

Equipamiento, erogaciones, becas y vinculaciones institucionales admiten fechas
desde el 01/01/2010. Se mantienen las reglas particulares que impiden fechas
futuras en incorporaciones y erogaciones.

## Funcionalidad

El modulo administra equipamiento e infraestructura y los movimientos de ingresos y
egresos. Cada entidad dispone de home, formulario, detalle, auditoria e historial.
Los homes muestran hasta 9 elementos y los historiales 3 items por pagina.

## Equipamientos: presentación del home (ISS-38)

`pages/EquipamientoHome.tsx` usa la tabla compartida con hasta 9 registros por
página. La barra reúne búsqueda por denominación o descripción, chips de estado,
año de incorporación y rango de monto; en anchos reducidos los filtros se
desplazan horizontalmente. Cada fila abre el detalle. Las acciones Ver, Editar y
Eliminar son individuales; Editar y Eliminar aparecen solo para registros activos
y roles autorizados. La baja lógica conserva confirmación y mensaje de resultado.

El historial se consulta al expandir una fila mediante
`services/equipamientoServices.ts` y se pagina de a 3 cambios. Presenta carga,
error con reintento y estado vacío. Omite acciones técnicas, inicializaciones y
valores equivalentes; las fechas y montos usan formatos legibles y no se muestran
objetos ni identificadores internos. `hooks/useEquipamiento.ts` expone carga
inicial, actualización y reintento para conservar las filas durante un refetch.

El detalle mantiene datos, Auditoría, Historial de cambios y las acciones
condicionadas por estado y permisos. El formulario conserva la validación local,
los errores por campo y el envío exclusivo de diferencias en edición. Esta
adaptación no cambia payloads, rutas ni reglas del backend.

## Servicios y contratos

Los services normalizan contratos planos y respuestas envueltas en `{ data }` sin
usar `any`. Equipamiento, erogaciones, payloads, catalogos e historiales mantienen
tipos explicitos. Las llamadas HTTP se concentran en services dedicados.

## Formularios y navegacion

- Las altas vuelven al home con `successMessage`.
- Las ediciones vuelven al detalle y envian solo diferencias reales.
- Equipamiento valida denominacion, descripcion, monto positivo finito y una fecha
  de incorporacion entre el `01/01/2010` y la fecha actual, ambos limites
  inclusive. El formulario informa el rango y lo aplica al selector de fecha; la
  funcion pura `utils/equipamientoValidation.ts` conserva la misma regla para el
  envio.
- Movimientos valida fecha, monto positivo y fuente obligatoria para ambos tipos.
  Los egresos requieren categoría y pueden seleccionar un equipamiento disponible;
  se propone su monto y la categoría Capital. Número y tipo no se editan; en
  edición se envían solo los campos modificados.

El home de Movimientos muestra el saldo global y el saldo neto por fuente, con
ingresos y egresos desglosados. El panel permite seleccionar una fuente y muestra
hasta tres tarjetas por página; el historial en tabla conserva nueve filas por página.
El formulario muestra un modal con el saldo de la fuente si el egreso lo supera.

## Seguridad, permisos y errores

Los errores se procesan con `getErrorMessage`, admitiendo el contrato tipado del
backend sin reflejar cuerpos desconocidos. Las operaciones fallidas muestran un
fallback accionable. Los permisos visuales complementan los controles del backend.

El modulo no usa `any`, HTML no confiable, secretos ni `fetch` directo.
El borrador de erogaciones se guarda en backend por usuario y registro, vence a los
siete días y nunca se persiste en el almacenamiento del navegador. Al volver con
cambios, el usuario puede guardarlo, descartarlo o seguir editando.
React renderiza los datos como texto y los payloads se construyen con campos
permitidos explicitamente.

## Validacion tecnica

El cierre del modulo requiere auditoria estatica focalizada, pruebas unitarias
compartidas, `npm run typecheck` y `npm run build`.

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

Equipamiento y movimientos muestran el indicador en cada campo que el formulario exige para guardar, incluida la fuente para todo movimiento y la categoría para egresos. El equipamiento relacionado es opcional.

## Errores de formularios (ISS-19, en curso)

El calendario compartido inserta ambas barras al escribir la fecha desde cero,
conserva los separadores al reemplazar dia, mes o anio y permite sobrescribir
digitos al ubicar el cursor en una fecha completa. Se mantienen los limites y
la validacion de fecha.

Equipamiento y movimientos no infieren el campo inválido a partir del texto del error. `applyFieldErrors` utiliza `error.details.fields`; los errores restantes se muestran como aviso general. Alta y edición usan fallbacks propios. Las claves HTTP de fecha, monto, tipo, fuente y categoría se asocian a controles visibles.

## Borradores de formularios (ISS-22)

En equipamiento y erogaciones, los cambios no se guardan como borrador mientras se escribe.
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

En EquipamientoDetalle y ErogacionesDetalle, las etiquetas de datos y los encabezados de tarjetas
usan peso seminegrita y color pizarra oscuro para distinguirse del contenido.
La disposición, los textos, las acciones y el contrato permanecen iguales.

## Carga de becas (ISS-94)

Becas conserva sus services, filtros por anio y estado, permisos, mensajes
e historial. El backend precarga fuentes, becarios y clasificaciones para
reducir consultas de listado y dashboard anual. No cambia el contrato
financiero ni la paginacion de nueve filas de Becas. Las pruebas de la
etapa y su aceptacion funcional quedaron registradas en el CHANGELOG.
