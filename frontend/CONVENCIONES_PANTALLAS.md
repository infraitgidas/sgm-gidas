# Convenciones de pantallas del frontend

Este documento define el contrato visual y funcional de las pantallas del
sistema GIDAS. Su objetivo es facilitar la adaptación progresiva de módulos sin
perder contratos de dominio, permisos, trazabilidad ni contexto de navegación.

Las decisiones específicas de una entidad prevalecen cuando están documentadas,
pero toda excepción debe ser explícita y conservar las garantías de seguridad,
accesibilidad e historial descritas aquí.

## 1. Arquitectura y alcance

- Cada dominio vive en `src/modules/<modulo>` y separa `pages`, `services`,
  `hooks`, `components` y `utils` según corresponda.
- Las páginas componen la vista y coordinan consultas y navegación. La lógica
  pura de presentación, comparación o normalización debe residir en `utils`.
- Los services concentran tipos TypeScript, adaptación de contratos y llamadas
  HTTP. Las páginas no deben usar `fetch` directamente.
- Los hooks reutilizables encapsulan consultas y mutaciones de TanStack Query.
- Los componentes globales permanecen en `src/components` y no deben modificarse
  durante una adaptación de módulo sin autorización expresa.
- No se crean fachadas paralelas en `src/pages`, `src/services` o `src/hooks`.
- Router principal, layout, autenticación, hooks compartidos, estilos base y
  componentes globales son zonas restringidas.

## 2. Lenguaje visual común

- Mantener tipografía, paleta, radios, sombras, densidad y jerarquía de las
  pantallas de referencia ya aprobadas.
- El encabezado incluye título claro, descripción breve cuando aporte contexto y
  acciones principales alineadas con el patrón de Proyectos.
- Los textos usan español completo, tildes y nombres funcionales; no deben exponer
  claves de API, nombres internos ni identificadores técnicos.
- La interfaz debe ser minimalista: no duplicar instrucciones, estados, errores
  ni acciones que ya estén representados de forma suficiente.
- Los valores vacíos se muestran con una convención legible, normalmente `-` o
  un estado vacío descriptivo, nunca `undefined`, `null` o `[object Object]`.

## 3. Homes y listados ABMC

### 3.1 Estructura

- Usar la tabla compartida `Table` para listados ABMC; no recrear tablas por
  módulo ni modificar el componente global para resolver una particularidad
  local sin autorización.
- Mostrar como máximo 9 registros por página.
- La tabla debe ofrecer estados diferenciados de carga inicial, actualización,
  error recuperable, vacío y contenido.
- Un refetch con datos utilizables conserva las filas visibles y anuncia la
  actualización; no reemplaza el contenido por la carga inicial.
- Los errores de consulta ofrecen una acción `Reintentar` y un mensaje seguro y
  accionable.

### 3.2 Barra de búsqueda y filtros

- Búsqueda, chips de estado y selectores se ubican en una única barra horizontal.
- Los chips y selectores se alinean verticalmente con `py-1` en el contenedor.
- En anchos reducidos, la barra usa desplazamiento horizontal y no envuelve los
  controles.
- El scrollbar local aprobado usa `scrollbar-width: thin`, altura webkit de 4 px,
  thumb gris redondeado y track transparente.
- No se modifican estilos base para aplicar este scrollbar.
- Los filtros conservan el estado necesario al paginar y reinician la página
  cuando cambia el conjunto filtrado.
- Los nombres de filtros y opciones deben ser legibles y derivados de valores
  normalizados, nunca de la coerción implícita de objetos.

### 3.3 Filas, navegación y acciones

- La fila navega al detalle cuando la entidad posee esa vista.
- Los controles internos no deben disparar la navegación de la fila.
- Las acciones son individuales por registro. No se recuperan selección masiva
  ni paneles laterales retirados por la estandarización.
- Ver, editar, eliminar, cerrar, reabrir u otras transiciones se muestran solo
  cuando el estado y los permisos de frontend lo permiten.
- El backend continúa siendo la autoridad definitiva de permisos y reglas.
- Las acciones destructivas o de transición requieren confirmación cuando la
  regla de dominio vigente así lo establece.
- La baja lógica conserva confirmación, feedback visible e invalidación de las
  consultas relacionadas.
- El contexto de Memorias se preserva al navegar desde una fila y al volver.

### 3.4 Orden y paginación

- El orden debe ser controlado y usar etiquetas accesibles.
- La paginación se presenta debajo de la tabla, centrada y con anterior, números
  de página y siguiente cuando el componente lo soporte.
- La página activa se ajusta si una búsqueda, filtro o eliminación reduce la
  cantidad total de páginas.

### 3.5 Pantallas que no son listados ABMC

- Dashboard y Administración no adoptan automáticamente la tabla de homes: su
  estructura responde a información agregada y operaciones propias.
