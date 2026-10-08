# Recursos

## Becas y vencimientos (ISS-93)

Las rutas de Becas se publican bajo `/api/v1/recursos/becas` mediante
`routes/becas_rutas.py`, `controllers/becas_controller.py`,
`services/becas_service.py` y `models/becas.py`. `Beca` guarda nombre,
descripción, fecha de alta, fuente opcional y auditoría. `Beca_Becario` guarda
el becario, inicio, fin y monto percibido de cada vínculo. Las bajas son
lógicas; detalle e historial siguen disponibles para una beca inactiva.

- `GET /`: lista becas. Con `page` y `per_page` devuelve `data` y `meta`; acepta
  `activos=true|false|all`, `orden=asc|desc` y `q` para buscar por nombre o
  descripción. El home solicita nueve filas por página.
- `GET /<id>`: detalle con becarios vinculados activos.
- `GET /<id>/historial`: cambios de campos y eventos relacionales.
- `POST /`: crea una beca. Requiere `nombre_beca` y `fecha_alta_grupo`; acepta
  `descripcion` (máximo 2000 caracteres) y `fuente_financiamiento_id` opcionales.
- `PUT /<id>`: acepta únicamente los campos enviados, registra diferencias en
  auditoría y valida nombre, descripción, fecha y fuente cuando corresponden.
- `DELETE /<id>`: baja lógica.
- `POST /<id>/vincular-becario`: exige `id_becario`, `fecha_inicio` y
  `fecha_fin`; acepta `monto_percibido` no negativo. La baja del vínculo usa
  `DELETE /<id>/becarios/<becario_id>`.
- `GET /proximas-a-vencer`: exclusivo para `GESTOR`. Devuelve vínculos activos
  cuyo fin es hoy o cae en los siguientes 29 días civiles, ordenados por fecha.
  Cada elemento contiene `vinculacion_id`, `becario_id`, `becario`, `beca_id`,
  `beca`, `fecha_fin` y `dias_restantes`. Excluye becas, becarios y vínculos
  con baja lógica y no ofrece una acción para extender el plazo.

La lectura y el historial permiten `ADMIN`, `GESTOR` y `LECTURA`; las
mutaciones permiten `ADMIN` y `GESTOR`. El service rechaza nombres duplicados
para la misma fuente, fechas inválidas, fin anterior al inicio, montos
negativos y relaciones inexistentes. Los controladores usan el contrato de
errores compartido. Las pruebas del módulo están en
`tests/test_beca_vencimientos.py`, `tests/test_beca_historial.py` y
`tests/test_auditoria_relaciones_services.py`.

## Becas activas por año (ISS-84)

`GET /api/v1/recursos/becas/activas?anio=YYYY` requiere un año valido y
devuelve las becas activas con al menos una vinculacion vigente durante ese
año. Excluye becas, becarios y vinculaciones con baja logica, respeta la UCT
del usuario y devuelve cada beca una sola vez. Sin `anio` o con un valor
invalido responde HTTP 400 mediante el contrato general de errores.

El contrato vigente de ingresos, egresos, saldo, auditoría, permisos y API está en
[MOVIMIENTOS.md](MOVIMIENTOS.md). El modelo y las rutas antiguas de erogaciones no
forman parte del contrato público actual.

La denominación del equipamiento debe contener una letra. Montos y fechas
mantienen sus validaciones propias.

## Contrato de fechas

Equipamiento, erogaciones, becas y sus relaciones se validan desde el
01/01/2010, conservando los límites futuros específicos de cada entidad.

## Funcionalidad

El modulo administra equipamiento, becas y movimientos financieros. Cada
entidad separa rutas, controladores, servicios y modelos, y aplica permisos por rol
en sus endpoints.

## Equipamiento

Los endpoints de equipamiento se publican bajo `/api/v1/recursos/equipamiento`:

