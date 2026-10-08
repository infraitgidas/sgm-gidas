---
id: frontend-calidad-seguridad
title: Auditar y fortalecer calidad y seguridad del frontend
status: finished
area: frontend
module: frontend-security
priority: alta
risk_level: medio-alto
execution_order: 3
created_at: 2026-08-14
updated_at: 2026-08-20
closed_at: 2026-08-20
source: user-request
commit_sugerido: "refactor(frontend): fortalecer calidad y seguridad por modulo"
owner: codex
blocked_by: []
related_files:
  - frontend/src/lib/
  - frontend/src/components/
  - frontend/src/modules/
  - frontend/tests/
---

# Riesgo

El frontend debe revisarse de forma sistematica para detectar exposicion de datos,
manejo inseguro de HTML o credenciales, contratos HTTP inconsistentes, validaciones
insuficientes, errores no accionables y desviaciones de las convenciones del proyecto.
Una correccion mecanica puede alterar permisos, navegacion o contratos del backend.

# Objetivo

- Inventariar riesgos de seguridad y defectos de calidad con evidencia reproducible.
- Fortalecer primero infraestructura frontend compartida sin modificar zonas restringidas.
- Corregir cada modulo de manera independiente y documentar sus contratos.
- Preservar permisos, navegacion, mensajes y contratos vigentes.
- Validar con typecheck, build y pruebas focalizadas disponibles.

# Orden modular por riesgo y superficie

1. Infraestructura compartida: cliente HTTP, errores, sanitizacion y utilidades.
2. `memorias`: exportaciones, versiones y datos historicos.
3. `produccion`: mayor superficie de formularios y relaciones.
4. `personal`: datos personales y relaciones.
5. `recursos`: informacion economica.
6. `grupo` y `proyectos`: permisos, relaciones y cierres.
7. `transferencia`, `catalogos`, `dashboard` y `search`.

`auth`, layout global, router principal, hooks compartidos, estilos base y componentes
globales reutilizables solo se auditan; cualquier modificacion requiere autorizacion.

# Proceso por modulo

1. Inventariar servicios, tipos, hooks, vistas, permisos y validaciones.
2. Clasificar hallazgos por severidad antes de editar.
3. Corregir service, hooks, vistas y documentacion de forma consistente.
4. Agregar o ajustar pruebas focalizadas cuando exista soporte.
5. Ejecutar typecheck y build al cerrar cada modulo.
6. Ejecutar un commit atomico por modulo, sin push, segun autorizacion del usuario.
7. Continuar con el siguiente modulo.

# Criterios de aceptacion

- No se renderiza HTML no confiable sin sanitizacion explicita.
- No se exponen secretos ni credenciales persistentes evitables.
- Servicios HTTP mantienen contratos tipados y errores seguros y accionables.
- Formularios validan entradas y envian solo diferencias reales en edicion.
- Permisos de UI coinciden con las restricciones del backend sin considerarse barrera unica.
- Homes usan hasta 9 items e historiales 3 items por pagina.
- Typecheck y build completos finalizan correctamente.
- Cada modulo actualizado queda documentado y con mensaje de commit propuesto.

# Hallazgos del inventario transversal

- No se detectaron `dangerouslySetInnerHTML`, `eval`, `document.write`, secretos
  versionados ni almacenamiento persistente de tokens en el codigo funcional.
- El cliente HTTP trata todo `404` como `null`, incluso en mutaciones. Debe migrarse
  por servicio para no romper los detalles que esperan ausencia como resultado.
- Existian multiples interpretaciones manuales de `body.error` y `body.message` que
  no comprendian el contrato tipado `error.message` del backend.
- `transferencia/adoptantesServices.ts` conserva un mock en `localStorage`; solo se
  activa si no existe URL de API, pero debe aislarse explicitamente de produccion.
- `proyectos/proyectoInvestigacionServices.ts` sustituye cualquier error HTTP por
  datos mock, lo que puede ocultar fallos de permisos o conectividad.
- El bundle inicial es de 1.279 MB; el ajuste pertenece a la tarea independiente
  `frontend-code-splitting.md` y no se mezcla con esta auditoria.
- No habia runner de pruebas frontend configurado.

# Plan de solucion por modulo

- Infraestructura compartida: centralizar la extraccion segura de errores, agregar
  runner de pruebas y migrar gradualmente la semantica generica de `404`.
