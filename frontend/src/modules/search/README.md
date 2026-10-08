# Busqueda global

Los movimientos financieros recuperados enlazan a `/movimientos/:id`. El detalle
conserva el contexto de retorno a Búsqueda; el listado financiero muestra los
registros de la UCT activa.

La busqueda se ejecuta automaticamente luego de 400 ms sin escritura y requiere
al menos dos caracteres. Cada nueva consulta cancela la anterior mediante
`AbortController`; un identificador interno impide que una respuesta antigua
reemplace resultados recientes.

El hook conserva hasta 30 consultas durante 30 segundos. La clave incluye texto,
orden, estado y pagina. El endpoint se consume con paginas de 9 resultados.

## Contratos y validaciones

El service usa `URLSearchParams` para codificar la consulta y acepta exclusivamente
los ordenamientos `alf_asc`, `alf_desc`, `fecha_asc` y `fecha_desc`. La pagina se
normaliza a un entero positivo y el texto requiere entre 2 y 80 caracteres. Los
rangos de fecha inconsistentes se rechazan antes de presentar resultados filtrados.

La respuesta se valida defensivamente antes de convertirla a `SearchResult`. Los
elementos heterogeneos de `extra` se leen mediante guards y solo se conservan IDs,
etiquetas y URLs con tipos validos. Las URLs externas o protocol-relative se
rechazan y redirigen a la busqueda.

## Seguridad y estados

El resaltado se construye con nodos React desde texto, sin HTML inyectado. Los
errores usan el extractor seguro compartido y muestran un mensaje accionable. Las
consultas anteriores se cancelan con `AbortController` y un identificador impide que
una respuesta tardia reemplace resultados recientes.

La busqueda respeta los permisos del endpoint; el frontend no usa el filtrado visual
como barrera de autorizacion. Los resultados se paginan de a 9 y los parametros
validos se reflejan en la URL para permitir navegacion reproducible.

Antes de desplegar deben ejecutarse typecheck, build, tests backend y
`python tools/verify_search_retrieval.py`. Este ultimo comando es de solo lectura
y valida recuperacion real en los 24 modulos buscables.

La cobertura integral se valida con los datos ficticios e idempotentes de
`backend/tools/seed_testing_data.py` en una base aislada. El seed requiere
`APP_ENV=testing` o una habilitacion efimera y consciente mediante
`ALLOW_TEST_SEED=true` en staging. Esta variable no debe persistirse ni utilizarse
contra produccion. La validacion de referencia recupera correctamente los 24
modulos.

## Feedback de acciones (seguimiento ISS-09)

Las acciones asíncronas del módulo usan Button con loading/loadingText
o ConfirmDialog, que espera la promesa devuelta por onConfirm. Durante la
operación se muestra texto de progreso con un icono animado, aria-busy y
role=status. El botón de acción se deshabilita hasta terminar; las
confirmaciones bloquean además cancelar, el fondo y los campos del diálogo.
El estado se libera al resolver o fallar, conservando errores y mensajes de
éxito existentes. Los callbacks basados en React Query deben devolver
mutateAsync para que el diálogo cubra toda la operación.

## ISS-12: autoría de integrantes

La vista de búsqueda muestra el preview de trabajos usando extra.autores y la etiqueta Autores. Los nombres pueden pertenecer a investigadores o becarios; el resto de tipos de resultados conserva su contrato.

Corrección de alcance ISS-12: los autores de trabajos son únicamente investigadores y becarios. Personal (PTAA/profesional) no puede vincularse como autor. Se mantiene la etiqueta Autores.

## ISS-13: fecha de presentación

La fecha genérica del resultado de un trabajo en reunión corresponde a
fecha_presentacion. El enlace abre el detalle con Fecha de presentación;
se conserva el contrato genérico de SearchPage sin campos nuevos de búsqueda.

## Paginación de listados (ISS-23)

Los resultados paginados muestran controles centrados de anterior, números
de página y siguiente, inmediatamente debajo de las tarjetas o resultados.
El máximo de resultados por página conserva el contrato del módulo.
