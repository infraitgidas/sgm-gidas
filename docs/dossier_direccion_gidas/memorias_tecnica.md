# Documentacion Tecnica - Modulo Memorias

## Objetivo
El modulo `Memorias` es el expediente historico del sistema GIDAS.

Su responsabilidad es:
- definir el periodo institucional de una memoria
- congelar una foto historica consistente de las entidades del sistema
- permitir navegacion y consulta segura sobre esa foto
- servir como base futura para la exportacion Excel

`Memorias` no es un CRUD comun. Es un modulo de versionado, cierre y consulta historica.

## Conceptos del dominio

### Memoria
Representa la identidad persistente del expediente.

Campos principales:
- `id`
- `periodo_inicio`
- `periodo_fin`
- `version_actual_id`

### MemoriaVersion
Representa cada ciclo editable o historico de una memoria.

Campos principales:
- `id`
- `numero_version`
- `fecha_apertura`
- `fecha_cierre`
- `estado`
- `memoria_id`

Estados validos:
- `abierta`
- `en revision`
- `cerrada`

## Reglas estructurales del modulo

### Una memoria por anio
El sistema solo admite una memoria por anio calendario.

Regla:
- `periodo_inicio` y `periodo_fin` deben pertenecer al mismo anio
- no puede existir otra memoria no eliminada cuyo `periodo_fin.year` sea igual

### Una sola memoria activa a la vez
Solo puede existir una memoria activa en el sistema en un momento dado.

Se considera activa a una memoria cuya `version_actual.estado` no sea `cerrada`.

Esto implica:
- no se puede crear una nueva memoria si ya existe otra memoria abierta o en revision
- no se puede reabrir una memoria si ya existe otra memoria activa

### Versionado
Una memoria no se reescribe historicamente.

Reglas:
- al crearse, nace con una `MemoriaVersion` inicial en estado `abierta`
- cuando una version pasa a `cerrada`, se genera el snapshot historico
- una version cerrada no se edita
- si hace falta continuar el trabajo, se crea una nueva version de la misma memoria

## Reglas de transicion de estado

Transiciones permitidas:
- `abierta -> en revision`
- `abierta -> cerrada`
- `en revision -> abierta`
- `en revision -> cerrada`

Reglas adicionales:
- una version `cerrada` no cambia de estado
- para continuar trabajando debe ejecutarse `reabrir`
- `reabrir` crea una nueva version abierta y deja intacta la version cerrada anterior

## Roles y permisos

### Administrador
Puede:
- crear memorias
- cambiar estado de memoria
- reabrir memorias cerradas
- consultar detalles
- consultar elementos registrados
- eliminar memoria solo mediante la mecanica de seleccion del home, igual que el resto del sistema

### Gestor
Puede:
- consultar memorias
- consultar detalle de memoria
- consultar elementos registrados
- generar Excel una vez que el snapshot de la memoria exista

No puede:
- crear memorias
- cambiar estado
- reabrir

### Lector
Puede:
- consultar memorias
- consultar detalle de memoria
- consultar elementos registrados

No puede:
- crear
- editar
- cambiar estado
- reabrir
- generar Excel

## Regla central de pertenencia a memoria
La memoria no consume tablas vivas directamente. Consume snapshots.

Una entidad pertenece a una memoria si cumple la regla temporal correspondiente para esa entidad al momento de cerrar la version.

Hay dos familias de criterio temporal.

### 1. Entidades persistentes
Son elementos que pueden permanecer vigentes durante un tramo amplio del tiempo.

Regla:
- pertenecen si estuvieron activas en algun tramo del periodo de la memoria

Formula:
- `fecha_alta_o_inicio <= periodo_fin`
- y `fecha_baja_o_fin es null o >= periodo_inicio`

Entidades que usan este criterio:
- `Investigador`
- `Becario`
- `Personal`
- `Beca`
- `ProyectoInvestigacion`
- `ActividadDocencia`
- `TransferenciaSocioProductiva`
- `Equipamiento`

### 2. Entidades puntuales o eventuales
Son hechos puntuales del periodo y no deben arrastrarse a otras memorias solo por no tener baja.

