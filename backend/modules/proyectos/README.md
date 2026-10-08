# Modulo backend de proyectos

## Logros obtenidos para memorias (ISS-94)

POST `/api/v1/proyectos` y PUT `/api/v1/proyectos/{id}` admiten
`logros_obtenidos`, texto opcional de hasta 20000 caracteres. Se recortan espacios
exteriores y un texto vacío se guarda como null. Un tipo diferente de string/null
o un texto demasiado largo devuelve `400 VALIDATION_ERROR` con
`error.details.fields.logros_obtenidos`. La respuesta serializa el campo y el
historial registra sus cambios como el resto de los atributos del proyecto.
Los permisos ADMIN/GESTOR y las restricciones de estado del guardado no cambian.

La migración aditiva reversible `a7c9e2f4b6d8`, posterior a `d8e1f4a6b2c9`, añade
columnas nullable al PID y a `proyecto_investigacion_memoria_version`; no rellena
versiones anteriores desde datos vivos. Al cerrar la memoria se copia el texto y
el Excel lo consume desde el snapshot. Una edición posterior no altera el
documento cerrado. Los resultados de informes PID ya congelados se mantienen
como compatibilidad para memorias anteriores.

Nombre del proyecto y nombre del evento requieren alguna letra. Código, fechas,
IDs y montos conservan reglas propias. El error indica `details.fields`.

Las fechas inválidas del alta y la edición de proyectos responden con `error.details.fields` para `fecha_inicio` o `fecha_fin`. Una fecha fuera del rango institucional mantiene el código de validación y muestra la indicación junto al control correspondiente.

## Errores accionables (ISS-09)

Las selecciones inexistentes de tipo de proyecto, fuente de financiamiento,
grupo e investigador se informan mediante `VALIDATION_ERROR` (400) y
`error.details.fields`, indicando la selección que debe corregirse.
El código de proyecto conserva su regla vigente: texto alfanumérico de hasta
50 caracteres; ISS-09 no modifica esa regla. Los errores inesperados incluyen
`details.request_id` correlacionable con los logs y un mensaje seguro.

## Contrato de fechas

Los proyectos y sus relaciones se validan desde el 01/01/2010. Los services
mantienen el orden inicio-fin y la prohibición de cierres futuros.

## Duracion inicial y prorrogas (ISS-77)

El alta exige `fecha_inicio` y `fecha_fin`. El intervalo inicial inclusivo debe
abarcar entre 12 y 36 meses: el limite es el dia anterior al aniversario de 12
o 36 meses. Si el aniversario no existe en el mes destino, se utiliza su ultimo
dia (29/02/2024 a 28/02/2025). La misma regla se aplica cuando PUT modifica
cualquiera de las fechas. Un PUT que solo cambia `fecha_fin` es una edicion, no
un cierre. La falta de fecha final o una duracion fuera de rango devuelve
`400 VALIDATION_ERROR` con `error.details.fields.fecha_fin`.

`POST /api/v1/proyectos/{id}/prorroga` requiere ADMIN o GESTOR y el body
`{"motivo":"justificacion de 10 a 2000 caracteres"}`. Registra una sola
prorroga de exactamente 12 meses inclusivos a partir del dia siguiente al fin
original. Se permite despues del vencimiento si el proyecto no tiene baja
manual. Un motivo invalido devuelve `400 VALIDATION_ERROR` con
`error.details.fields.motivo`; una segunda prorroga devuelve `409 CONFLICT`.
Las fechas no pueden editarse una vez prorrogado.

El modelo conserva `fecha_fin_original`, `fecha_fin_prorrogada`,
`prorroga_motivo`, `prorroga_by` y `prorroga_at`. `fecha_fin` sigue siendo la
fecha vigente usada por estado, listados, busqueda y snapshots posteriores de
Memorias. Hasta el cierre representa el fin previsto; un cierre manual la
sustituye por la fecha real. La respuesta agrega `prorroga_by_nombre` y expone
ambas fechas planificadas. Auditoria registra un evento `prorroga` con el fin
anterior, el nuevo, el motivo, autor y fecha.

El cierre manual con fecha usa `POST /api/v1/proyectos/{id}/cerrar` y
`{"fecha_fin":"YYYY-MM-DD"}`; exige una fecha entre el inicio y hoy, aplica
baja logica y conserva original y prorroga. DELETE conserva el cierre con fecha
de hoy. La reapertura de un proyecto prorrogado restaura el fin prorrogado si
aun esta vigente; rechaza una prorroga ya vencida. Las rutas de escritura
requieren ADMIN o GESTOR; LECTURA solo puede consultar datos e historial.

