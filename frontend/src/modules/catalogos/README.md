# Catalogos frontend

## Filtros desplegables (ISS-47)

CatalogosHome: estado de valores; las opciones de estado siguen deshabilitadas cuando el catálogo no informa estado.
Los filtros del listado utilizan `TableFilterSelect`, con nombre accesible y
selección mediante teclado. Todos/Todas elimina la restricción del criterio.
La adaptación del selector conserva valores, setters y opciones de consulta;
se mantienen services, permisos, nueve filas por página, contexto de Memoria
y persistencia de filtros de ISS-50. No se modifican campos de formularios.

Aceptado visual y funcionalmente el 06/11/2026. Validación integrada:
269 pruebas frontend, TypeScript y build de producción aprobados.
`tests/homeFilterSelect.test.ts` comprueba selección y limpieza en las cuatro
pantallas principales y ausencia de chips de filtrado en los homes.

## Retorno al origen y breadcrumb (ISS-45)

Al abrir Gestionar Catálogos desde `Sidebar`, el enlace guarda en el estado
de navegación `catalogosReturnTo`, con `pathname`, `search`, `hash` y `state`
del origen. `utils/catalogNavigation.ts` valida el destino interno y excluye
mensajes de éxito y retornos anidados del contexto que se restaura.

`CatalogosHome` resuelve el destino con `getCatalogReturn`. Volver restaura
la URL y el estado del origen y reemplaza la entrada de Catálogos. Un acceso
directo sin origen válido vuelve a Inicio. Reingresar al mismo enlace conserva
el origen inicial y recargar la entrada mantiene su estado. Los filtros y
borradores siguen usando sus mecanismos existentes; esta navegación no guarda
valores nuevos de formularios ni ejecuta mutaciones de catálogo.

El breadcrumb incorpora la jerarquía del origen, por ejemplo
`Inicio > Proyectos > Detalle > Editar > Catálogos`. Su enlace al origen
conserva query, hash y contexto. Sin origen válido muestra `Inicio > Catálogos`.
La resolución compartida y las pruebas de enlaces están en `shared`.

Se mantienen roles, validaciones, services y contratos HTTP existentes.
Pruebas de retorno y componentes reales en `tests/catalogNavigation.test.ts`;
breadcrumb en `tests/routeBreadcrumbs.test.ts`. Aceptado visual y funcionalmente
el 06/11/2026: 264 pruebas frontend, TypeScript y build aprobados.

## Validacion preventiva de formularios (ISS-33)

`CatalogosHome` muestra el error junto al nombre durante alta y edicion,
al escribir y al salir del campo. Reutiliza la regla descriptiva del catalogo;
autores bibliograficos y adoptantes conservan la restriccion de letras Unicode
y espacios. El guardado conserva sus comprobaciones, normalizacion y control
definitivo de duplicados en servidor. Abrir otra edicion o completar un alta
limpia el feedback local correspondiente. No se persiste el catalogo al validar.

El panel mantiene errores locales separados para el nombre de alta y el de
edicion, con su comprobacion especifica `validateName`. No agrega hooks
compartidos ni modifica componentes globales.
Las validaciones no disparan escrituras de dominio. Se conservan services,
contratos, permisos, borradores, navegacion y feedback de exito.
La etapa fue aceptada visual y funcionalmente por el usuario el 05/11/2026;
la regresion transversal esta en `tests/liveValidation.test.ts`.

## ISS-83: administracion de adoptantes

`CatalogosHome` incluye `Adoptantes` sin ruta nueva. El service generico consulta
`GET /adoptantes?activos=all` para mostrar vigentes e inactivos, y ofrece alta,
edicion, baja logica e historial por registro. La tabla muestra nueve valores por
pagina y el historial diferido tres cambios por pagina, con carga, vacio, error
y reintento. Solo ADMIN y GESTOR ven acciones de escritura; LECTURA conserva
acceso de consulta al endpoint protegido.