- `memorias`: consumir errores tipados, proteger errores de exportacion, respetar la
  navegacion del alta y documentar snapshots, permisos y contratos.
- `produccion`: eliminar `any` en respuestas y snapshots, normalizar errores en CRUD
  y desvinculaciones, comprobar diferencias reales, navegacion e historial.
- `personal`: reforzar tipos de datos personales y becas, errores accionables,
  actualizaciones diferenciales, permisos, auditoria e historial.
- `recursos`: tipar montos y catalogos financieros, normalizar errores, validar
  rangos y fechas, y revisar auditoria e historial.
- `grupo`: reemplazar `any`, reutilizar mensajes seguros en exportacion y CRUD,
  comprobar relaciones consolidadas, permisos e historial paginado.
- `proyectos`: eliminar el fallback mock ante errores HTTP, tipar respuestas,
  normalizar errores y comprobar relaciones, cierres, auditoria e historial.
- `transferencia`: aislar mocks y `localStorage` de produccion, eliminar `any`,
  normalizar errores y verificar relaciones de adoptantes e historial.
- `catalogos`: eliminar silencios de errores, normalizar contratos, revisar permisos
  de mutacion, sanitizacion textual e historial.
- `dashboard`: tipar filtros y respuestas, mostrar errores accionables y verificar
  que no se expongan detalles internos en visualizaciones.
- `search`: validar y codificar parametros, tipar resultados heterogeneos, limitar
  contenido resaltado a nodos React seguros y normalizar errores.
- `auth` y zonas restringidas: documentar hallazgos y solicitar permiso antes de
  modificar; no mezclar sus correcciones con los commits modulares.

# Estado de ejecucion

Completados y validados:

- Baseline: typecheck y build correctos antes de cambios.
- Infraestructura compartida: parser seguro y compatible de mensajes HTTP,
  4 pruebas unitarias con el runner nativo de Node, typecheck y build correctos.
- `memorias`: errores normalizados, alta redirige al home, README tecnico agregado;
  4 pruebas compartidas, typecheck y build correctos.
- `produccion` parcial:
  - articulos y distinciones tipados, errores seguros y altas al home (`0b5bce5`)
  - docencia y documentacion tipadas, contrato de IDs corregido, errores seguros y
    alta de documentacion al home (`7df95ae`)
  - tras cada subbloque: 4 pruebas, typecheck y build correctos
  - registros de propiedad tipados, errores seguros y alta al home (`203296c`)
  - trabajos en reuniones y revistas tipados, relaciones consolidadas y errores
    seguros (`19bd071`)
  - documentacion tecnica completa (`3d9a6b2`)
  - auditoria final sin `any`, `HttpError`, HTML peligroso, storage ni `fetch` directo
  - validacion integral: 4 pruebas, typecheck y build correctos
- `personal` parcial:
  - contratos de datos personales, becas, relaciones, detalle e historial tipados;
    eliminados los `any` del modulo (`6829330`)
  - validacion del bloque: 4 pruebas y typecheck correctos
  - formularios con errores seguros y visibles, services con retornos tipados,
    cargas/bajas accionables y README actualizado (`91d84d9`)
  - auditoria final sin `any`, `HttpError`, HTML peligroso, storage ni `fetch` directo
  - validacion integral: 4 pruebas, typecheck y build correctos
- `recursos`: contratos tipados, importes finitos, errores seguros, navegacion,
  actualizaciones diferenciales, historial y README completos (`e90dcf4`)
  - auditoria final sin `any`, `HttpError`, HTML peligroso, storage ni `fetch` directo
  - validacion integral: 4 pruebas, typecheck y build correctos
- `grupo`: UCT/exportacion, visitantes y planificaciones con contratos tipados,
  errores seguros, navegacion convencional y relaciones consolidadas
  (`2da6a6d`, `3d597d6`, `e1d0c16`)
  - auditoria final sin `any`, `HttpError`, HTML peligroso, storage ni `fetch` directo
  - homes de 9 elementos e historiales de 3 elementos confirmados
  - validacion integral: 4 pruebas, typecheck y build correctos
- `proyectos`: eliminado fallback mock, contratos y errores normalizados, relaciones
  de investigadores/becarios consolidadas y participaciones tipadas
  (`54fae31`, `ef3cc61`, `a1edae9`)
  - corregido el payload de desvinculacion para respetar la lista exigida por backend
  - auditoria final sin `any`, `HttpError`, HTML peligroso, storage ni `fetch` directo
  - validacion: 4 pruebas frontend, typecheck y 11 pruebas backend correctos