Regla:
- pertenecen solo si su fecha propia cae dentro del periodo de la memoria

Formula:
- `periodo_inicio <= fecha_evento <= periodo_fin`

Entidades que usan este criterio:
- `DocumentacionBibliografica`
- `ParticipacionRelevante`
- `DistincionRecibida`
- `Erogacion`
- `RegistrosPropiedad`
- `ArticuloDivulgacion`
- `TrabajoReunionCientifica`
- `TrabajosRevistasReferato`
- `VisitaAcademica`

## Campos temporales por entidad

### Persistentes
- `Investigador`: `fecha_alta_grupo`
- `Becario`: `fecha_alta_grupo`
- `Personal`: `fecha_alta_grupo`
- `Beca`: `fecha_alta_grupo`
- `ProyectoInvestigacion`: `fecha_inicio` / `fecha_fin`
- `ActividadDocencia`: `fecha_inicio` / `fecha_fin`
- `TransferenciaSocioProductiva`: `fecha_inicio` / `fecha_fin`
- `Equipamiento`: `fecha_incorporacion` y eventual baja logica

### Puntuales
- `DocumentacionBibliografica`: `fecha`
- `ParticipacionRelevante`: `fecha`
- `DistincionRecibida`: `fecha`
- `Erogacion`: `fecha`
- `RegistrosPropiedad`: `fecha_registro`
- `ArticuloDivulgacion`: `fecha_publicacion`
- `TrabajoReunionCientifica`: `fecha_inicio`
- `TrabajosRevistasReferato`: `fecha`
- `VisitaAcademica`: `fecha`

## Snapshots

### Definicion
Un snapshot es una foto historica persistida al cerrar una `MemoriaVersion`.

No es una vista dinamica de datos vivos.

### Momento de generacion
Se genera cuando una version pasa a estado `cerrada`.

### Regla de inmutabilidad
Una vez generado:
- no se recalcula automaticamente
- no cambia si luego cambian las tablas vivas
- solo una nueva version cerrada genera una nueva foto historica

### Consecuencia operativa
Si se ajusta una entidad luego del cierre:
- la version cerrada anterior conserva su snapshot original
- para ver el nuevo estado en memoria se debe reabrir y volver a cerrar

## Regla de consulta

### Memorias cerradas
Deben leerse exclusivamente desde snapshots.

### Tablas vivas
No deben usarse para reconstruir una memoria cerrada.

Esto aplica especialmente a:
- la pantalla `Elementos registrados`
- los filtros contextuales desde memoria hacia los modulos
- la futura exportacion Excel

## Comportamiento frontend acordado

### Home de memorias
Debe:
- listar memorias con paginacion de `9`
- mostrar badge de estado de la version actual
- mostrar metricas resumidas

Filtros validos:
- `Activas`
- `Todas`
- `Cerradas`

No debe ofrecer:
- filtro por `Inactivas`

### Badges de estado
- `abierta`: amarillo
- `en revision`: naranja
- `cerrada`: violeta

### Titulo de tarjeta y detalle
Debe mostrarse como:
- `Memoria {anio de periodo_fin}`

Ejemplo:
- `Memoria 2027`

### Elementos registrados
La vista de elementos registrados:
- solo debe estar disponible cuando la version este `cerrada`
- debe mostrar resumen por seccion
- no debe insinuar datos vivos que no pertenezcan al snapshot
- debe priorizar metricas o navegacion controlada

### Navegacion desde memoria a modulos
Cuando el usuario entra a un modulo desde `Elementos registrados`:
- debe navegar al home del modulo correspondiente
- debe aplicarse un filtro contextual solo con IDs presentes en el snapshot
- debe mostrarse una banda indicando que el usuario esta viendo resultados de una memoria
- debe existir opcion `Volver a memoria`
- debe existir opcion `Quitar filtro`

### Restriccion de seguridad funcional
El usuario no debe consumir desde esa navegacion registros que no pertenezcan al snapshot de la memoria consultada.

## Excel
La regla funcional definida es:
- el Excel solo puede generarse una vez que la memoria tenga snapshot
- en la practica, eso significa una version `cerrada`

