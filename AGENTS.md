# Guia Operativa del Proyecto

## Objetivo

Establecer reglas de trabajo consistentes para acelerar el desarrollo y reducir retrabajo entre frontend y backend.

## Tareas del agente

- Las tareas del agente viven en `tasks/` organizadas por estado:
  - `tasks/in-progress/`
  - `tasks/pendient/`
  - `tasks/finished/`
- `docs/agents-tasks/` queda reemplazada por `tasks/`.
- La convencion de nombres de tareas es `ISS-XX.md`, con un unico archivo por identificador.
- Los seguimientos y ajustes de una tarea se agregan dentro de su archivo, en orden temporal, con fecha, cambios, archivos, validaciones, incidencias y estado de aceptacion relevantes. No crear archivos adicionales con sufijos para el mismo issue.
- Al iniciar una sesion de trabajo, revisar primero `tasks/in-progress/` y luego `tasks/pendient/` antes de modificar codigo.
- No modificar codigo antes de leer la tarea activa y comprender su estado actual.
- Al pausar una tarea, dejarla en `tasks/in-progress/` y registrar archivos modificados, estado exacto, validaciones hechas y proximo paso.
- No cerrar ni mover una tarea a `tasks/finished/` mientras su validacion visual o manual siga pendiente de aceptacion por el usuario. Durante ese periodo debe permanecer en `tasks/in-progress/` con su estado y proximo paso actualizados.
- Las actualizaciones de documentacion tecnica y `CHANGELOG.md` se realizan unicamente despues de que el usuario termine y acepte la validacion visual o manual del modulo. Deben ser la ultima tarea del agente antes de ejecutar un commit solicitado expresamente por el usuario o, si no solicita ejecutarlo, antes de proponer el mensaje de commit final.
- Una vez completada la aceptacion y la documentacion final, mover la tarea a `tasks/finished/`, completar metadata de cierre y proponer el mensaje de commit. No ejecutar commits automaticamente.
- Al finalizar una tarea, preguntar si existen tareas faltantes para agregar a `tasks/pendient/`.

## Convenciones de navegacion

- En edicion: volver siempre al detalle con `successMessage`.
- En alta: volver siempre al home con `successMessage`.

## Paginacion

- Homes: maximo 9 elementos por pagina.
- Historial de cambios en detalle: 3 items por pagina.

## Pantallas de detalle

Toda pantalla de detalle debe incluir:

- tarjeta principal de datos
- tarjeta `Auditoria`
- tarjeta `Historial de cambios`
- boton `Volver`
- boton `Editar` solo si la entidad esta activa y el rol lo permite

Toda entidad con endpoint de historial debe consumirlo en frontend. Si una entidad requiere historial y no existe endpoint, implementarlo manteniendo la arquitectura del proyecto.

## Historial de cambios

El historial debe contemplar:

- cambios de campos
- eventos relacionales cuando correspondan

## Formularios

En edicion:

- enviar solo diferencias reales
- si no hay cambios, no llamar al backend
- si hay error, mostrar `body.error` o `body.message`
- si hay exito, mostrar `successMessage`

Relaciones:

- permitir altas y bajas en el mismo formulario
- consolidar cambios antes de guardar
- no persistir cada cambio individual inmediatamente
- contemplar desvinculacion cuando aplique

## Mensajes UI

- Mantener el estilo actual de mensajes de exito.
- Los errores del servidor deben mostrarse con tono claro y accionable.
- Mensaje base de carga: `Lo sentimos, no pudimos recuperar la informacion. Intente nuevamente.`
- Mensaje base de guardado: `Lo sentimos, no pudimos guardar los cambios. Verifique los datos e intente nuevamente.`
- Mensaje base de eliminacion: `Lo sentimos, no pudimos completar la operacion. Intente nuevamente.`

## Alcance cuando cambia backend

Cuando una entidad cambia en backend, actualizar todo el flujo consistente sin esperar pedido puntual:

- service
- home
- form
- detalle
- hooks/tipos/validaciones/documentacion cuando corresponda

El frontend debe respetar el contrato actual del backend. Si se detecta una incoherencia menor que bloquea un flujo, se puede corregir tambien backend sin autorizacion extra siempre que el cambio sea acotado y consistente con la arquitectura.

