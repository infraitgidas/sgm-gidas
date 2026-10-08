# Borradores de formularios

## Paginacion compartida (ISS-89)

`controllers/pagination.py` valida `page`, `per_page`, `activos` y `orden`, y
arma respuestas paginadas; ya no registra un hook global. Los services usan
`count` y `LIMIT/OFFSET` sobre la consulta filtrada antes de serializar. El
marcador `meta.source = "legacy-list"` permanece en las rutas que ya lo
exponian para conservar el contrato HTTP. `services/catalog_pagination.py`
centraliza la paginacion de catalogos y `services/auditoria_service.py` pagina
los cambios por entidad y UCT, con orden estable. Los historiales de detalle
siguen mostrando tres eventos por pagina.

`GET /api/v1/borradores` conserva su respuesta anterior sin parametros. Con
`page` o `per_page` devuelve `data`, `meta` y `error`; el total y la pagina se
calculan solo sobre borradores vigentes del usuario autenticado. Una pagina
invalida responde `VALIDATION_ERROR` (400).

## Lecturas con alcance UCT (ISS-84)

`services/tenant_scope.py` conserva por identificador de UCT las opciones y
predicados ORM usados en las lecturas. La UCT se resuelve de nuevo para cada
solicitud a partir de la pertenencia activa del usuario; la cache no almacena
datos ni respuestas. Las escrituras siguen validando la UCT y sus relaciones
antes de persistir. `test_tenant_scope.py` verifica la alternancia entre dos
UCT y el aislamiento de consultas, memorias y becas.

## Ruta de retorno de proyectos (ISS-68)

El servicio de borradores devuelve `/proyectos/:id/editar` para un proyecto
existente y `/proyectos/nuevo` para uno nuevo. El payload del borrador y sus
validaciones no cambian; el frontend conserva la redirección desde la ruta
anterior para enlaces guardados.

El backend guarda un único borrador por usuario, módulo y registro en `form_draft`.
Un `PUT` reemplaza la última versión del mismo elemento. Los datos viven en la base
de datos y vencen a los siete días. La lista muestra metadatos, nunca el contenido.
Para borradores de Personal, Becario e Investigador, la lista incluye
`display_name` cuando el nombre del borrador contiene solo letras y espacios.
El resto de los campos del formulario no se expone en el listado.

## Endpoints

Todos requieren un access token válido y rol `ADMIN` o `GESTOR`.

- `GET /api/v1/borradores`: lista los borradores vigentes del usuario.
- `GET /api/v1/borradores/<module>/<record_key>`: devuelve datos de un borrador propio.
- `PUT /api/v1/borradores/<module>/<record_key>`: guarda `{ "data": { ... } }`.
- `DELETE /api/v1/borradores/<module>/<record_key>`: descarta un borrador propio.

`record_key` es `new` o un ID entero positivo. Los módulos permitidos y sus rutas
de retorno están en `services/form_draft_service.py`. El cuerpo no puede superar
64 KiB, tener más de 12 niveles ni contener claves de credenciales. Los errores
usan el contrato general de respuestas. La entidad sigue validándose al guardar
definitivamente; el borrador no concede permisos de edición sobre ella.

El frontend envía `data.__draft_meta.schema=1` y una huella de los valores
originales junto con `data.fields`. El backend guarda ese JSON sin interpretar
la huella y valida claves sensibles en toda la estructura. Los borradores
vencidos se ocultan de inmediato y se eliminan al consultar o guardar borradores
del usuario. Una fila de un usuario que nunca regrese permanece hasta una
limpieza operativa de la base.

La migración `a1d7c9e2f4b6` crea la tabla y sus índices. Debe ejecutarse con el
servicio `migrate`, que utiliza un rol con permisos DDL; el rol de la aplicación
no tiene permiso para crear tablas.

El listado de borradores incluye opcionalmente `display_name`, derivado de
campos de identificacion ya guardados (nombre, titulo, denominacion, evento
o numero, segun modulo). La lista sigue omitiendo `data` y solo el usuario
propietario puede consultarla. El valor se normaliza y limita a 120 caracteres.

## Rendimiento UCT y tablas paginadas (ISS-94)

La politica ORM reutiliza las mismas opciones inmutables de alcance que ya
heredan las consultas de relaciones. Antes de cada flush agrupa las claves
foraneas por modelo y columna y valida lotes de hasta 500 IDs. Conserva el
rechazo de relaciones ajenas y vuelve a consultar la pertenencia en cada
flush: no almacena resultados de autorizacion entre escrituras.

`table_query_page` recibe expresiones SQL definidas por cada service, aplica
el alcance UCT explicito a la entidad raiz y recupera solo la pagina pedida.
El parametro interno `sortable` permite limitar el orden a un subconjunto
de campos, independientemente de las expresiones usadas en filtros.
`table_scope_predicate` protege tambien las proyecciones y subconsultas de
relaciones, donde un filtro ORM implicito puede no alcanzar el conteo.

Las rutas que optan por `view=table` aceptan `page`, `per_page`,
`activos=true|false|all`, `q` (hasta 200 caracteres), `sort`,
`direction=asc|desc`, `filter_<campo>` e `ids` separados por coma.
Los nombres de orden y filtro se definen en el modulo; nunca se interpolan
expresiones SQL recibidas del cliente. Los IDs deben ser positivos y se
intersectan con la UCT; `ids=` produce un listado vacio.

`table_page_response` devuelve `data`, `error` y `meta` con
`page`, `per_page`, `total`, `total_pages` y `options`.
Cada opcion es `{value: string, label: string}`. Se calcula sobre todo el
alcance de estado/IDs/UCT antes de busqueda y filtros individuales, para
conservar opciones de otras paginas. Los errores son `VALIDATION_ERROR`
(400); siguen disponibles las respuestas anteriores sin `view=table`.
Las regresiones de aislamiento, lotes y tablas estan en
`tests/test_tenant_scope.py`.