La migracion `e77a1b2c3d4e` agrega las columnas y copia `fecha_fin` de
proyectos existentes a `fecha_fin_original` sin corregir duraciones historicas.
Esos registros se conservan y solo deben cumplir el nuevo rango al cambiar sus
fechas. Los snapshots ya guardados de Memorias permanecen intactos; los
posteriores capturan la fecha vigente. Las participaciones continuan usando el
fin vigente del proyecto para sus reglas de cierre.

## Cierre con informe por período (ISS-85)

La fecha `fecha_fin` de un proyecto activo indica su fin vigente o previsto,
incluso cuando ya pasó. El vencimiento y el registro de un informe PID no
cambian el estado del proyecto. `POST /api/v1/proyectos/{id}/cerrar` y la ruta
DELETE exigen un informe PID activo que incluya el proyecto y pertenezca a una
Memoria activa cuyo período contenga la fecha efectiva de cierre. Sin él,
responden `409 CONFLICT`. El cierre explícito registra la baja lógica; el
detalle y los listados solo presentan `cerrado` cuando hay baja, fecha de
cierre válida e informe que la justifica. Los filtros de activos usan el
estado persistido y los listados verifican informes en una consulta por lote.
La reapertura conserva el contrato existente. El último informe requerido
por un proyecto cerrado no puede darse de baja ni perder ese vínculo.

Pruebas: `tests/test_proyecto_prorroga.py`,
`tests/test_proyecto_coordinador.py` y
`tests/test_proyecto_codigo_alfanumerico.py`; `tests/test_informes.py` cubre
el requisito de informe y el cierre explícito.

## Responsabilidad

Gestiona proyectos de investigacion, sus tipos, participaciones relevantes y
relaciones con investigadores y becarios.

## Coordinador y guardado atómico (ISS-10)

`ProyectoGuardadoService` coordina los services del agregado sin commits
intermedios. POST `/api/v1/proyectos` y PUT `/api/v1/proyectos/{id}` mantienen
sus rutas y permisos ADMIN/GESTOR. Admiten las siguientes claves opcionales
además de los campos existentes:

- `investigadores_ids`: lista de IDs de investigadores, positivos, enteros y sin duplicados.
- `becarios_ids`: lista equivalente de becarios.
- `coordinador_id`: ID de un investigador de la lista final, o null si no hay investigadores.

Una clave omitida conserva su estado; una lista vacía desvincula sus integrantes.
Si se quita al coordinador, debe enviarse su reemplazo o null cuando la lista
queda vacía. Ejemplo de reemplazo sin alterar participaciones:
`{"coordinador_id": 2}`. Con investigadores seleccionados se exige exactamente
un coordinador; un proyecto sin investigadores puede no tener coordinador.

Las nuevas vinculaciones y promociones a coordinador requieren que el registro
exista en la tabla de su subtipo, esté activo y no tenga baja lógica. Se rechazan
bool, IDs inexistentes/inactivos y coordinadores externos al proyecto mediante
400 `VALIDATION_ERROR` con `error.details.fields`. Un coordinador inactivo ya
asignado puede conservarse, ser reemplazado o desvincularse sin borrar datos
históricos. La consulta de proyectos devuelve `activo` en sus investigadores
para que el detalle pueda indicar esta situación. Los proyectos que ya estaban
cerrados al iniciar una edición no admiten nuevas asignaciones. El alta permite
registrar un proyecto histórico con fecha de fin pasada o de hoy y guardar
sus integrantes y coordinador en la misma transacción; las participaciones
iniciales quedan con la fecha de fin del proyecto. Una fecha de fin futura
también se admite en alta y conserva el proyecto abierto; las participaciones
nuevas quedan sin cierre efectivo. Se mantiene la validación inicio-fin.

El cambio de rol modifica `es_coordinador` en la participación existente;
conserva ID y fechas. Las bajas usan soft delete. La composición inicial de
investigadores, coordinador y becarios forma parte del alta y no genera entradas
de historial. Las vinculaciones y desvinculaciones posteriores registran el ID y
el nombre de la persona para presentar un evento legible sin exponer el payload
interno. También se registran las diferencias posteriores de `coordinador_id` y
el actor de auditoría, dentro de la misma transacción que los campos. Cualquier
fallo anterior al commit revierte proyecto, relaciones e historial. PUT bloquea
solo la fila de `proyecto_investigacion` mediante `FOR UPDATE OF`, evitando que
PostgreSQL intente bloquear las relaciones opcionales cargadas con `LEFT JOIN`.
Las rutas relacionales existentes reutilizan ese bloqueo para serializar cambios
del agregado. No se modifican snapshots ni versiones de memorias. No se requiere
migración para el contrato agregado.

