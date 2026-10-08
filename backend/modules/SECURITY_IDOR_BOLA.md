# Matriz IDOR/BOLA del backend

Fecha de revision: 2026-08-21

> Esta matriz conserva el estado historico de RBAC de agosto de 2026. Las
> columnas que dicen `global` o `parcial` no describen el alcance vigente por
> UCT. Para las reglas actuales de pertenencia, filtros y snapshots, consultar
> [Aislamiento de datos por UCT](SECURITY_MULTITENANCY_UCT.md). La revision
> completa de esta matriz queda pendiente cuando se implemente el selector.

## Criterio

Esta matriz registra autorizacion efectiva en backend. Los botones o rutas del
frontend no se consideran controles de seguridad. Una fila se aprueba solo cuando
el rol, el alcance del recurso y las pruebas negativas estan implementados.

Respuestas esperadas:

- `401`: solicitud sin autenticacion valida;
- `403`: rol autenticado sin permiso para la operacion;
- `404`: recurso inexistente o no visible cuando se implemente ocultamiento por
  alcance;
- nunca se confia en rol, propietario o UCT enviados por el frontend.

## Personal

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/personal` | listar | ADMIN, GESTOR, LECTURA | no | global | RBAC probado |
| `/api/v1/personal` | crear | ADMIN, GESTOR | no | `grupo_utn_id` del payload se valida como relacion, no como alcance del actor | parcial |
| `/api/v1/personal/{rol}/{id}` | detalle | ADMIN, GESTOR, LECTURA | `rol`, `id` | global | parcial |
| `/api/v1/personal/{rol}/{id}/historial` | historial | ADMIN, GESTOR, LECTURA | `rol`, `id` | global | parcial |
| `/api/v1/personal/{rol}/{id}` | actualizar, eliminar | ADMIN, GESTOR | `rol`, `id` | global | parcial; LECTURA recibe 403 |
| `/api/v1/personal/all[/{rol}/{id}]` | lista y detalle completo | ADMIN, GESTOR, LECTURA | `rol`, `id` cuando aplica | global | parcial |
| `/api/v1/personal/investigadores[/{id}]` | CRUD y restaurar | lectura: todos; mutacion: ADMIN, GESTOR | `id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/personal/investigadores/{id}/historial` | historial | ADMIN, GESTOR, LECTURA | `id` | global | parcial |
| `/api/v1/personal/becarios[/{id}]` | CRUD | lectura: todos; mutacion: ADMIN, GESTOR | `id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/personal/becarios/{id}/historial` | historial | ADMIN, GESTOR, LECTURA | `id` | global | parcial |
| `/api/v1/personal/tipo-*` | CRUD | lectura: todos; mutacion: ADMIN, GESTOR | `id` | catalogo global | RBAC probado |
| `/api/v1/personal/tipo-*/{id}/historial` | historial | ADMIN, GESTOR, LECTURA | `id` | catalogo global | RBAC probado |

## Grupo

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/grupo/grupo-utn` | consultar | ADMIN, GESTOR, LECTURA | grupo activo implicito | instancia global unica | RBAC probado |
| `/api/v1/grupo/grupo-utn` | crear, actualizar, eliminar, restaurar | ADMIN, GESTOR | grupo activo implicito | instancia global unica | RBAC probado; LECTURA recibe 403 |
| `/api/v1/grupo/grupo-utn/exportar-excel` | exportar | ADMIN, GESTOR | grupo activo implicito | instancia global unica | LECTURA recibe 403 |
| `/api/v1/grupo/directivos` | listar | ADMIN, GESTOR, LECTURA | no | global | parcial |
| `/api/v1/grupo/directivos/{id}` | actualizar | ADMIN, GESTOR | `directivo_id` | global | parcial; LECTURA recibe 403 |
| `/api/v1/grupo/directivos/grupo/{grupo_id}[/actuales]` | consultar relacion | ADMIN, GESTOR, LECTURA | `grupo_id` | global | parcial |
| `/api/v1/grupo/directivos/asignar` | crear relacion | ADMIN, GESTOR | IDs del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/grupo/directivos/finalizar` | cerrar relacion | ADMIN, GESTOR | IDs del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/grupo/visitas-academicas[/{id}]` | CRUD | lectura: todos; mutacion: ADMIN, GESTOR | `id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/grupo/visitas-academicas/{id}/historial` | historial | ADMIN, GESTOR, LECTURA | `id` | global | parcial |
| `/api/v1/grupo/programas-incentivos[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `id` | catalogo global | RBAC probado |
| `/api/v1/grupo/planificaciones[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |

## Evidencia automatizada

`backend/tests/test_idor_bola_personal_grupo.py` enumera dinámicamente todas las
rutas `POST`, `PUT`, `PATCH` y `DELETE` bajo `/api/v1/personal`,
`/api/v1/grupo`, `/api/v1/recursos`, `/api/v1/produccion`, `/api/v1/proyectos`,
`/api/v1/transferencia`, `/api/v1/catalogos`, `/api/v1/memorias`,
`/api/v1/dashboards` y `/api/v1/search`. Cada una debe responder `403` para un token
con rol `LECTURA`. Tambien se enumeran los `GET` cuyo path contiene `exportar-`,
porque son lecturas privilegiadas. La enumeracion evita que una nueva operacion
quede fuera de la prueba por olvido.

## Recursos

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/recursos/becas[/{beca_id}]` | lista, detalle, dashboard, activas | ADMIN, GESTOR, LECTURA | `beca_id` cuando aplica | global | parcial |
| `/api/v1/recursos/becas/{beca_id}/historial` | historial | ADMIN, GESTOR, LECTURA | `beca_id` | global | parcial |
| `/api/v1/recursos/becas[/{beca_id}]` | crear, actualizar, eliminar | ADMIN, GESTOR | `beca_id` cuando aplica | beca y relaciones sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/recursos/becas/{beca_id}/becarios` | listar relacion | ADMIN, GESTOR, LECTURA | `beca_id` | global | parcial |
| `/api/v1/recursos/becas/{beca_id}/vincular-becario` | crear relacion | ADMIN, GESTOR | `beca_id` e ID del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/recursos/becas/{beca_id}/becarios/{becario_id}` | eliminar relacion | ADMIN, GESTOR | ambos IDs | global | parcial; LECTURA recibe 403 |
| `/api/v1/recursos/equipamiento[/{equipamiento_id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `equipamiento_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/recursos/erogaciones[/{erogacion_id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `erogacion_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/recursos/tipo-erogacion[/{tipo_id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `tipo_id` | catalogo global | RBAC probado |

## Produccion

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/produccion/actividades-docencia[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `actividad_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/articulos-divulgacion[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `articulo_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/distinciones[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `distincion_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/registros-propiedad[/{id}]` | CRUD, historial y restaurar | lectura: todos; mutacion: ADMIN, GESTOR | `registro_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/trabajos-reunion-cientifica[/{id}]` | CRUD, historial y restaurar | lectura: todos; mutacion: ADMIN, GESTOR | `trabajo_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/trabajos-reunion-cientifica/{id}/investigadores` | agregar o quitar relaciones | ADMIN, GESTOR | `trabajo_id` e IDs del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/trabajos-revistas[/{id}]` | CRUD, historial y restaurar | lectura: todos; mutacion: ADMIN, GESTOR | `trabajo_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/trabajos-revistas/{id}/investigadores` | agregar o quitar relaciones | ADMIN, GESTOR | `trabajo_id` e IDs del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/documentacion-bibliografica[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `doc_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/documentacion-bibliografica/{id}/autores[/{autor_id}]` | agregar o quitar relaciones | ADMIN, GESTOR | `doc_id`, `autor_id` | global | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/autores[/{id}]` | CRUD | lectura: todos; mutacion: ADMIN, GESTOR | `autor_id` | global | RBAC probado |
| `/api/v1/produccion/autores/{id}/libros[/{libro_id}]` | agregar o quitar relaciones | ADMIN, GESTOR | `autor_id`, `libro_id` | global | parcial; LECTURA recibe 403 |
| `/api/v1/produccion/{catalogos}[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | ID del catalogo | catalogo global | RBAC probado |

## Proyectos

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/proyectos[/{proyecto_id}]` | CRUD, historial, cerrar y reabrir | lectura: todos; mutacion: ADMIN, GESTOR | `proyecto_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/proyectos/{proyecto_id}/investigadores` | vincular o desvincular | ADMIN, GESTOR | proyecto e IDs del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/proyectos/{proyecto_id}/becarios` | vincular o desvincular | ADMIN, GESTOR | proyecto e IDs del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/proyectos/participaciones-relevantes[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `participacion_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/proyectos/tipos-proyecto[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `tipo_id` | catalogo global | RBAC probado |

## Transferencia

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/transferencia/transferencias[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `transferencia_id` | `grupo_utn_id` sin alcance del actor | parcial; LECTURA recibe 403 |
| `/api/v1/transferencia/transferencias/{id}/adoptantes` | agregar o quitar relaciones | ADMIN, GESTOR | transferencia e IDs del payload | global | parcial; LECTURA recibe 403 |
| `/api/v1/transferencia/adoptantes[/{id}]` | CRUD | lectura: todos; mutacion: ADMIN, GESTOR | `adoptante_id` | global | RBAC probado |
| `/api/v1/transferencia/tipo-contrato[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `tipo_contrato_id` | catalogo global | RBAC probado |

## Catalogos

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/catalogos/categoria-utn[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `id` | catalogo global | RBAC probado |
| `/api/v1/catalogos/fuente-financiamiento[/{id}]` | CRUD e historial | lectura: todos; mutacion: ADMIN, GESTOR | `id` | catalogo global | RBAC probado |

## Memorias

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/memorias[/{memoria_id}]` | CRUD, estado y reapertura | lectura: todos; mutacion: ADMIN, GESTOR | `memoria_id` | periodo global y datos multi-UCT | parcial; LECTURA recibe 403 |
| `/api/v1/memorias/{id}/versiones/{version_id}/{recurso}` | consultar snapshots | ADMIN, GESTOR, LECTURA | memoria y version | snapshot historico global | parcial |
| `/api/v1/memorias/{id}/versiones/{version_id}/exportar-excel` | exportar | ADMIN, GESTOR | memoria y version | snapshot historico global | parcial; LECTURA recibe 403 |

## Dashboard y search

| Recurso y ruta | Operacion | Roles | ID controlado | Alcance UCT/propietario | Estado |
| --- | --- | --- | --- | --- | --- |
| `/api/v1/dashboards/resumen` | resumen agregado | ADMIN, GESTOR, LECTURA | filtros de consulta | datos globales | parcial |
| `/api/v1/search` | busqueda global | ADMIN, GESTOR, LECTURA | filtros y resultados con IDs | datos globales | parcial |

Estos endpoints no mutan datos, pero pueden exponer informacion de multiples UCT.
Si se adopta alcance por UCT, sus queries y resultados tambien deben filtrarse en
backend y probarse con identidades pertenecientes a UCT diferentes.

## Riesgos y siguiente cierre

- No existe asociacion entre usuario autenticado y UCT autorizadas.
- Los IDs de otra UCT no pueden diferenciarse hoy porque ADMIN y GESTOR tienen
  alcance global por diseño efectivo.
- Decision del 2026-08-22: GESTOR y LECTURA quedan limitados a las UCT a las que
  pertenecen; ADMIN selecciona la UCT activa y puede cambiar entre UCT configuradas.
- La implementacion queda diferida hasta finalizar el resto de tareas y se detalla
  en `tasks/pendient/security-multitenancy-uct.md`.
- Se necesita modelo de pertenencia usuario-UCT, contexto validado, comprobacion
  central reutilizable y pruebas cruzadas con recursos de al menos dos UCT.
- Hasta esa decision, filas con `grupo_utn_id` o relaciones por `grupo_id` quedan
  `parcial`; no corresponde declarar aprobado el control IDOR/BOLA completo.

## Configuraciones manuales

Ninguna. El alcance IDOR/BOLA debe resolverse en codigo y datos, no mediante una
variable de entorno ni una regla del proxy.