El nombre acepta letras Unicode y espacios; se normalizan espacios repetidos.
En edicion se envia PUT solo si hay una diferencia real. Las mutaciones invalidan
las consultas para reflejar correcciones en los formularios de transferencia.
El backend bloquea la baja de un adoptante vinculado a una transferencia activa.
El historial del adoptante muestra cambios de nombre y estado; los eventos de
vinculo pertenecen al historial de la transferencia.

## ISS-82: autores de documentación bibliográfica

La opción `Autores de documentación bibliográfica` se integra en
`CatalogosHome`, sin ruta nueva. Usa el service genérico `catalogoServices.ts`
con `/autores/` y el campo `nombre_apellido`. El listado consulta
`?activos=all`, muestra hasta nueve autores por página y distingue vigentes e
inactivos. Cada autor tiene historial diferido con tres eventos por página,
responsable, fecha y valores legibles, además de estados de carga, vacío y error.

ADMIN y GESTOR pueden crear, editar y dar de baja desde Catálogos. La creación
desde el formulario de Documentación sigue disponible. El nombre admite letras
Unicode y espacios; se normalizan espacios repetidos y se envía `PUT` solo si
hay una diferencia real. La edición invalida las consultas para reflejar la
corrección en Documentación. El backend decide definitivamente los permisos y
el alcance por UCT.

La baja es lógica: se bloquea si el autor participa en una documentación
activa y se permite si todas sus documentaciones vinculadas están inactivas.
Catálogos muestra la confirmación y el error correspondiente. Los cambios de
nombre y estado pertenecen al historial del autor; sus vínculos pertenecen al
historial de Documentación.

## Paginacion de Gestion de Catalogos (ISS-75)

El listado de valores usa el aspecto compacto de la
paginacion de `Table`: botones `Anterior` y `Siguiente`, numeros de pagina y
resaltado de la pagina actual. Los extremos se deshabilitan segun la pagina
seleccionada. Se mantienen nueve valores por pagina y tres eventos por pagina
en el historial de cada valor.

## Alcance

El modulo centraliza la consulta y administracion de valores reutilizados por
personal, proyectos, produccion, recursos y transferencia. `CatalogosHome` permite
seleccionar un tipo de catalogo y buscar sus valores. La tabla compacta muestra el
nombre vigente, estado, auditoria y acciones permitidas.

`ObjetosFinHome` conserva la vista combinada heredada de equipamientos y erogaciones;
los flujos principales de esas entidades se documentan en el modulo `recursos`.

## Services, tipos y hooks

- `catalogoServices.ts` expone las operaciones genericas de listado, historial,
  alta, actualizacion y baja logica.
- Los services especificos de categorias UTN, fuentes, procedencias y tipos ofrecen
  opciones tipadas a los formularios consumidores.
- Los hooks basados en React Query encapsulan carga, cache e invalidacion de las
  opciones compartidas por los modulos funcionales.

Los endpoints se reciben como definiciones internas constantes, no desde entradas
del usuario. Los cuerpos se serializan como JSON y los errores reconocidos se
procesan mediante el extractor seguro compartido.

Tipo de revista se administra mediante `/tipos-revista/` y es independiente de
Tipo de reunión científica. Sus valores iniciales de testing son `Nacional` e
`Internacional`; el formulario de Trabajos en revistas consume el service y
hook dedicados del módulo Producción.

## Permisos y estados

Los roles `ADMIN` y `GESTOR` pueden crear, editar y eliminar valores. `LECTURA`
puede consultar catalogos e historiales, pero la interfaz no presenta acciones de
mutacion. El backend vuelve a validar el rol y constituye la autoridad final.

Cuando el contrato informa `activo` o `deleted_at`, la interfaz distingue activos e
inactivos y evita editar o volver a eliminar un valor dado de baja. La eliminacion
es logica cuando lo implementa el catalogo correspondiente.

## Validaciones y actualizaciones