- `GET /` y `GET /<id>`: consulta para `ADMIN`, `GESTOR` y `LECTURA`;
- `GET /<id>/historial`: historial de cambios para los mismos roles;
- `POST /`, `PUT /<id>` y `DELETE /<id>`: mutaciones para `ADMIN` y `GESTOR`.

El home de Equipamientos consulta el historial existente al expandir una fila;
el detalle también consume ese endpoint. La estandarización visual ISS-38 no
modificó rutas, payloads, permisos, validaciones ni persistencia del backend.

El payload de alta requiere `denominacion`, `descripcion_breve`,
`fecha_incorporacion`, `monto_invertido` y `grupo_utn_id`. La edicion acepta solo
los campos modificados.

`fecha_incorporacion` usa formato `YYYY-MM-DD` y debe estar comprendida entre
`2010-01-01` y la fecha actual, ambos limites inclusive. La regla se aplica en el
service tanto al crear como al editar; una fecha fuera del rango devuelve un error
de validacion y no se persiste. Los cambios reales se registran en la auditoria de
`equipamiento_grupo` y alimentan el historial consumido por el frontend.

La eliminacion es logica. Los snapshots de memoria conservan los datos del
equipamiento correspondientes al periodo versionado para mantener trazabilidad.

Un equipamiento activo puede vincularse con un solo egreso de su UCT. La
relación conserva el monto del egreso como importe histórico aunque luego se
modifique `monto_invertido`. Un equipo vinculado no puede trasladarse a otra
UCT; la baja lógica del movimiento conserva el vínculo para la trazabilidad.

## Errores

La edición de movimientos acepta diferencias de fecha, monto y relaciones. La
fuente es obligatoria para ingresos y egresos; el egreso requiere categoría y
puede vincular equipamiento. El backend comprueba el saldo global y el de la
fuente, además de las relaciones, antes de guardar. Registra cada cambio real
en la auditoría y mantiene inmutables los snapshots de
Memorias ya creados.

Los controladores delegan en el contrato uniforme de errores. Los datos ausentes,
formatos invalidos, montos no positivos, grupos inexistentes y fechas fuera del
rango se responden como errores de validacion sin exponer detalles internos.

ISS-19: equipamiento identifica `denominacion`, `descripcion_breve`, `monto_invertido` y `fecha_incorporacion` en `error.details.fields`. Movimientos identifica `tipo_movimiento`, `fecha`, `monto`, `fuente_financiamiento_id`, `categoria_erogacion_id` y `equipamiento_id` según corresponda. Los conflictos de saldo o de vínculo duplicado responden HTTP 409.

## Snapshots de memorias (ISS-16)

Equipamiento y movimientos se filtran por UCT. Equipamiento usa solapamiento entre incorporación, baja y período; movimientos usan su fecha puntual inclusiva. Una baja posterior no elimina un hecho histórico que correspondía al período.
# Paginacion SQL (ISS-89)

Becas activas, becarios de una beca, equipamientos disponibles, movimientos
financieros y categorias de erogacion cuentan y limitan en SQL las filas que
cumplen sus filtros. Se preservan ano, vigencia, disponibilidad, pertenencia
al grupo y UCT. Los historiales siguen ordenados y paginados de a tres; las
rutas sin `page`/`per_page` conservan su respuesta previa.

## Precarga de becas y distribuciones (ISS-94)

Los listados completos, paginados y activos por anio de Beca precargan
fuente, vinculaciones y los campos de Becario necesarios para serializar
ID, nombre y estado. El detalle de vinculaciones tambien precarga el
becario. El dashboard anual precarga formacion y grupo en la consulta de
vinculos para evitar lecturas por cada becario.

Los endpoints, parametros, importes, reglas de vigencia, permisos,
auditoria, bajas logicas y alcance UCT conservan sus contratos. No se
modifico la conversion monetaria ni el servicio de movimientos.
Se compararon listas activas de 2025/2026, lista completa y dashboard
anual contra las respuestas anteriores, conservando datos y orden.

Las pruebas existentes de becas, paginacion y aislamiento estan incluidas
en la suite backend completa de 648 casos validada para esta etapa.
