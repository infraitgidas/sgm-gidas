# Movimientos financieros: contrato backend

## Modelo y reglas

`MovimientoFinanciero` registra un único `INGRESO` o `EGRESO` por fila. La numeración positiva es única dentro de `grupo_utn_id` y la asigna el servicio bajo bloqueo del grupo. `fecha` es civil, `monto` es decimal positivo de hasta dos decimales y `moneda` es obligatoria (`ARS` o `USD`). El importe original conserva su moneda. `monto_equivalente_ars` es el valor contable que usan los saldos y agregados; en ARS coincide con `monto`.

Para USD, `TipoCambioService` selecciona la última cotización oficial cuya fecha no sea posterior a la del movimiento. Si no existe una anterior, rechaza el alta. El movimiento guarda `tipo_cambio_id`, `tipo_cambio_aplicado` y `monto_equivalente_ars`; el equivalente se calcula con `Decimal` y se redondea a centavos. Editar el monto recalcula el equivalente con la cotización histórica guardada. No se permite cambiar la fecha de un movimiento USD ni recalcular su cotización desde valores posteriores.

Todo movimiento requiere `fuente_financiamiento_id`. Un ingreso excluye categoría y equipamiento. Un egreso requiere `categoria_erogacion_id` y puede vincular un `equipamiento_id` activo de su misma UCT. Las categorías estructuradas son `CORRIENTE` y `CAPITAL`. Cada equipo puede estar asociado a un solo movimiento, incluso si ese movimiento se da de baja; la base lo garantiza con una restricción única. Al vincular un equipo se toma `monto_invertido` redondeado a dos decimales. Ese importe queda registrado en el egreso y no cambia al modificar el equipo; para editar manualmente el monto hay que desvincularlo. No se puede mover a otra UCT un equipo vinculado.

El tipo, grupo, número y moneda no son editables. El vínculo de equipamiento se limita a egresos ARS porque el valor del equipo está expresado en ARS. `AuditMixin` conserva autoría, fechas y baja lógica; `AuditoriaService` registra cambios de monto, equivalente ARS, fecha, fuente, categoría y vínculo de equipamiento. `MovimientoMemoriaVersion` guarda una foto inmutable del movimiento, su cotización, equivalente ARS, grupo, fuente, categoría y equipo al cerrar una versión de memoria. La exportación de Memorias utiliza el equivalente ARS, sin alterar las versiones históricas cerradas.

El saldo de una UCT y el de cada fuente se derivan de los equivalentes ARS de sus movimientos activos: ingresos menos egresos. No se almacenan como campos editables. Crear o aumentar un egreso se rechaza con `409 CONFLICT` si supera el saldo global o el de la fuente elegida; en edición se reintegra primero el equivalente anterior en su fuente original. Cambiar la fuente de un movimiento, reducir un ingreso o eliminarlo se rechaza si alguna fuente quedaría negativa. La baja de un egreso aumenta el saldo de su fuente. Dashboard, búsqueda y exportaciones también consolidan en ARS. Las escrituras bloquean la fila del grupo para serializar numeración, unicidad del vínculo de equipamiento y validación financiera.

## API

Prefijo público: `/api/v1/recursos/movimientos`. `ADMIN`, `GESTOR` y `LECTURA` pueden consultar; solo `ADMIN` y `GESTOR` pueden escribir.

| Método y ruta | Respuesta o propósito |
| --- | --- |
| `GET /?activos=true|false|all&grupo_utn_id=<id>` | Listado ordenado por fecha y número; estado activo por defecto. |
| `GET /<id>` | Movimiento, relaciones, estado y auditoría. |
| `GET /<id>/historial` | Cambios auditados. |
| `GET /categorias` | Categorías activas. |
| `GET /cotizacion?fecha=YYYY-MM-DD` | Cotización USD/ARS aplicable a la fecha; incluye fecha oficial, valor, serie y fuente. |
| `GET /grupos/<id>/resumen` | `moneda`, `saldo_disponible`, `total_ingresos`, `total_egresos`, `cantidad_movimientos`, con importes como cadenas decimales. |
| `GET /grupos/<id>/saldos-por-fuente` | Lista de `fuente_id`, `fuente_nombre`, `total_ingresos`, `total_egresos`, `saldo_disponible` y `cantidad_movimientos`; importes decimales en cadena, solo movimientos activos. |
| `GET /grupos/<id>/equipamientos-disponibles?movimiento_id=<id>` | Equipos activos de la UCT aún no vinculados; incluye el equipo propio si se edita el movimiento indicado. Devuelve `id`, `denominacion` y `monto_invertido` decimal. |
| `POST /` | Alta; asigna `numero_movimiento`. |
| `PUT /<id>` | Edición de diferencias permitidas. |
| `DELETE /<id>` | Baja lógica con control de saldo. |