- `transferencia`: mock limitado a desarrollo mediante flag explicito, lectura de
  `localStorage` defensiva, contratos de listas e historial tipados y errores seguros
  - frontend alineado con el endpoint real de baja logica de adoptantes
  - alta vuelve al home, edicion al detalle y relaciones se consolidan al guardar
  - home de 9 elementos, detalle, auditoria e historial de 3 elementos confirmados
  - README tecnico agregado y auditoria sin `any`, `HttpError`, HTML peligroso ni
    `fetch` directo
  - validacion: 4 pruebas frontend, typecheck, build y 19 pruebas backend correctos
- `catalogos`: permisos de mutacion alineados con backend, errores seguros y visibles,
  actualizaciones diferenciales y dependencias obligatorias validadas
  - eliminado el `catch` vacio de opciones relacionadas y expuestos fallos parciales
    de historial sin ocultar los valores cargados
  - paneles paginados a 9 valores e historiales paginados a 3 eventos
  - README tecnico agregado y auditoria sin `any`, `HttpError`, HTML peligroso,
    storage ni `fetch` directo
  - validacion: 4 pruebas frontend, typecheck, build y 16 pruebas backend correctos
- `dashboard`: tooltip y respuestas tipados, filtros validados y errores de UCT,
  metricas y eliminacion visibles y accionables
  - corregido el estado que sugeria crear una UCT ante un fallo de servidor
  - permisos de edicion/eliminacion conservados y README tecnico agregado
  - auditoria sin `any`, `HttpError`, HTML peligroso, storage ni `fetch` directo
  - validacion: 4 pruebas frontend, typecheck, build y 2 pruebas backend correctos
- `search`: parametros URL normalizados, resultados y campos `extra` validados con
  guards, errores seguros y destinos externos rechazados
  - conservado resaltado mediante nodos React sin HTML inyectado, cache acotada,
    cancelacion de consultas y paginacion de 9 resultados
  - README ampliado y auditoria sin `any`, `HttpError`, HTML peligroso, storage ni
    `fetch` directo
  - validacion: 4 pruebas frontend, typecheck, build y 9 pruebas backend correctos
  - verificador de recuperacion real pendiente: launcher Python global invalido y
    Docker Compose bloqueado por ausencia de `MIGRATION_DATABASE_URL`
- Semantica compartida de `404`: `GET` conserva compatibilidad nullable y admite
  `allowNotFound` explicito; `POST`, `PUT` y `DELETE` ahora lanzan `HttpError`
  - detalles de memorias y transferencias migrados a semantica nullable explicita
  - 3 pruebas de politica agregadas; validacion total de 7 pruebas, typecheck y build

Archivos modificados:

- `frontend/package.json`
- `frontend/src/lib/httpError.ts`
- `frontend/tests/httpError.test.ts`
- `frontend/src/modules/memorias/README.md`
- `frontend/src/modules/memorias/services/memoriasService.ts`
- `frontend/src/modules/memorias/pages/MemoriasHome.tsx`
- `frontend/src/modules/memorias/pages/MemoriaForm.tsx`
- `frontend/src/modules/memorias/pages/MemoriaDetalle.tsx`

Proximo paso: ejecutar la auditoria transversal final y documentar hallazgos de
`auth` y zonas restringidas sin modificarlas antes de solicitar autorizacion.

Auditoria restringida completada el 2026-08-18 sin modificar codigo. Los hallazgos,
severidades, controles verificados, plan y commits propuestos quedaron registrados
en `tasks/pendient/frontend-auth-zonas-restringidas.md`. Su implementacion permanece
bloqueada hasta recibir autorizacion explicita.

El escaneo transversal posterior detecto tipos `any` residuales en snapshots de
versiones de memoria. Se reemplazaron por `MemoriaSnapshotEntry` y tipos de dominio,
con 7 pruebas frontend y typecheck correctos (`6f1d423`). Fuera de zonas restringidas
ya no quedan coincidencias funcionales de `any`, `HttpError` manual, HTML peligroso,
storage ni `fetch` directo fuera del cliente HTTP y el mock explicito de transferencia.

# Procesos restantes documentados

