# Aislamiento de UCT en el frontend

## Comportamiento actual

La sesion de ADMIN, GESTOR o LECTURA muestra los datos de la unica UCT activa
asignada por el backend. El frontend no selecciona una UCT ni envia un header
de grupo. `AuthContext` limpia la cache de React Query al iniciar sesion,
cerrarla o perderla, para que las vistas de otro usuario no reutilicen datos
de la sesion anterior. La autorizacion efectiva siempre ocurre en la API.

La ficha de la UCT asignada y los catalogos compartidos pueden aparecer aunque
las listas de datos de negocio esten vacias. Las vistas existentes de grupo,
personal, proyectos, produccion, recursos, transferencia, memorias, dashboard
y busqueda consumen respuestas ya limitadas por el backend. Una cuenta sin UCT
activa recibe un error de acceso en endpoints tenant; no se presenta un grupo
ajeno como alternativa.

## Contratos y tipos

`GET /api/v1/auth/ucts-permitidas` devuelve una lista de objetos `{id, nombre}`
para la sesion autenticada. Es un contrato de consulta, preparado para una
seleccion futura; hoy no modifica la sesion ni autoriza el uso de otro grupo.

Los tipos TypeScript de becas, autores, directivos y adoptantes admiten el
`grupo_utn_id` que ahora puede devolver la API. El payload de alta de adoptante
continua enviando solo `nombre`; la propiedad de UCT la decide el servidor.
Los errores `401`, `403` y `404` conservan el manejo uniforme de cada service
y vista. No se cachea una lista de UCT como fuente de permisos.

## Memorias y validacion

`MemoriasHome`, `MemoriaDetalle` y `MemoriaVersionDetalle` consumen memorias y
snapshots limitados a la UCT de la sesion. Un detalle o snapshot de otra UCT
responde como recurso no disponible. La exportacion conserva las restricciones
de rol y de pertenencia del backend. Las paginas mantienen sus estados vacios,
de carga y de error existentes.

La validacion tecnica incluyo `npm run build`, `npx tsc --noEmit` y solicitudes
HTTP reales con una cuenta LECTURA de LINES sin registros. La validacion visual
de esa sesion fue aceptada por el usuario. El selector de multiples UCT y sus
controles de interfaz se implementaran en una entrega posterior.