Alta de ingreso USD: `{"grupo_utn_id":1,"tipo_movimiento":"INGRESO","moneda":"USD","fecha":"2026-09-30","monto":"100.00","fuente_financiamiento_id":1}`. Alta de egreso ARS: `{"grupo_utn_id":1,"tipo_movimiento":"EGRESO","moneda":"ARS","fecha":"2026-09-30","monto":"75.00","fuente_financiamiento_id":1,"categoria_erogacion_id":2,"equipamiento_id":8}`; `equipamiento_id` es opcional y, si se envía, el servidor toma el importe del equipo. La edición admite diferencias de `fecha`, `monto`, `fuente_financiamiento_id`, `categoria_erogacion_id` y `equipamiento_id`; este último acepta `null` para desvincular. Categoría y equipamiento solo aplican a egresos. Las respuestas exponen `numero_movimiento`, `tipo_movimiento`, `monto`, `moneda`, `tipo_cambio_aplicado`, `monto_equivalente_ars`, `tipo_cambio`, grupo, fuente, categoría, equipo, estado y auditoría. Errores de validación usan `400`, registros ausentes `404`, conflictos financieros o vínculos duplicados `409` y permisos insuficientes `403`; los campos corregibles se informan en `error.details.fields`.

## Integraciones y datos de prueba

Dashboard, búsqueda, snapshots y exportación de Memorias consumen el modelo nuevo. La exportación separa ingresos y egresos corrientes/de capital. Las rutas públicas del módulo anterior están desregistradas; sus modelos y tablas permanecen internamente como legado temporal. No se migraron registros históricos porque el usuario confirmó que los datos del entorno son ficticios. La migración `e3a7d9b2c4f1` creó el esquema y categorías; `f4b8c6d2e9a1` descarta los movimientos, snapshots y auditorías financieros ficticios anteriores para exigir fuente también en egresos e incorporar el vínculo único de equipo. `tools/seed_testing_data.py` los regenera bajo la UCT activa con fuente para cada movimiento. La aplicación y el migrador mantienen roles de base separados en Docker Compose; el DDL se ejecuta con el servicio `migrate`.

## Cotizaciones BCRA y despliegue

`TipoCambio` es una tabla independiente con observaciones USD/ARS por fecha y serie. La migración `d8e1f4a6b2c9` añade sus restricciones y los campos financieros y de snapshot; convierte los movimientos ARS existentes sin consultar BCRA. `clients/bcra_client.py` consulta la API de Estadísticas Monetarias v4 y verifica la identidad de la variable en catálogo y metodología antes de importar. La serie inicial es la minorista vendedor, Comunicación B 9791 (`idVariable=4`, `cdSerie=7927`); su elección institucional sigue sujeta a confirmación administrativa.

`TipoCambioService.sincronizar()` importa observaciones oficiales de una ventana retrospectiva de siete días por defecto. Es idempotente, no sobrescribe cotizaciones existentes ni crea fechas artificiales para fines de semana o feriados. El job se ejecuta con `python -m modules.recursos.jobs.sincronizar_tipos_cambio`; `scripts/run-bcra-sync.sh` y `scripts/bcra-sync.cron.example` documentan la programación externa. `backend/.env.example` y `.env.production.example` contienen URL, ID, serie, tokens de descripción/metodología, ventana y timeout configurables. Una caída de BCRA falla el job y conserva los datos ya almacenados; los movimientos ARS siguen operativos.

Las pruebas cubren montos, numeración, permisos, saldo por fuente, vínculo de equipo, baja, auditoría, snapshots, migración, conversión USD, precisión, fallback histórico, rechazo sin cotización y sincronización idempotente. El 2026-10-02 pasaron 36 pruebas focalizadas de BCRA y movimientos; la prueba de exportación Excel queda pendiente mientras se ajusta la plantilla de Memorias. El usuario aprobó el flujo financiero; la validación final del Excel y la instalación del cron en el host de despliegue son pasos pendientes.