## 1. Completar `personal`

### Hallazgos pendientes

- `FormInvestigador`, `FormBecario` y `FormPTAAProfesional` esperan operaciones
  asincronas sin capturar errores; un rechazo puede quedar sin feedback visible.
- Los services de alta y actualizacion no declaran siempre el tipo de retorno.
- Falta comprobar que carga y mutaciones muestren el mensaje base accionable.
- El README debe reflejar el contrato tipado nuevo y la estrategia de errores.

### Archivos objetivo

- `frontend/src/modules/personal/pages/FormInvestigador.tsx`
- `frontend/src/modules/personal/pages/FormBecario.tsx`
- `frontend/src/modules/personal/pages/FormPTAAProfesional.tsx`
- `frontend/src/modules/personal/pages/PersonalForm.tsx`
- `frontend/src/modules/personal/pages/PersonalHome.tsx`
- `frontend/src/modules/personal/services/*.ts`
- `frontend/src/modules/personal/README.md`

### Secuencia

1. Tipar retornos de altas, actualizaciones y eliminaciones.
2. Incorporar estado de error y `getErrorMessage` en cada formulario.
3. Mantener comparacion diferencial y no ejecutar `PUT` sin cambios.
4. Confirmar que becas se consolidan en un unico payload al guardar.
5. Revisar permisos de alta, edicion y baja y consumo de historial.
6. Auditar ausencia de `any`, `HttpError`, storage, HTML peligroso y `fetch` directo.
7. Actualizar README y validar pruebas, typecheck y build.

### Cierre y commit

- Criterio: todos los errores son visibles, seguros y accionables; contratos tipados,
  navegacion e historial conservados.
- Commit: `refactor(personal): completar errores seguros y contratos frontend`.

## 2. Completar `recursos`

### Hallazgos a verificar

- Parsers manuales de errores en formularios y homes de equipamiento y erogaciones.
- Tipos de montos, fuentes de financiamiento, fechas y respuestas de historial.
- Rango y precision de importes; rechazo de valores no finitos o negativos.
- Navegacion de alta al home y edicion al detalle.

### Archivos objetivo

- `frontend/src/modules/recursos/services/`
- `frontend/src/modules/recursos/hooks/`
- `frontend/src/modules/recursos/pages/`
- `frontend/src/modules/recursos/README.md`

### Secuencia

1. Inventariar contratos de becas, equipamiento, erogaciones y tipos.
2. Eliminar `any` y tipar respuestas planas o envueltas en `{ data }`.
3. Migrar mensajes a `getErrorMessage` con fallbacks de guardado/eliminacion.
4. Validar montos, fechas, catalogos obligatorios y actualizaciones diferenciales.
5. Verificar permisos, auditoria, historial de 3 items y home de 9 items.
6. Documentar contratos y ejecutar pruebas, typecheck y build.

### Cierre y commit

- Commit: `refactor(recursos): fortalecer contratos y errores frontend`.

## 3. Completar `grupo`

### Hallazgos a verificar

- `UctForm` y exportacion conservan `any` y un extractor local de errores.
- Los flujos de directivos, planificaciones y visitas deben consolidar relaciones.
- Debe preservarse el historial de directivos y su paginacion de 3 items.

### Archivos objetivo

- `frontend/src/modules/grupo/services/uctServices.ts`
- `frontend/src/modules/grupo/services/visitantesServices.ts`
- `frontend/src/modules/grupo/pages/`
- `frontend/src/modules/grupo/components/DirectivosHistoryPopover.tsx`
- `frontend/src/modules/grupo/README.md`

### Secuencia

1. Reutilizar `getErrorMessage` en exportacion y mutaciones.
2. Tipar UCT, visitantes, directivos y opciones de catalogo.
3. Revisar diferencias reales y consolidacion de altas/bajas relacionales.
4. Confirmar permisos y guardas sin modificar el hook compartido restringido.
5. Validar exportacion, historial, navegacion, pruebas, typecheck y build.

### Cierre y commit

- Commit: `refactor(grupo): fortalecer contratos y errores frontend`.

## 4. Completar `proyectos`

### Hallazgos conocidos

- `proyectoInvestigacionServices.ts` devuelve datos mock ante cualquier error HTTP,
  ocultando fallos de permisos, sesion o conectividad.
- Formularios y homes interpretan manualmente errores del backend.
- Deben preservarse coordinador, investigadores, participaciones y cierre.

