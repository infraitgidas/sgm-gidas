# Informes por período (ISS-85)

## Responsabilidad y acceso

El módulo registra informes manuales de `investigadores`, `pid` y `uct`. Cada
informe pertenece a una sola Memoria y a su UCT. Las rutas están bajo
`/api/v1/informes` y exigen el rol `GESTOR`, tanto para consultas como para
escrituras. `ADMIN` y `LECTURA` no tienen acceso. El servicio comprueba la UCT
de la sesión al consultar Memorias, informes y registros vinculables.

## Modelo y relaciones

`Informe` guarda `tipo`, `memoria_id`, `grupo_utn_id`, `titulo`,
`fecha_realizacion`, `resumen`, `actividades`, `resultados`, `observaciones`,
`uct_snapshot` y campos de auditoría. `InformeInvestigador` e `InformeProyecto`
guardan cada vínculo con su copia `snapshot` y auditoría propia. Las copias
incluyen `_version: 1`; editar el registro de origen no modifica los datos ya
guardados. Un informe puede vincular varios investigadores o proyectos y un
proyecto puede aparecer en informes de períodos distintos. UCT no admite
`vinculos_ids`. La baja de informes y vínculos es lógica.

La migración reversible `a85f1e2d3c4b` crea las tres tablas, restricciones e
índices. Las Memorias con informes activos no pueden cambiar de período ni
darse de baja. El período de un informe no puede cambiarse por `PUT`.

## Contrato HTTP

`{tipo}` admite `investigadores`, `pid` o `uct`:

| Método | Ruta | Resultado |
| --- | --- | --- |
| GET | `/{tipo}?page=1&per_page=9&memoria_id=...` | Lista resumida y `meta` de paginación; `memoria_id` es opcional. |
| GET | `/{tipo}/candidatos?memoria_id=...&search=...&page=1&per_page=9` | Investigadores o proyectos elegibles, con `id`, `name`, `activo` y `meta`. |
| POST | `/{tipo}` | Crea un informe; responde 201 con detalle. |
| GET | `/{tipo}/{id}` | Contenido, auditoría, período y copias de vínculos. |
| PUT | `/{tipo}/{id}` | Actualiza únicamente los campos enviados y responde con detalle. |
| DELETE | `/{tipo}/{id}` | Baja lógica; responde con mensaje. |
| GET | `/{tipo}/{id}/historial` | Cambios de campos y eventos de vínculo. |

El `POST` recibe `memoria_id`, `titulo`, `fecha_realizacion` en formato
`YYYY-MM-DD`, las cuatro secciones de texto y `vinculos_ids`. Investigadores y
PID requieren al menos un ID; UCT usa una lista vacía. `PUT` admite un
subconjunto no vacío de los campos editables, sin `memoria_id`. El listado
omite secciones largas y copias; el detalle devuelve `uct_snapshot` y
`investigadores` o `proyectos`, según el tipo. Las listas y los candidatos
admiten hasta nueve elementos por página.

## Validaciones, historial y estados

Título: 1 a 200 caracteres; cada sección: 1 a 20.000; fecha de realización:
válida, dentro del rango institucional y no futura. Los vínculos no pueden
repetirse y deben pertenecer a la UCT y al período de la Memoria. Los
investigadores se admiten si ingresaron al grupo hasta el fin del período;
los proyectos, si su intervalo se cruza con ese período. Los candidatos
históricos pueden aparecer inactivos para conservar la trazabilidad.

Los errores de validación usan 400 y, para campos, `error.details.fields`.
Un tipo o registro inexistente responde 404. Los conflictos de período,
baja o cierre responden 409. El historial registra diferencias reales y
vinculaciones o desvinculaciones posteriores al alta, con autor y fecha.

Registrar un informe PID no cierra el proyecto. El cierre requiere la acción
explícita sobre el proyecto y un informe PID activo que lo vincule desde una
Memoria activa cuyo período contiene la fecha elegida de cierre. La fecha debe
estar entre el inicio del proyecto y hoy. Un proyecto con fecha prevista vencida
permanece activo hasta esa acción. El estado `cerrado` se presenta solo para
proyectos dados de baja por cierre con informe válido; el listado calcula esta
condición en lote. El último informe que justifica un cierre no puede eliminarse
ni desvincularse del proyecto cerrado. Los informes de proyectos abiertos sí
pueden eliminarse o desvincularse según las reglas generales.

## Validación

`backend/tests/test_informes.py` cubre migración, copias históricas,
períodos, UCT, permisos, candidatos, historial, Memorias y cierre de PID.
`backend/tests/test_proyecto_coordinador.py` verifica el estado de proyectos
con fecha prevista vencida. La suite backend completa pasó 572 pruebas antes
de los últimos ajustes; las 48 pruebas dirigidas finales pasaron.