Permisos:
- `Administrador`: puede operar la memoria
- `Gestor`: puede generar Excel una vez generado el snapshot
- `Lector`: solo consulta

Nota:
- el ajuste final del backend de Excel puede cerrarse despues, pero la regla de negocio ya es parte del contrato del modulo

## Endpoints principales

### Memorias
- `GET /memorias`
- `GET /memorias/<id>`
- `POST /memorias`
- `PUT /memorias/<id>/estado`
- `PUT /memorias/<id>/reabrir`
- `DELETE /memorias/<id>`

### Snapshots por version
Patron general:
- `GET /memorias/<memoria_id>/versiones/<memoria_version_id>/<seccion>`

Secciones actuales:
- `investigadores`
- `becarios`
- `personal`
- `proyectos`
- `actividades-docencia`
- `participaciones-relevantes`
- `documentacion-bibliografica`
- `equipamiento`
- `erogaciones`
- `transferencias`
- `trabajos-reunion-cientifica`
- `trabajos-revistas`
- `distinciones`
- `registros-propiedad`
- `articulos-divulgacion`
- `visitas-academicas`

## Consideraciones de auditoria
El modulo de memorias convive con dos planos de trazabilidad:

### Auditoria de entidades vivas
- `created_at`
- `updated_at`
- `deleted_at`
- `created_by`
- `updated_by`
- `deleted_by`
- historial de cambios por campo

### Snapshot historico
Representa la foto de cierre.

No reemplaza la auditoria viva.

La auditoria explica como evoluciono una entidad.
El snapshot explica que quedo asentado en una memoria cerrada.

## Casos operativos importantes

### Caso 1
Se crea una documentacion con fecha anterior al inicio del periodo.

Resultado esperado:
- no debe entrar al snapshot

### Caso 2
Un investigador pertenece al grupo desde 2018 y sigue activo.

Resultado esperado:
- aparece en todas las memorias cuyos periodos se solapen con su vigencia

### Caso 3
Un personal es dado de baja antes del inicio del periodo de una memoria.

Resultado esperado:
- no aparece en esa memoria

### Caso 4
Una memoria ya cerrada contiene un snapshot incorrecto por una regla anterior.

Resultado esperado:
- la version cerrada no cambia sola
- debe reabrirse y cerrarse nuevamente para generar una nueva version con snapshot correcto

## Restricciones que deben mantenerse
- no reconstruir una memoria cerrada desde tablas vivas
- no permitir mas de una memoria por anio
- no permitir mas de una memoria activa simultanea
- no modificar una version cerrada
- no mostrar acciones de administracion a roles sin permiso
- no permitir generacion de Excel sin snapshot

## Archivos clave del backend
- `backend/modules/memorias/models/memorias.py`
- `backend/modules/memorias/services/memoria_service.py`
- `backend/modules/memorias/services/memoria_periodo_service.py`
- `backend/modules/memorias/controllers/memoria_controller.py`
- `backend/modules/memorias/routes/memorias_rutas.py`

## Archivos clave del frontend
- `frontend/src/services/memoriasService.ts`
- `frontend/src/pages/MemoriasHome.tsx`
- `frontend/src/pages/MemoriaForm.tsx`
- `frontend/src/pages/MemoriaDetalle.tsx`
- `frontend/src/pages/MemoriaVersionDetalle.tsx`
- `frontend/src/components/MemoriaFilterBanner.tsx`
- `frontend/src/lib/memoriaSectionFilter.ts`

## Criterio de mantenimiento
Toda modificacion futura del modulo debe validar estos cuatro planos:
- permisos por rol
- regla temporal de pertenencia
- consistencia del snapshot
- coherencia entre lo mostrado en memoria y lo revelado en modulos filtrados

## Estado actual esperado del modulo
Si el modulo esta correctamente implementado, debe cumplirse:
- el home refleja estado y version actual de cada memoria
- el detalle muestra la version actual real de esa memoria, no el ID global de la fila
- `Elementos registrados` solo funciona sobre versiones cerradas
- los modulos abiertos desde memoria muestran exclusivamente registros pertenecientes al snapshot
- los snapshots respetan el criterio temporal correcto de cada entidad
