# Aislamiento de datos por UCT

## Alcance de esta etapa

Cada usuario activo, incluidos ADMIN, GESTOR y LECTURA, trabaja en una unica
UCT activa asignada. La seleccion de varias UCT por un administrador queda para
otra entrega. No existe un header ni un parametro HTTP que cambie la UCT activa:
el backend la resuelve desde las pertenencias persistidas en cada solicitud.

Los catalogos compartidos (roles, tipos, cargos, fuentes de financiamiento y
otros valores de referencia) son globales. Los datos de negocio de una UCT se
filtran en listados, detalles, relaciones, historiales, busqueda, dashboard,
saldos, memorias, snapshots y exportaciones. Un ID de otra UCT no concede
acceso aunque el usuario conozca su valor.

## Modelo y migraciones

`usuario_grupo_utn` relaciona `usuario.id` con `grupo_utn.id`. Cada pertenencia
tiene estado activo, fecha y autor de creacion, fecha y autor de actualizacion,
y campos de baja logica. Los indices permiten resolver pertenencias por usuario
y grupo; la unicidad parcial impide dos pertenencias activas al mismo par.

La migracion `b2c4d6e8f0a1` crea la tabla. Asigna usuarios activos solo si
existe exactamente una UCT activa y un ADMIN activo. Con dos o mas UCT activas
no adivina la pertenencia: los usuarios quedan sin acceso a datos tenant hasta
recibir una asignacion verificada.

La migracion `c3d5e7f9a1b2` agrega `grupo_utn_id` nullable a becas, autores,
directivos y adoptantes. Conserva el propietario cuando las relaciones apuntan
a una sola UCT; registros ambiguos permanecen sin propietario y no se exponen.
Las FKs nullable permiten revisar datos heredados antes de hacerlas obligatorias.
Ambas migraciones tienen downgrade; el downgrade elimina el estado de
pertenencias o propietario agregado, por lo que se debe respaldar la base antes
de aplicarlo.

## Resolucion y permisos

`tenant_request.py` valida el access token, consulta el estado actual del
usuario y su rol y exige exactamente una pertenencia activa hacia una UCT
activa. La ausencia de pertenencia o mas de una pertenencia activa devuelve
`403` en endpoints tenant. Una cuenta o token invalido devuelve `401`. Las
rutas publicas de autenticacion y las rutas de perfil, cambio de contrasena y
consulta de pertenencias tienen las excepciones necesarias para resolver el
estado de la sesion. La primera alta de UCT tiene una excepcion acotada para
el ADMIN inicial cuando aun no existe ninguna UCT activa.

`GET /api/v1/auth/ucts-permitidas` devuelve `[{"id": 1, "nombre": "GIDAS"}]`
para el usuario autenticado. Es informativo: el frontend no puede usar el
resultado para autorizar otra UCT. `POST /api/v1/auth/usuarios` y el registro
posterior al administrador inicial asignan al usuario nuevo la misma UCT del
ADMIN que realiza el alta. La primera creacion de grupo asigna su creador.

Los controles de rol existentes siguen vigentes: LECTURA consulta; GESTOR y
ADMIN pueden mutar solo las operaciones que su ruta permite y siempre dentro
de su UCT. La capa ORM de `tenant_scope.py` filtra lecturas por propietario,
incluidas las entidades cuya UCT se deriva de un padre. Antes de persistir,
asigna la UCT a registros nuevos cuando corresponde y rechaza cambios de
propietario o relaciones con otra UCT. Los historiales comprueban primero la
visibilidad del registro padre. Un recurso ajeno se presenta como no encontrado
en las rutas de detalle que usan esta politica; los permisos de rol mantienen
`403`.

## Memorias y snapshots

Una memoria pertenece a una UCT. Al cerrar una version, cada consulta de
origen debe usar la UCT de esa memoria; si falta memoria o UCT, la generacion
falla antes de seleccionar datos. Las filas de snapshot se filtran tanto por
la version de la memoria como por la UCT de su fuente. Una fila con fuente de
otra UCT no aparece aunque ya estuviera almacenada.

El contexto institucional historico se serializa solo cuando el grupo
congelado coincide con la UCT de la memoria. La exportacion Excel aplica la
misma comprobacion; un contexto historico ausente o inconsistente no se
reconstruye desde los datos actuales. Historiales, saldos, busqueda y dashboard
usan el mismo alcance. Los catalogos globales pueden conservar contadores o
opciones visibles aun cuando la UCT no tenga registros de dominio.

## Despliegue y verificacion

1. Respaldar la base y revisar las UCT activas, las cuentas existentes y los
   registros con propietario ambiguo.
2. Ejecutar `flask db upgrade` antes de iniciar el backend con esta version.
3. Asignar pertenencias verificadas a cuentas heredadas si habia mas de una
   UCT activa. Nunca asignarlas por nombre de usuario sin revisar los datos.
4. Comprobar con dos UCT que listados, detalles, snapshots, exportaciones,
   busqueda y dashboard no devuelven datos cruzados.

Las pruebas automatizadas principales estan en `tests/test_tenant_scope.py` y
`tests/test_memoria_periodos_uct.py`. En desarrollo se comprobo ademas una
sesion LECTURA de LINES sin registros frente a GIDAS con dos memorias: LINES
recibio listas vacias y `404` para un detalle y snapshot de GIDAS.

El selector de UCT, la gestion administrativa de pertenencias y la conversion
final de FKs historicas nullable quedan fuera de esta etapa.