### Archivos objetivo

- `frontend/src/modules/proyectos/services/`
- `frontend/src/modules/proyectos/hooks/`
- `frontend/src/modules/proyectos/pages/`
- `frontend/src/modules/proyectos/README.md`

### Secuencia

1. Eliminar fallback mock en errores; permitir mock solo mediante modo explicito.
2. Tipar listas, detalles, payloads, historiales y relaciones.
3. Migrar errores a `getErrorMessage` y mantener validacion por campo.
4. Verificar actualizacion diferencial y consolidacion de relaciones.
5. Revisar permisos de edicion, baja y cierre; auditoria e historial.
6. Validar pruebas, typecheck, build y documentacion.

### Cierre y commit

- Commit: `refactor(proyectos): eliminar fallbacks inseguros y tipar contratos`.

## 5. Completar `transferencia`

### Hallazgos conocidos

- Adoptantes conserva datos mock en `localStorage` cuando no hay URL de API.
- Transferencias e historiales usan respuestas `any`.
- La eliminacion de adoptantes no existe en backend fuera del mock.

### Archivos objetivo

- `frontend/src/modules/transferencia/services/`
- `frontend/src/modules/transferencia/hooks/`
- `frontend/src/modules/transferencia/pages/`
- `frontend/src/modules/transferencia/README.md`

### Secuencia

1. Definir modo mock explicito, limitado a desarrollo/testing, nunca por ausencia
   accidental de configuracion en produccion.
2. Proteger lectura de JSON mock corrupto y evitar tratarlo como dato confiable.
3. Tipar transferencias, adoptantes, contratos, historiales y relaciones.
4. Normalizar errores y verificar altas/bajas consolidadas de adoptantes.
5. Revisar permisos, navegacion, auditoria, historial y paginacion.
6. Validar pruebas, typecheck, build y documentacion.

### Cierre y commit

- Commit: `refactor(transferencia): aislar mocks y tipar contratos frontend`.

## 6. Completar `catalogos`

### Hallazgos conocidos

- `CatalogosHome` contiene una promesa con `catch` vacio que silencia fallos.
- Existen interpretaciones locales de `HttpError` y una vista de gran superficie.
- Deben verificarse permisos de mutacion y dependencias entre catalogos.

### Archivos objetivo

- `frontend/src/modules/catalogos/services/`
- `frontend/src/modules/catalogos/hooks/`
- `frontend/src/modules/catalogos/pages/`
- `frontend/src/modules/catalogos/README.md`

### Secuencia

1. Clasificar catalogos y contratos de dependencia antes de editar la vista.
2. Eliminar silencios de errores y usar mensajes seguros/accionables.
3. Tipar definiciones, historiales y resultados de mutacion.
4. Recortar y validar nombres; impedir envios vacios o sin diferencias.
5. Revisar permisos, estados activos/inactivos e historial.
6. Validar pruebas, typecheck, build y documentacion.

### Cierre y commit

- Commit: `refactor(catalogos): normalizar contratos y errores frontend`.

## 7. Completar `dashboard`

### Hallazgos a verificar

- La carga fallida usa un texto no alineado con el mensaje accionable del proyecto.
- Filtros y respuestas agregadas deben permanecer tipados y codificados.
- Las visualizaciones no deben reflejar detalles internos ni datos inesperados.

### Secuencia

1. Revisar service, hook y pagina sin modificar componentes globales.
2. Tipar filtros, metadatos, series y respuestas vacias.
3. Normalizar feedback de carga y reintento.
4. Verificar permisos, estados vacios, accesibilidad y renders.
5. Documentar y validar pruebas, typecheck y build.

### Cierre y commit

- Commit: `refactor(dashboard): fortalecer filtros y errores frontend`.

## 8. Completar `search`

### Hallazgos a verificar

- Resultados heterogeneos y metadatos requieren validacion defensiva.
- Parametros deben codificarse y limitarse antes de llamar al backend.
- `highlight` usa nodos React seguros; debe conservarse sin HTML inyectado.

### Secuencia

1. Tipar variantes de resultados y extras mediante uniones/guards.
2. Validar longitud, pagina, filtros y `URLSearchParams`.
3. Normalizar errores y estados de reintento.
4. Confirmar paginacion de 9 resultados y resaltado sin HTML.
5. Documentar y validar pruebas, typecheck y build.