Pruebas de API y persistencia SQLite: `tests/test_proyecto_coordinador.py`.
El bloqueo concurrente PostgreSQL requiere comprobación en el entorno Docker;
SQLite no valida la semántica de `FOR UPDATE`.

## Contrato de errores

Los services distinguen validaciones (`VALIDATION_ERROR`), recursos inexistentes
(`NOT_FOUND`) y conflictos de estado o duplicidad (`CONFLICT`). Los controladores
serializan solo excepciones de dominio conocidas. Las fallas inesperadas se
registran de forma sanitizada y responden `INTERNAL_ERROR` con `request_id`.

## Código de proyecto

`codigo_proyecto` es una cadena alfanumérica obligatoria de hasta 50 caracteres.
El alta y la edición eliminan espacios exteriores, conservan mayúsculas y
minúsculas y aceptan únicamente el patrón `[A-Za-z0-9]+`.

El mismo tipo se conserva en los snapshots de proyectos y distinciones asociados
a versiones de memorias. La migración `c6e8a1f4b2d9` convierte las columnas
numéricas anteriores a `VARCHAR(50)` y preserva sus valores como texto.

Los errores de formato se devuelven como `VALIDATION_ERROR` con el mensaje del
campo en `error.details.fields.codigo_proyecto`.

## Permisos y trazabilidad

Las rutas mantienen los permisos definidos en el modulo. Altas, cambios,
relaciones, cierres y reaperturas conservan auditoria e historial.

## Pruebas relacionadas

- `tests/test_proyecto_domain_errors.py`
- `tests/test_proyecto_codigo_alfanumerico.py`
- `tests/test_proyecto_memoria_historial.py`

## Snapshots de memorias (ISS-16)

Un proyecto entra cuando pertenece a la UCT y su intervalo desde `fecha_inicio` hasta el primero entre `fecha_fin` y baja lógica solapa el período. Los terminados antes se excluyen. Distinciones y participaciones heredan la UCT del proyecto o participante y usan su fecha puntual inclusiva.

## Participaciones relevantes (ISS-19, ISS-35)

El service de participaciones devuelve `error.details.fields` para participante,
nombre_evento, forma_participacion y fecha. La escritura usa
`participante: { rol: "investigador" | "becario", id }`; la lectura agrega nombre
y categoria y conserva temporalmente los campos heredados para compatibilidad.
La base exige exactamente un investigador o becario por registro mediante una
restriccion `CHECK` y claves foraneas para ambos roles.

Una persona inactiva, eliminada o inexistente pide elegir otra. El duplicado se
evalua por identidad compuesta `(rol, id)`, evento, forma y fecha, y responde
`CONFLICT` con un mensaje publico y accionable. Los filtros aceptan
`participante_rol` y `participante_id` juntos, ademas del filtro heredado por
investigador. Alta, edicion y baja conservan transacciones, permisos, auditoria y
soft delete.

Los snapshots de Memorias preservan rol, ID y nombre del participante. La
seleccion por periodo consulta tanto la relacion con investigadores como con
becarios y mantiene la exportacion XLSX y la busqueda global con nombres legibles
de ambos tipos de persona.

La revision `c35e8a1b7d42` agrega las columnas de becario, flexibiliza las columnas
anteriores de investigador, incorpora claves foraneas y restricciones de
integridad, y mantiene los registros existentes asociados a investigadores.
# Paginacion SQL (ISS-89)

Participaciones relevantes y tipos de proyecto aplican conteo y
`LIMIT/OFFSET` en SQL con los filtros y el orden vigentes. El service
serializa solo la pagina. Sin `page` ni `per_page` sigue el array previo;
con alguno se mantienen `data`, `meta`, `error`, permisos y alcance UCT.

## Carga del listado PID (ISS-94)

El listado precarga distinciones y reduce las columnas y relaciones de
participantes a las necesarias para serializar sus nombres, IDs y estado.
Evita que la precarga de investigadores/becarios active publicaciones o
historiales ajenos al listado. Se conserva la respuesta exacta verificada
contra el escenario anterior, junto con paginacion, filtros, permisos,
auditoria, reglas de duracion y logros obtenidos.

La medicion local paso de 21 a 9 consultas. Las pruebas existentes del
modulo y del flujo de Memorias se incluyen en los 648 casos backend
validados para esta etapa.