- Los nombres se recortan y deben contener al menos una letra Unicode. Pueden
  incluir numeros y signos junto a texto descriptivo. La validacion se aplica en
  altas y al cambiar el nombre en edicion; los registros existentes no se migran.
- Las descripciones se recortan antes de persistirse.
- En edicion se comparan nombre, descripcion y relacion; si no existen diferencias,
  no se llama al backend.
- Los errores de carga, dependencias, historial y mutaciones permanecen visibles y
  accionables.

## Paginacion e historial

El catalogo seleccionado muestra como maximo 9 valores por pagina. Cada fila ofrece
una accion `Historial`: al abrirla consulta `/:id/historial` y muestra hasta 3
eventos por pagina, incluyendo cambios de campos y eventos de sistema cuando el
backend los informa. La carga inicial no solicita todos los historiales.

Editar un nombre conserva el ID del valor y registra el cambio historico. La baja
logica se muestra como `Inactivo`; los valores disponibles se indican `Vigente`.
Las advertencias generales se retiraron de la pantalla. El manual de usuario queda
fuera de este issue por indicacion del usuario.

## Contratos relevantes

- Listado: `GET <endpoint>?activos=all`.
- Historial: `GET <endpoint>/:id/historial`.
- Alta: `POST <endpoint>` con el campo de nombre propio del catalogo.
- Edicion: `PUT <endpoint>/:id` solo con diferencias reales.
- Baja: `DELETE <endpoint>/:id`.

Las respuestas incluyen como mínimo `id` y el campo de nombre. Pueden incorporar
`activo`, marcas de auditoría y relaciones tipadas.

## Feedback de acciones (seguimiento ISS-09)

Las acciones asíncronas del módulo usan Button con loading/loadingText
o ConfirmDialog, que espera la promesa devuelta por onConfirm. Durante la
operación se muestra texto de progreso con un icono animado, aria-busy y
role=status. El botón de acción se deshabilita hasta terminar; las
confirmaciones bloquean además cancelar, el fondo y los campos del diálogo.
El estado se libera al resolver o fallar, conservando errores y mensajes de
éxito existentes. Los callbacks basados en React Query deben devolver
mutateAsync para que el diálogo cubra toda la operación.
CatalogPanel comparte un bloqueo entre alta, edición y eliminación.
Muestra Creando, Guardando o Eliminando según la acción.

## Indicadores de campos obligatorios (ISS-21)

En altas y ediciones, el nombre muestra el indicador obligatorio. Becas se
administra desde Personal > Becas y ya no forma parte de `CatalogosHome`.

## Paginación de listados (ISS-23)

Los resultados paginados muestran controles centrados de anterior, números
de página y siguiente, inmediatamente debajo de las tarjetas o resultados.
El máximo de resultados por página conserva el contrato del módulo.

## Denominaciones y tipos de personal

Los nombres de Gestionar Catálogos son la referencia para las etiquetas y
selectores de los formularios consumidores. Se usa Tipo de Registro de Propiedad
para ese catálogo. Los mensajes visibles mantienen tildes y signos de apertura.

La API de Tipo de Personal rechaza nombres equivalentes por tildes, mayúsculas,
espacios o puntuación, incluidos registros inactivos. Los errores se muestran
en el flujo existente. Una opción retirada conserva su historial y referencias;
la depuración no reasigna personas. Los permisos, nueve valores por página y
tres eventos por página de historial mantienen sus contratos.


## Recuperacion del contexto de consulta (ISS-50)

CatalogosHome recupera el catalogo seleccionado; cada CatalogPanel conserva busqueda, estado y pagina por endpoint. Los borradores y las acciones de alta/edicion siguen su flujo propio.

Los homes con estado local usan `shared/hooks/useHomeState.ts`; Busqueda conserva
su contrato de URL. La persistencia validada se limita a la pestana y al usuario,
sin guardar filas ni acciones pendientes. Se mantienen services, permisos,
validaciones y paginacion vigentes. Contrato y pruebas en `../shared/README.md`.
Aceptado funcionalmente por el usuario el 06/11/2026.