- Catálogos conserva su diseño específico. Solo incorpora nuevos tipos cuando un
  dominio lo requiere y no se rediseña como efecto lateral de otra adaptación.
- Un agregador de varias entidades debe identificar el tipo de cada fila y
  delegar navegación, permisos, acciones, eliminación e historial al service del
  dominio correspondiente.
- Una pantalla sin ruta accesible no se adapta de forma implícita: primero debe
  definirse su navegación y registrarse como tarea independiente.

## 4. Historial de cambios

### 4.1 Carga y paginación

- Toda entidad con endpoint de historial debe consumirlo en frontend.
- En homes, el historial se carga de forma diferida al expandir la fila.
- En detalles, se presenta dentro de la tarjeta `Historial de cambios`.
- Se muestran 3 eventos por página.
- Deben existir estados de carga, error con reintento y ausencia de eventos.
- La consulta y su caché se identifican por entidad e ID para no mezclar datos.

### 4.2 Cambios ordinarios de campos

- Un cambio ordinario muestra un título funcional y los valores anterior y nuevo.
- Fechas, montos, estados y catálogos se formatean de acuerdo con su dominio.
- Las relaciones u objetos se normalizan a un nombre conocido. Nunca se muestran
  JSON crudo, IDs internos ni `[object Object]`.
- Se omiten `accion`, `acciones`, valores equivalentes y registros que solo
  representan la inicialización de un campo.
- El valor asignado durante un alta es estado inicial y no debe presentarse como
  un cambio posterior salvo que el dominio requiera expresamente ese evento.

### 4.3 Eventos relacionados con acciones

Los campos que representan una acción o un cambio relacional no siguen el formato
`Valor anterior` / `Valor nuevo`. Deben usar la presentación directa establecida
en Trabajos en reuniones y Proyectos.

La tarjeta del evento muestra:

1. La acción realizada en pasado y con la entidad afectada.
2. El nombre legible de la persona, objeto o relación.
3. La fecha del evento.
4. El usuario que realizó la acción.

Ejemplos aprobados:

- `Autor vinculado` + `Dra. Ana Pérez (Investigador)`.
- `Autor desvinculado` + `Dra. Ana Pérez (Investigador)`.
- `Investigador vinculado` + nombre del investigador.
- `Becario desvinculado` + nombre del becario.
- `Coordinador asignado` + nombre del investigador.

Reglas obligatorias:

- No mostrar `Valor anterior` y `Valor nuevo` en estos eventos.
- No mostrar el ID de la relación como descripción.
- No mostrar el payload de auditoría ni su JSON serializado.
- Usar el nombre conservado en el snapshot o detalle del evento. Como
  compatibilidad, puede resolverse mediante la colección actual de la entidad.
- Si no existe un nombre seguro, mostrar una descripción funcional neutra; no
  sustituirla por el identificador interno.
- El backend debería registrar eventos relacionales con una estructura estable,
  por ejemplo `{ accion, detalle }`, y conservar en `detalle` los datos necesarios
  para interpretar el evento históricamente.
- El frontend centraliza la interpretación en una utilidad pura del módulo y la
  reutiliza en home y detalle.
- Una presentación personalizada debe ser optativa: los consumidores que no la
  utilizan conservan el formato ordinario anterior/nuevo.

## 5. Pantallas de detalle

- Incluir tarjeta principal, `Auditoría`, `Historial de cambios`, botón `Volver`
  y botón `Editar` cuando corresponda.
- `Editar` solo aparece si el registro está activo, su estado admite edición y el
  rol posee el permiso requerido.
- La información usa etiquetas funcionales y valores normalizados.
- Los enlaces externos válidos abren con `noopener noreferrer`.
- `Volver` respeta el contexto de navegación, especialmente desde Memorias.
- Un `successMessage` recibido por navegación se muestra y luego se elimina del
  estado sin descartar otros datos necesarios.

## 6. Formularios de alta y edición

- En alta, un guardado exitoso vuelve al home con `successMessage`.
- En edición, un guardado exitoso vuelve al detalle con `successMessage`.
- La edición envía únicamente diferencias reales.
- Si no existen cambios, no se llama al backend.
- Altas y bajas de relaciones se consolidan localmente y se persisten juntas al
  guardar; no se llama al backend por cada interacción del selector.
- Los campos obligatorios usan `Field required`; los opcionales no llevan marca.
- Los controles incluyen etiqueta asociada, placeholder o ayuda cuando resulte
  necesaria y errores próximos a la acción que debe corregirse.
- Las fechas civiles usan el contrato institucional y no se convierten con
  `toISOString()` para campos SQL `Date`.
- Los inputs se recortan, validan y normalizan antes de construir el payload.
- Los borradores, cuando aplican, se gestionan mediante el servidor y no guardan
  información sensible en `localStorage` o `sessionStorage`.
- Durante el guardado se bloquean acciones incompatibles y se muestra feedback
  accesible de progreso.

## 7. Mensajes y manejo de errores