### Cierre y commit

- Commit: `refactor(search): validar resultados y errores frontend`.

## 9. Resolver semantica compartida de `404`

### Restriccion

`http()` devuelve `null` para todo `404`, incluso en `PUT` y `DELETE`. No debe
cambiarse globalmente hasta clasificar todos los consumidores, porque los detalles
actuales dependen de `null` para representar ausencia.

### Secuencia segura

1. Inventariar services con retorno nullable y endpoints de mutacion.
2. Agregar una opcion explicita como `allowNotFound` o un helper de lectura nullable.
3. Mantener `null` solo en consultas de detalle que lo documenten.
4. Hacer que mutaciones `404` lancen `HttpError` y muestren feedback.
5. Agregar pruebas para GET nullable, PUT/DELETE 404 y reintento 401.
6. Migrar modulo por modulo y retirar la compatibilidad generica al final.

### Cierre y commit

- Commit: `refactor(frontend-shared): distinguir ausencias de errores HTTP`.

## 10. Zonas restringidas y `auth`

### Hallazgos documentados, no autorizados para cambio

- `auth` conserva algunos `any` en formularios y parsers propios de errores.
- Layout, router, `AuthContext`, hooks compartidos, estilos base y componentes
  globales no se modifican dentro de esta tarea sin permiso adicional.

### Proceso

1. Emitir informe con archivo, linea, severidad e impacto.
2. Solicitar autorizacion explicita para cada zona restringida necesaria.
3. Si se autoriza, crear subtarea y commit independientes con pruebas de sesion,
   permisos y rutas protegidas.

## 11. Validacion y cierre integral

1. Ejecutar busqueda transversal de `any`, `HttpError` manual, HTML peligroso,
   storage, secretos, logs, `fetch` directo y silencios de errores.
2. Ejecutar `npm test`, `npm run typecheck` y `npm run build`.
3. Comparar bundle con baseline sin implementar code splitting en esta tarea.
4. Confirmar homes de 9 items, historiales de 3, navegacion y feedback.
5. Actualizar cada README y la evidencia de commits/pruebas en esta tarea.
6. Mover la tarea a `tasks/finished/` con metadata de cierre.
7. Commit final: `docs(tasks): cerrar auditoria de seguridad frontend`.
8. No hacer push y preguntar por tareas faltantes para `tasks/pendient/`.

# Commits esperados

```text
refactor(frontend-shared): fortalecer contratos y errores seguros
refactor(memorias): fortalecer calidad y seguridad frontend
refactor(produccion): fortalecer calidad y seguridad frontend
refactor(personal): fortalecer calidad y seguridad frontend
refactor(recursos): fortalecer calidad y seguridad frontend
refactor(grupo): fortalecer calidad y seguridad frontend
refactor(proyectos): fortalecer calidad y seguridad frontend
refactor(transferencia): fortalecer calidad y seguridad frontend
refactor(catalogos): fortalecer calidad y seguridad frontend
refactor(dashboard): fortalecer calidad y seguridad frontend
refactor(search): fortalecer calidad y seguridad frontend
docs(tasks): cerrar auditoria de calidad y seguridad frontend
```

## Mejoras introducidas

- Uniforma contratos, validaciones, permisos, historial y paginacion por modulo.
- Reduce deuda transversal y deja sucesoras explicitas para riesgos no cerrados.

# Cierre 2026-08-20

- Auditoria transversal final sin `any` funcional, `HttpError` manual, HTML
  peligroso ni `fetch` directo fuera del cliente HTTP.
- Los usos de storage restantes corresponden a la limpieza de la clave heredada de
  auth y al mock explicito de transferencia limitado a desarrollo.
- `npm test`: 9 pruebas correctas.
- `npm run typecheck`: correcto.
- `npm run build:production`: correcto; bundle inicial de 1.284,65 kB con la
  advertencia conocida cubierta por `tasks/pendient/frontend-code-splitting.md`.
- La auditoria e implementacion de auth y zonas restringidas quedaron documentadas
  en `tasks/pendient/frontend-auth-zonas-restringidas.md`; sus pruebas backend
  continuan condicionadas por el launcher Python invalido y la configuracion Docker.
- No se ejecutaron commits durante este cierre.

Mensaje de commit propuesto:

```text
docs(tasks): cerrar auditoria de calidad y seguridad frontend
```