## Zonas restringidas

No modificar sin pedir permiso:

- layout global
- router principal
- auth
- hooks compartidos
- estilos base
- componentes reutilizables globales

## Validacion esperada

- las validaciones tecnicas automatizadas corresponden al agente
- la validacion visual y del comportamiento del modulo corresponde al usuario
- test backend para el modulo actualizado
- prueba completa al final del modulo

## Aceptacion, documentacion y cierre

- La validacion tecnica del agente no reemplaza la aceptacion visual y funcional
  del usuario.
- Mientras el usuario no confirme expresamente que el modulo y su comportamiento
  fueron aprobados, la tarea debe permanecer en `tasks/in-progress/`.
- Antes de esa aprobacion no se debe actualizar la documentacion tecnica del
  modulo, `CHANGELOG.md`, cerrar la tarea ni ejecutar el commit.
- Despues de la aprobacion, y cuando el usuario solicite finalizar el trabajo,
  actualizar como ultimo paso la documentacion tecnica y `CHANGELOG.md`, mover la
  tarea a `tasks/finished/` y completar sus datos de cierre.
- Ejecutar el commit unicamente cuando el usuario lo solicite expresamente y
  siempre despues de completar la documentacion y el cierre de la tarea.

## Commits

Por cada modulo actualizado se debe proponer un mensaje de commit, pero no ejecutar el commit automaticamente.

Si el usuario solicita expresamente ejecutar el commit, primero completar la validacion visual o manual, actualizar como ultimo paso la documentacion tecnica y `CHANGELOG.md`, cerrar la tarea y recien entonces ejecutar el commit solicitado.

Formato:

```text
tipo(scope opcional): descripcion breve
```

## Escalabilidad arquitectonica

Toda nueva funcionalidad debe contemplar:

- modularidad
- separacion de responsabilidades
- reutilizacion futura
- posibilidad de migracion parcial a microservicios
- versionado de datos
- trazabilidad historica
- desacoplamiento frontend/backend
- extensibilidad para nuevos modulos

Se debe mantener documentacion tecnica por modulo en `frontend` y `backend`, detallando funcionalidades, contratos, vistas, services, componentes, hooks, permisos, validaciones, endpoints, payloads, reglas de negocio, modelos, relaciones, estados y errores.

## Estandarizacion de modulos

Frontend:

- service dedicado
- tipos TypeScript
- hooks reutilizables
- validaciones
- manejo uniforme de errores

Backend:

- rutas
- controller
- service
- model
- historial
- permisos

## Seguridad obligatoria

Toda nueva funcionalidad debe contemplar:

- permisos por rol
- validacion backend
- validacion frontend
- auditoria
- soft delete cuando aplique
- proteccion de endpoints criticos
- mensajes seguros
- sanitizacion de inputs
- trazabilidad

## UX/UI

Toda implementacion debe respetar:

- heuristicas de Nielsen
- consistencia visual
- placeholders
- feedback visible
- prevencion de errores
- accesibilidad basica
- diseno responsive
- minimalismo institucional

## Infraestructura

Mantener compatibilidad con:

- Docker
- Docker Compose
- variables de entorno
- healthchecks
- CI/CD futuro
- proxy reverso
- balanceo
- cloud deployment

## Performance

Considerar en cada nueva funcionalidad:

- paginacion
- queries optimizadas
- carga diferida
- reutilizacion
- minimizacion de renders
- eficiencia de consultas

<!-- CODEGRAPH_START -->
## CodeGraph

In repositories indexed by CodeGraph (a `.codegraph/` directory exists at the repo root), reach for it BEFORE grep/find or reading files when you need to understand or locate code:

- **MCP tool** (when available): `codegraph_explore` answers most code questions in one call — the relevant symbols' verbatim source plus the call paths between them, including dynamic-dispatch hops grep can't follow. Name a file or symbol in the query to read its current line-numbered source. If it's listed but deferred, load it by name via tool search.
- **Shell** (always works): `codegraph explore "<symbol names or question>"` prints the same output.

If there is no `.codegraph/` directory, skip CodeGraph entirely — indexing is the user's decision.
<!-- CODEGRAPH_END -->
