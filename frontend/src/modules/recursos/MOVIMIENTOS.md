# Movimientos financieros: contrato frontend

## Vistas y rutas

`/movimientos` muestra el saldo disponible de la UCT activa y los totales consolidados en ARS, además del historial en tabla. Cada importe conserva el código de moneda original. La columna Movimiento contiene solo el número; Tipo y Fuente son columnas separadas. La tabla permite buscar por número, fuente o categoría, filtrar por estado, tipo, fuente, categoría y fecha, y muestra hasta 9 registros por página. El historial de cambios de cada fila se carga al expandirla y se pagina de a 3 eventos.

El panel «Saldo por fuente de financiamiento» presenta ingresos, egresos y saldo disponible de cada fuente con movimientos activos. Tiene un selector para ver todas las fuentes o una en particular y pagina de a 3 tarjetas para conservar visible el historial. El selector y su paginación son independientes de los filtros de la tabla. No crea fuentes nuevas.

`/movimientos/nuevo` permite el alta; `/movimientos/:id` muestra los datos, Auditoría e Historial de cambios; `/movimientos/:id/editar` permite editar un registro activo. Las altas vuelven al listado y las ediciones al detalle con `successMessage`.

## Formulario y reglas

El formulario pide tipo, moneda (`ARS` o `USD`), fecha, monto y fuente de financiamiento. Para USD consulta la cotización aplicable a la fecha, muestra fecha oficial, valor y equivalente ARS antes de guardar, y bloquea el alta si no hay una cotización anterior disponible. Si no hay observación en el día elegido, muestra la fecha de la última observación previa. Un egreso también requiere categoría y puede vincular opcionalmente un equipamiento activo de la misma UCT, solo si está en ARS. La lista de equipos disponibles excluye los vinculados a otro egreso e incluye el equipo propio durante la edición. Al seleccionar uno, el formulario toma su `monto_invertido` y propone la categoría `CAPITAL`, que el usuario puede cambiar. El monto queda de solo lectura mientras haya un equipo vinculado; para editarlo manualmente hay que desvincularlo. El importe del egreso se conserva como dato histórico si luego cambia el valor del equipo.

Número, tipo y moneda quedan fijos en edición. En USD también queda fija la fecha para preservar la cotización aplicada; cambiar el monto usa esa cotización histórica. Se envían solo diferencias reales y no se llama al backend si no hubo cambios. La validación local exige monto positivo, fecha válida, fuente y categoría cuando corresponde; los errores por campo provienen de `error.details.fields` y los fallos generales muestran un mensaje accionable. El detalle presenta monto original, equivalente ARS y datos de la cotización junto con Auditoría e Historial.

Antes de guardar un egreso, el formulario consulta `GET /recursos/movimientos/grupos/<id>/saldos-por-fuente` y contrasta el equivalente ARS con el saldo vigente de la fuente elegida. En edición reintegra el equivalente anterior únicamente si mantiene esa fuente. Si no alcanza, impide el envío y abre el diálogo modal nativo `Saldo Insuficiente`, con foco en `Aceptar` y el saldo de esa fuente visible. Si el backend rechaza una operación concurrente, vuelve a consultar y muestra el saldo actualizado. El backend conserva la autoridad final.

## Servicios, hooks y permisos

`services/erogacionesServices.ts` concentra las consultas y mutaciones HTTP y sus tipos TypeScript. `hooks/useErogaciones.ts` consulta el historial de la UCT, `hooks/useSaldosPorFuente.ts` consulta el panel, `hooks/useCategoriasErogacion.ts` carga las categorías y `hooks/useCotizacionMovimiento.ts` resuelve la cotización para la vista previa. `utils/movimientoHistory.ts` presenta importes, relaciones e historial; `utils/movimientoSaldo.ts` calcula equivalentes y compara centavos sin pérdida de precisión. El formulario consulta los equipos disponibles mediante el service dedicado y actualiza las consultas afectadas tras guardar.

`ADMIN`, `GESTOR` y `LECTURA` ven listado y detalle; solo los dos primeros pueden crear, editar o eliminar. La baja es lógica y requiere confirmación. La navegación desde Búsqueda y Memorias usa `/movimientos/:id`; la portada pública no presenta el breadcrumb `Portada`.

El historial y el saldo se filtran por la UCT activa. Los datos ficticios se regeneran bajo esa UCT para que los resultados de Búsqueda también aparezcan en Finanzas. Dashboard, Memorias, exportaciones y Búsqueda consolidan movimientos en ARS mediante el equivalente persistido. La cotización BCRA inicial es minorista vendedor B 9791 y permanece pendiente de confirmación administrativa.

Validación del 2026-10-02: 192 pruebas frontend, `typecheck` y build correctos. La revisión visual del flujo financiero fue aprobada por el usuario; la generación y revisión final del Excel de Memorias continúa en ajuste.