- Mantener el estilo vigente de mensajes de éxito.
- Los errores del servidor deben ser claros, seguros y accionables.
- Carga: `Lo sentimos, no pudimos recuperar la información. Intente nuevamente.`
- Guardado: `Lo sentimos, no pudimos guardar los cambios. Verifique los datos e intente nuevamente.`
- Eliminación: `Lo sentimos, no pudimos completar la operación. Intente nuevamente.`
- Asociar `error.details.fields` a los controles mediante los helpers compartidos
  y enfocar el primer campo inválido.
- Los errores sin campo conocido mantienen el aviso general.
- No mostrar request IDs, trazas, claves internas ni respuestas desconocidas.

## 8. Permisos, seguridad y trazabilidad

- Toda acción se condiciona por rol y estado en frontend y se valida nuevamente
  en backend.
- Conservar auditoría, soft delete y trazabilidad histórica cuando correspondan.
- React presenta datos no confiables como texto; no usar HTML inyectado ni `eval`.
- Los endpoints críticos permanecen protegidos y los errores no filtran
  información sensible.
- No almacenar credenciales ni datos de sesión en storage del navegador.

## 9. Accesibilidad y responsive

- Diseñar mobile-first y validar visualmente en 375, 768, 1024 y 1440 px.
- Usar HTML semántico, encabezados coherentes, labels asociados y foco visible.
- Los botones declaran `type`; los controles solo con icono tienen nombre
  accesible y los iconos decorativos usan `aria-hidden`.
- Estados asíncronos usan `role`, `aria-live` o `aria-busy` según el patrón.
- La tabla conserva caption, encabezados con `scope`, orden con `aria-sort`,
  expansión con `aria-expanded` y soporte de teclado.
- Las transiciones respetan `prefers-reduced-motion`.
- Las columnas secundarias pueden ocultarse progresivamente; el contenido debe
  seguir siendo comprensible y las acciones esenciales permanecen disponibles.

## 10. Estado, consultas y rendimiento

- Los hooks se invocan siempre en el mismo orden; las consultas condicionales
  usan `enabled`.
- Diferenciar carga inicial de `isFetching`.
- Evitar duplicar estado derivable y no incorporar `useEffect` o `useMemo` sin una
  necesidad observable.
- Invalidar lista, detalle, historial, búsqueda, snapshots o agregados afectados
  después de una mutación.
- Reutilizar caché y carga diferida para evitar solicitudes innecesarias.
- La paginación y los filtros de servidor deben usar consultas optimizadas cuando
  el volumen de datos lo requiera.

## 11. Pantallas públicas y autenticación

- Pueden usar una composición de pantalla completa independiente del layout
  autenticado, sin alterar los destinos institucionales aprobados.
- Deben distinguir restauración de sesión, consulta inicial, actualización y
  error; una indisponibilidad no se interpreta como autorización válida.
- No consultar información de configuración pública que ya no sea necesaria para
  un usuario autenticado.
- Login, registro, recuperación y rutas protegidas deben permanecer alineados con
  el router y con la autorización del backend.
- La carga de una ruta diferida ofrece feedback y un error recuperable sin
  exponer detalles técnicos.

## 12. Pruebas y aceptación por módulo

- Cubrir tabla, búsqueda, filtros, permisos, acciones, historial, paginación y
  valores estructurados mediante pruebas focalizadas.
- Cuando cambia backend, agregar pruebas de rutas, service, reglas de negocio,
  integridad, auditoría, snapshots y concurrencia cuando corresponda.
- Ejecutar `npm test`, `npm run typecheck`, `npm run build:production` y
  `git diff --check` al finalizar el módulo.
- Las validaciones automatizadas corresponden al agente; la validación visual y
  funcional corresponde al usuario.
- Antes de la aprobación no se actualizan README, documentación técnica ni
  `CHANGELOG.md`, no se cierra la tarea y no se ejecuta el commit.
- Tras la aprobación y la solicitud de cierre, actualizar documentación como
  último paso, cerrar la tarea y realizar el commit solo si fue solicitado.

## 13. Lista de control para adaptar una pantalla

- Revisar tarea activa, contratos frontend/backend y una pantalla comparable.
- Identificar permisos, estados, contexto de Memorias y reglas de baja.
- Mantener 9 registros por home y 3 eventos por página de historial.
- Aplicar la barra de filtros y scrollbar compacto aprobados.
- Garantizar navegación de fila y acciones individuales condicionadas.
- Implementar carga diferida del historial cuando corresponda.
- Separar cambios ordinarios de eventos de acción o relación.
- Normalizar objetos, catálogos y personas a etiquetas legibles.
- Verificar carga, actualización, error, vacío y reintento.
- Verificar teclado, foco, nombres accesibles y responsive.
- Ejecutar pruebas focalizadas y suite completa del módulo.
- Esperar aprobación antes de documentar y cerrar.
