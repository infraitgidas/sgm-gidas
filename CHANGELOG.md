# Changelog

Este archivo registra los cambios funcionales y correcciones derivados del
testing del sistema GIDAS.

El formato se basa en Keep a Changelog y las versiones siguen versionado
semántico cuando se publica una entrega.

## [Sin publicar]

### ISS-94: rendimiento de listados y cierre de memorias

- Docencia, Transferencias y Biblioteca recuperan nueve filas por pagina
  desde el servidor, con busqueda, orden, totales y opciones de filtro sobre
  todo el alcance de estado/memoria. Se conservan listas anteriores para
  formularios y otros consumidores, permisos y aislamiento UCT.
- Se precargan relaciones utilizadas en Produccion, Transferencias,
  Personal, Becas y PID. Inicio reutiliza los registros del resumen para
  contar integrantes por grupo, evitando consultas por coleccion.
- La politica UCT reutiliza opciones ORM heredadas y valida claves foraneas
  en lotes por flush, sin cachear resultados de autorizacion entre escrituras.
  Los totales, opciones y subconsultas de tablas conservan el alcance explicito.
- El cierre recolecta snapshots sin autoflush por consulta ni flush por
  transferencia; conserva commit atomico, validacion, auditoria y contenido.
  MemoriaDetalle invalida lista, detalle e historial en paralelo.

Mediciones locales: Docencia 41 a 11 consultas en su nueva tabla,
Transferencias 68 a 9, Biblioteca 16 a 8 e Inicio 59 a 19. El cierre
paso de 1540 a 413 consultas. Son resultados del escenario local, no
limites de latencia. La primera carga de Vite conserva su costo de
transformacion; los archivos compilados se midieron por separado.

Validacion: 648 pruebas backend, 197 frontend, TypeScript, build de
produccion, Compose, topologia y escaneo de secretos correctos.
Aceptacion funcional del usuario el 03/10/2026, confirmando cargas mas
rapidas, y solicitud expresa de commits. Las tareas y artefactos permanecen
excluidos de Git.

### Preparación de PR y verificación de CI

- El control de mensajes admite scopes separados por coma y conserva los tipos,
  el scope opcional y la descripción obligatoria; evita rechazar commits
  históricos como `docs(readme, changelog)` sin reescribir el historial.
- El validador productivo exige publicar el proxy en loopback. Las pruebas
  cubren esa restricción, la alternativa TLS y la precompresión gzip.
- Tareas y artefactos locales quedan fuera del seguimiento de Git. Se retiró
  el informe pre-merge obsoleto y se actualizó su referencia documental.

Verificación local del 02/10/2026: 637 pruebas backend con Python 3.11 y las
25 dependencias declaradas, 193 frontend con Node 22, TypeScript, build,
Compose, topología y escaneo de secretos correctos. El control Bash de
mensajes pasó sobre el rango `origin/main..HEAD` y nueve casos de formato.

### ISS-94: reapertura y acciones por versión de memoria

- ADMIN y GESTOR pueden reabrir una memoria cerrada, creando una versión abierta
  y conservando la versión histórica. La baja sigue reservada a ADMIN.
- El listado expandible presenta iconos de detalle, reapertura, cierre y revisión,
  condicionados por estado, versión vigente y permisos, con confirmación y feedback.
- El historial se refresca al reabrir; los mensajes del listado siguen visibles
  aunque el cambio de estado retire la memoria del filtro actual.
- Diagnóstico de rendimiento: navegación con costo de consultas/relaciones y
  cierres reales de aproximadamente 24 s; predominan validaciones de pertenencia
  UCT por registro y consultas repetidas. No se aplicó una optimización ni se
  desactivaron controles de seguridad.

Validaciones: 23 casos backend de flujo/período, 193 pruebas frontend, TypeScript
y build correctos; aprobación visual/funcional del usuario el 02/10/2026.

### ISS-94: logros obtenidos de proyectos PID

- Proyectos incorporan `logros_obtenidos`, opcional y de hasta 20000 caracteres,
  con carga, edición por diferencias, borradores, detalle e historial.
- La migración aditiva `a7c9e2f4b6d8` añade el campo al proyecto y su snapshot.
  El Excel consume el texto congelado; los informes históricos se conservan como
  compatibilidad para versiones anteriores.
- Acciones del detalle alineadas a la derecha y botón `Registrar Informe`.

Validaciones: creación, auditoría, validación, exportación e inmutabilidad
histórica cubiertas por pruebas; aceptación del usuario el 02/10/2026.

### ISS-93: gestión de becas y alertas de vencimiento

- Becas se administra desde Personal mediante tabla paginada, búsqueda, alta,
  edición, detalle, auditoría e historial. Se retiró de Catálogos.
- El formulario de Becarios selecciona becas existentes y exige el plazo del
  vínculo. Un modal informativo muestra a GESTOR los vencimientos con menos de
  30 días, destacando el tiempo restante sin permitir una extensión.

Validaciones: aceptación visual y funcional del usuario, 191 pruebas frontend,
10 pruebas backend focalizadas, `typecheck` y build de producción correctos.

### ISS-94: Excel institucional y escenario formal de memorias

- La generación completa la referencia `Memorias 2025 - GIDAS.xlsx` conservando
  hojas, encabezados, combinaciones, formato e impresión; amplía tablas cuando
  exceden sus filas disponibles y normaliza contenido a Calibri 11 negro.
- El documento usa snapshots inmutables, autoridades y planificación congeladas,
  fechas nativas y finanzas consolidadas en ARS por fuente y categoría.
- Seed optativa institucional 2025 y escenario formal 2025/2026 con protección de
  credenciales, otras UCT y fotos históricas. El escenario 2026 no crea memorias
  ni exporta: el operador selecciona el período y genera desde la interfaz.
- El botón de Excel muestra `Generando el archivo...` exclusivamente dentro del
  control mientras se procesa y evita envíos duplicados.

Validaciones: aceptación visual/funcional del usuario el 02/10/2026; suite backend
de 637 casos, 193 pruebas frontend, TypeScript y build de producción correctos.

### ISS-57 a ISS-62: movimientos financieros ARS/USD y cotización BCRA

- Los movimientos conservan su importe y moneda original; los saldos,
  dashboard, búsqueda y exportaciones consolidan en ARS con el equivalente
  persistido. El detalle muestra la cotización y su fecha.
- La cotización minorista vendedor del BCRA se sincroniza mediante un job
  idempotente. El alta USD usa la observación oficial de su fecha o la última
  anterior y conserva el valor aplicado en el movimiento y la memoria.
- Se incorporaron migración, validaciones, permisos, auditoría y pruebas de
  regresión para precisión decimal, saldos, snapshots y exportación.

Validaciones: 36 pruebas backend focalizadas y 192 frontend correctas,
`typecheck` y build correctos; job BCRA ejecutado dos veces con cinco
observaciones insertadas y luego cero duplicados. El usuario aprobó el flujo
financiero. La validación final del Excel institucional se completó en ISS-94.

### ISS-91: capacidades disponibles en Mi perfil

- La tarjeta de permisos muestra solamente las acciones disponibles para el rol
  de la sesión, centradas en la tarjeta.
- Las reglas de autorización y el contrato backend permanecen iguales.

Validaciones: aceptación visual y funcional del usuario, 4 pruebas frontend
dirigidas, `typecheck` y `git diff --check` correctos.

### ISS-90: menú lateral fijo en escritorio

- El menú autenticado permanece fijo a la izquierda desde 1024 px y conserva el
  diálogo desplegable en móvil.
- La paleta coincide con la barra superior y la sección de perfil permanece en
  el pie del menú en ambos tamaños.

Validaciones: aceptación visual y funcional del usuario, 191 pruebas frontend,
6 pruebas de navegación dirigidas, `typecheck`, build de producción y
`git diff --check` correctos.

### ISS-89: paginacion de listados desde SQL

- Los listados de catalogos, grupo, memorias, personal, produccion, proyectos,
  recursos, transferencia, usuarios, UCT y borradores cuentan y limitan filas
  en la base de datos antes de serializar; los snapshots e historiales siguen
  el mismo criterio.
- La busqueda global cuenta y ordena candidatos entre entidades en SQL y carga
  solo los registros de la pagina. Se conserva el alcance UCT y los permisos.
- Se retiro el hook global de paginacion en memoria. Los GET sin parametros
  conservan sus respuestas anteriores; las rutas paginadas mantienen los
  metadatos y el marcador `legacy-list` donde ya formaba parte del contrato.

Validaciones: aceptacion visual y funcional del usuario, 597 pruebas backend,
pruebas dirigidas de busqueda, auditoria, historial y recursos correctas; `git
diff --check` sin errores de contenido.

### ISS-83: historial y administracion de adoptantes

- Gestion de Catalogos permite crear, editar y dar de baja adoptantes, con
  historial de nombre y estado, permisos y alcance por UCT.
- El detalle de transferencia muestra el historial propio de cada adoptante
  vinculado, separado de los eventos de vinculacion, con tres cambios por pagina.
- La baja logica se bloquea mientras exista un vinculo vigente con una
  transferencia activa; el alta inline en transferencias sigue disponible.

Validaciones: aceptacion visual y funcional del usuario, 37 pruebas backend
dirigidas, 191 pruebas frontend, `typecheck` y build de produccion correctos.

### ISS-88: títulos más visibles en las tarjetas de detalle

- Las etiquetas de datos y los encabezados de tarjetas de los detalles usan mayor
  peso y contraste en los módulos de grupo, informes, memorias, personal,
  producción, proyectos, recursos y transferencia.
- Se conservaron la disposición, los textos, las acciones y los contratos.

Validaciones: aceptación visual y funcional del usuario, 191 pruebas frontend,
`typecheck`, build de producción y `git diff --check` correctos.

### ISS-85: informes por período y cierre explícito de proyectos

- Investigadores, Proyectos y UCT tienen informes manuales ligados a una Memoria,
  con copias históricas de los registros vinculados, auditoría e historial. El
  acceso a las vistas y los endpoints queda limitado a GESTOR.
- Los listados de informes muestran el período y permiten desplegar las copias
  vinculadas de investigadores y proyectos. El detalle conserva el estilo del
  sistema y el selector de vínculos permite navegar con teclado.
- Un informe PID habilita el cierre explícito del proyecto solo cuando la
  Memoria contiene la fecha elegida. Registrar un informe o vencer la fecha
  prevista no cierra el proyecto. El detalle de la prórroga distingue el fin
  vigente y muestra la Decisión de Prorrogación con autor y fecha.

Validaciones: 48 pruebas backend dirigidas, 12 frontend dirigidas, typecheck,
build de producción y healthcheck local correctos; aceptación del usuario.

### ISS-86: listado de Memorias por período y versión

- El home muestra una fila por Memoria y agrupa sus versiones en paneles
  independientes; se pueden mantener varios abiertos a la vez.
- La tabla, los filtros, los estados de consulta, la baja individual y la
  paginación de nueve Memorias siguen las convenciones visuales del sistema.
- Las versiones se consultan al expandir; las acciones respetan su estado y
  los permisos del usuario. El contrato backend no cambia.

Validaciones: aceptación funcional del usuario, 191 pruebas frontend,
`typecheck`, build de producción y `git diff --check` correctos.

### ISS-82: administracion de autores bibliograficos

- Catalogos permite editar y dar de baja autores de documentacion bibliografica y consultar su historial propio, con tres eventos por pagina. Documentacion conserva el alta de autores.
- Los cambios de nombre y estado se atribuyen al autor; las vinculaciones y desvinculaciones quedan en el historial de Documentacion. El nombre corregido se refleja en documentaciones activas y las versiones cerradas de Memorias conservan su captura.
- La baja logica se bloquea solo cuando existen documentaciones activas vinculadas. Se incorporo la migracion de auditoria de autores y se corrigio el error 500 de listado y alta aplicandola en desarrollo.

Validaciones: aceptacion funcional del usuario, 7 pruebas backend de autores, 1 de migracion, 5 de historial de Documentacion y Memorias, 21 de aislamiento UCT, 188 pruebas frontend, `typecheck` y build de produccion en contenedor correctos.

### ISS-81: cambios y periodos de directivos

- El historial del grupo separa cambios de nombre y de mandatos de los periodos
  directivos. Los nuevos eventos muestran autor y fecha, respetan la UCT y se
  consultan de a tres; los periodos anteriores no reciben auditoria retroactiva.
- El formulario aclara cuando un nombre esta pendiente y ofrece guardar la UCT
  junto a las tarjetas. Finalizar cargo usa una X y el exito identifica el equipo
  directivo cuando corresponde.

Validaciones: aceptacion funcional del usuario, 16 pruebas backend del modulo,
188 pruebas frontend, `typecheck` y build de produccion correctos.

### ISS-80: historial de campos y rutas de UCT

- La edición de la UCT registra diferencias reales de sus campos institucionales
  con valor anterior, nuevo, autor y fecha. El historial exige permisos de
  lectura y respeta el alcance de la UCT asignada.
- El menú `Historial Grupo` permite consultar cambios del grupo o períodos
  directivos, con tres elementos por página. La edición usa `/uct/editar` y
  muestra `Editar UCT` en el breadcrumb; `/uct/nueva` queda para el alta.

Validaciones: aceptación funcional del usuario, 28 pruebas backend focalizadas,
188 pruebas frontend, `typecheck`, build de producción y `git diff --check`.

### ISS-84: respuesta inicial de los módulos

- Se reutilizan los criterios de lectura por UCT para reducir el tiempo de
  preparación de consultas sin cambiar el aislamiento de datos.
- Memorias cuenta los elementos de versiones cerradas con una agregación en
  base de datos. La consulta de becas activas por año vuelve a responder.

Validaciones: 548 pruebas backend correctas desde Windows, lecturas de los
módulos con respuestas válidas y aceptación manual del rendimiento.

### security-multitenancy-uct: aislamiento por UCT asignada

- ADMIN, GESTOR y LECTURA consumen y modifican, segun su rol, solo los datos
  de su UCT activa. Las pertenencias se almacenan con auditoria y las altas de
  usuarios heredan la UCT del administrador.
- Listas, detalles, relaciones, historiales, busqueda, dashboard, saldos y
  exportaciones aplican el mismo alcance. Memorias y snapshots validan la UCT
  de la memoria y de cada dato de origen; se omite el contexto historico de
  otra UCT.
- El frontend limpia la cache al cambiar o perder la sesion. La seleccion de
  varias UCT queda para una entrega posterior.

Validaciones: 120 pruebas backend focalizadas y 38 pruebas adicionales de
autenticacion y aislamiento, migraciones upgrade/downgrade en SQLite,
`typecheck`, build frontend y validacion manual aceptada por el usuario.

### ISS-74: errores asociados a controles fuera de Field

- La edición de usuarios asocia etiquetas y errores a nombre, correo y rol.
- El programa de actividades de Memorias asocia el error de descripción al
  campo, sin atribuirle los fallos generales de guardado.
- La casilla de becas en Becario anuncia su error global y expone el estado
  inválido cuando corresponde.
- Mi Perfil asocia los errores de nombre y correo, enfoca el primer campo
  inválido y presenta el rol como dato de solo lectura accesible con Tab.
- Los avisos de éxito al crear o editar un becario se anuncian mediante una
  región de estado accesible.

Validaciones: 188 pruebas frontend, `typecheck`, build de producción y
`git diff --check` correctos. Comprobación manual con NVDA aceptada por el
usuario el 2026-09-30.

### ISS-78: bloqueo temporal de login

- Tres fallos consecutivos por nombre de usuario bloquean nuevos intentos durante
  15 minutos, incluso con la contraseña correcta. El contador persiste en la base
  de datos y se reinicia al vencer el bloqueo o tras un acceso válido.
- El mismo contrato de error se aplica a nombres existentes e inexistentes. El
  login muestra el tiempo de espera en una alerta accesible y la API incluye
  `Retry-After`. El cambio de contraseña autenticado no elimina el bloqueo.

Validaciones: 41 pruebas backend de Auth, 188 pruebas frontend, `typecheck`,
build de producción y `git diff --check` correctos.

### ISS-79: paleta institucional en KPI y graficos

- Los cinco KPI y las cuatro tarjetas de graficos del dashboard usan la paleta
  `#F86262`, `#EE63F8`, `#F962C2`, `#A162F9` y `#8E90FB` como acentos.
- Los KPI dejan de usar gradientes; las barras y los sectores comparten la
  paleta y conservan etiquetas, valores, filtros y navegacion.

Validaciones: aprobacion visual del usuario, 188 pruebas frontend, 2 pruebas
backend del dashboard, `typecheck`, build de produccion y `git diff --check`
correctos.

### ISS-77: duracion y prorrogas de proyectos

- Los proyectos nuevos o con fechas editadas requieren un periodo inicial
  inclusivo de 12 a 36 meses. Los registros existentes se conservan y se
  validan al cambiar sus fechas.
- Una accion protegida registra una unica prorroga de 12 meses con
  justificacion, autor, fecha de decision e historial. Detalle y listado
  distinguen el fin original, el fin prorrogado y la fecha final vigente.
- El cierre manual tiene un endpoint propio; editar solo `fecha_fin` ya no
  cierra el proyecto. La migracion conserva el fin original existente.

Validaciones: aprobacion visual y funcional del usuario, 31 pruebas backend
focalizadas, 188 pruebas frontend, `typecheck`, build de produccion y
`git diff --check` correctos.

### ISS-76: identidad documental en Personal

- Personal, Becario e Investigador requieren DNI y CUIL en las altas, validan
  formato, coincidencia con el DNI y digito verificador, y muestran errores de
  campo al editar o crear.
- La identidad compartida asegura unicidad de DNI y CUIL entre las tres
  variantes, conserva historiales y permite completar registros heredados.
- Se aplico la migracion de desarrollo y se regeneraron datos ficticios sin
  eliminar registros existentes.

Validaciones: aprobacion visual y funcional del usuario, 49 pruebas backend del
modulo, 186 pruebas frontend, `typecheck`, build de produccion y
`git diff --check` correctos.

### ISS-75: paginacion de Gestion de Catalogos

- Los valores de catalogos, incluida la seccion Becas, muestran controles de
  paginacion con el mismo aspecto compacto que las tablas del sistema.
- Se conservan nueve valores por pagina, la pagina activa y los extremos
  deshabilitados.

Validaciones: aprobacion visual y funcional del usuario, 184 pruebas frontend,
`typecheck`, build de produccion y `git diff --check` correctos.

### ISS-73: errores de campo descritos para lectores de pantalla

- Los controles de `Field`, incluidos los grupos compuestos, referencian sus
  errores visibles sin perder las ayudas existentes.
- El nombre del adoptante creado desde Transferencias vincula su error inline
  al input correspondiente.

Validaciones: aprobación funcional del usuario con NVDA, 184 pruebas frontend,
`typecheck` y build de producción con cargador `runner` correctos.

### ISS-70: indicadores de carga y exportación

- Las vistas, tablas y secciones con datos diferidos muestran skeletons con
  etiquetas accesibles durante la carga.
- La exportación Excel de Memorias informa generación, recepción e inicio de
  descarga, bloquea solicitudes duplicadas y permite reintentar tras un error.

Validaciones: aceptación visual y funcional del usuario, incluida una
exportación fallida, 184 pruebas frontend, `typecheck` y build de producción
con cargador `runner` correctos.

### ISS-71: recorrido de teclado en diálogos y listados

- Los diálogos modales contienen el foco, permiten Escape cuando la operación
  es cancelable y devuelven el foco al disparador al cerrarse.
- El menú conserva el foco al abrir submenús. Las tablas ofrecen una sola parada
  para encabezados ordenables y acceso directo al primer resultado.

Validaciones: aceptación funcional del usuario, 184 pruebas frontend,
`typecheck` y build de producción con cargador `runner` correctos.

### ISS-72: acceso directo al contenido

- Se agregó un enlace visible al recibir foco para ir al contenido principal
  desde el inicio del recorrido de teclado de las rutas autenticadas.

Validaciones: aceptación funcional del usuario, 183 pruebas frontend,
`typecheck` y build de producción con cargador `runner` correctos.

### ISS-69: limpieza de frontend

- Se eliminaron vistas, hooks, services, utilidades, componentes y datos mock
  sin consumidores, incluidos los restos de planificaciones fuera del router.
- Se conservaron las rutas activas y los contratos aún utilizados.

Validaciones: aceptación visual y funcional del usuario, 183 pruebas frontend,
`typecheck`, build de producción con cargador `runner` y `git diff --check`
correctos.

### ISS-68: rutas de edición coherentes

- Los proyectos usan `/proyectos/:id/editar`; la ruta anterior redirige sin
  perder búsqueda ni estado. Los enlaces del home, detalle y borradores se
  alinearon con la ruta canónica. Personal usa su ruta canónica desde el detalle.

Validaciones: aceptación funcional del usuario, 183 pruebas frontend,
8 pruebas backend de borradores, `typecheck` y build de producción con cargador
`runner` correctos.

### ISS-67: foco visible consistente

- Los controles interactivos presentan un contorno uniforme al navegar con
  teclado, incluido el modo de colores forzados.

Validaciones: aceptación visual y funcional del usuario, 183 pruebas frontend,
`typecheck` y build de producción con cargador `runner` correctos.

### ISS-66: listas relacionadas en formularios

- Los selectores de participantes, autores, adoptantes y personal de proyectos
  muestran hasta cinco resultados por página con búsqueda y navegación
  Anterior/Siguiente. Las colecciones seleccionadas también se limitan a cinco
  elementos visibles por página.
- Proyectos presenta candidatos en tarjetas con acción Añadir y conserva las
  relaciones pendientes al buscar o cambiar de página. Las becas vinculadas
  admiten búsqueda y paginación sin alterar el índice de edición de cada fila.
- Los cambios de relaciones continúan consolidándose al guardar el formulario.
  La paginación de homes e historiales permanece en nueve y tres elementos,
  respectivamente. No cambió el contrato del backend.

Validaciones: aceptación visual y funcional del usuario, 183 pruebas frontend,
`typecheck`, build de producción y `git diff --check` correctos.

### ISS-65: salida de formularios con borradores

- «Volver» y la navegación por rutas ya no muestran la confirmación de borrador
  cuando el formulario de alta o edición no tiene cambios reales.
- Revertir los campos al valor inicial, o al borrador recuperado, elimina la
  confirmación. Guardar y descartar el borrador conservan sus acciones.

Validaciones: aceptación visual y funcional del usuario, 181 pruebas frontend,
`typecheck`, build de producción y `git diff --check` correctos. No hubo cambios
de backend.

### Movimientos: fuente de egresos y equipamiento (ISS-51, ISS-63 e ISS-64)

- La fuente de financiamiento ahora es obligatoria para ingresos y egresos. El backend calcula el saldo de cada fuente como ingresos activos menos egresos activos y rechaza altas, ediciones o bajas que produzcan un saldo negativo.
- El home presenta ingresos, egresos y saldo disponible por fuente, con selector de fuente y hasta tres tarjetas por página. El historial conserva nueve filas por página y separa número de movimiento, tipo y fuente en columnas.
- Un egreso puede vincular un equipamiento activo de la misma UCT. Al seleccionarlo se toma su importe y se propone la categoría Capital, editable por el usuario. La relación es única, el importe del egreso queda histórico y el vínculo se registra en detalle, auditoría y snapshots.
- La migración `f4b8c6d2e9a1` descarta movimientos y snapshots ficticios previos, incorpora la fuente obligatoria y el vínculo de equipamiento. La semilla de pruebas los regenera con el nuevo esquema; la migración se aplicó en PostgreSQL de desarrollo.
- Se actualizó la expectativa de la búsqueda global a 23 módulos indexados, acorde con la unificación previa de movimientos.

Validaciones: aceptación visual y funcional del usuario, 44 pruebas backend focalizadas de Recursos, prueba de migración SQLite, 21 pruebas focalizadas de Búsqueda y logging, 178 pruebas frontend, `typecheck` y build correctos. La suite backend completa encontró un bloqueo de archivo SQLite en la prueba concurrente de autenticación sobre Windows.

### Movimientos financieros (ISS-41 a ISS-56, ISS-59 e ISS-60)

- Los ingresos y egresos usan un movimiento único con monto decimal, numeración por UCT, fuente o categoría condicional, auditoría y baja lógica. El saldo se deriva de movimientos activos y el backend rechaza operaciones que lo vuelvan negativo.
- La sección `/movimientos` presenta el saldo disponible y un historial en tabla de 9 filas por página, con filtros, detalle, formulario e historial de cambios de 3 eventos por página. Un egreso superior al saldo abre un diálogo modal enfocado con el saldo actualizado.
- API, Memorias, exportaciones, dashboard y búsqueda consumen el nuevo modelo. La semilla de pruebas usa la UCT activa para que los movimientos recuperados por Búsqueda aparezcan en el historial financiero. Los datos ficticios del entorno se alinearon con esa UCT.
- La portada pública dejó de mostrar el breadcrumb `Portada`. Login, registro y home autenticado conservan sus rutas de navegación.
- La moneda USD y la cotización manual histórica quedan para una etapa posterior con especificación adicional. Los modelos y tablas antiguos siguen internamente sin rutas públicas; no se realizó migración histórica controlada porque los datos existentes son ficticios.

Validaciones: aceptación visual y funcional del usuario, 178 pruebas frontend,
23 pruebas backend focalizadas, `typecheck`, build de producción y
`git diff --check` correctos. La suite backend completa tuvo un fallo ajeno al
módulo por bloqueo de un archivo SQLite en una prueba de autenticación en Windows.

### ISS-41: breadcrumbs en todas las rutas del frontend

- Se incorporó una ruta de navegación accesible en login, registro y pantallas
  autenticadas, incluidos listados, altas, detalles, ediciones y versiones.
- Los enlaces llevan a páginas reales y conservan el contexto de navegación de
  Memorias sin repetir mensajes de éxito. Las etiquetas `Detalle` y `Versión`
  omiten el ID del registro; la URL mantiene el identificador necesario.
- El login usa el breadcrumb para volver a la portada. El registro lo mantiene
  visible en sus estados de carga, error y configuración.

Validaciones: aceptación visual y funcional del usuario, 172 pruebas frontend,
`typecheck`, build de producción aislado y `git diff --check` correctos. No hubo
cambios de backend.

### ISS-40: estandarizar Transferencias y Adoptantes

- El home adoptó la tabla compartida con búsqueda, filtros y scrollbar del
  patrón de Trabajos de Reunión, 9 registros por página, acciones individuales
  e historial diferido de 3 eventos.
- El backend asigna el número de transferencia automáticamente y conserva la
  secuencia de los registros dados de baja. El formulario ya no solicita ese
  número.
- El formulario permite seleccionar, crear y quitar adoptantes en una grilla.
  Los cambios se guardan con la transferencia en una sola transacción; Enter en
  el nombre nuevo lo añade a la grilla sin enviar el formulario.
- El detalle y el historial presentan los vínculos y sus cambios con nombres
  legibles. El flujo utiliza el backend real para mantener coherentes catálogo,
  transferencia y mensajes de éxito.

Validaciones: aceptación visual y funcional del usuario, 167 pruebas frontend,
485 pruebas backend en Docker, `typecheck`, build de producción y
`git diff --check` correctos.

### ISS-39: estandarizar Documentación y Biblioteca

- El home adoptó la tabla compartida con búsqueda, filtros, orden, 9 registros
  por página, acciones individuales e historial diferido de 3 eventos.
- El formulario incorporó búsqueda de autores por nombre o iniciales, selección
  local de altas y bajas y creación diferida de autores nuevos. Conserva el envío
  de diferencias reales y la navegación con mensaje de éxito.
- El detalle y el home presentan cambios de campos y eventos de autores con
  nombres legibles. El backend registra vinculaciones y desvinculaciones con
  usuario y snapshot del nombre.
- Se corrigió la codificación de los textos de la pantalla y se unificó el botón
  «Añadir» del selector.

Validaciones: aceptación visual y funcional del usuario, 164 pruebas frontend,
9 pruebas backend focalizadas, `typecheck`, build de producción y
`git diff --check` correctos.

### ISS-38: estandarizar visualmente Equipamientos

- El home reemplazó las tarjetas, la selección masiva y el panel lateral por la
  tabla compartida con 9 filas, búsqueda y filtros horizontales de estado, año y
  rango de monto.
- Cada fila abre el detalle y ofrece acciones individuales según el estado y los
  permisos existentes. La baja conserva confirmación y feedback visible.
- El historial se carga al expandir una fila, muestra hasta 3 cambios por página
  y ofrece estados de carga, vacío y error con reintento. La actualización del
  listado conserva las filas visibles.
- El formulario, el detalle y el contrato backend mantienen sus reglas vigentes.

Validaciones: aceptación visual y funcional del usuario, 161 pruebas frontend,
`typecheck`, build de producción y `git diff --check` correctos. Las pruebas
backend no se ejecutaron porque el Python local no tiene `pytest` instalado;
no hubo cambios de backend.

### ISS-37: separar y estandarizar los tipos de Visitas

- Se incorporó el catálogo independiente Tipo de visita con los valores de
  prueba Académica e Intercambio, endpoints protegidos, auditoría, historial y
  baja lógica. Visitas dejó de depender de Tipo de reunión científica sin
  modificar los demás tipos de encuentro.
- El modelo vigente, los snapshots de Memorias, las validaciones, la API y el
  dataset de testing referencian el catálogo propio. Procedencia continúa
  representando el origen de la visita.
- El formulario diferencia tipo y procedencia, recupera errores del catálogo y
  conserva el envío exclusivo de diferencias, mensajes y navegación aprobados.
- El home adoptó la tabla compartida con 9 filas, búsqueda, filtros horizontales,
  acciones individuales e historial diferido paginado de a 3 eventos con el
  formato común de los módulos estandarizados.
- Home y detalle presentan tipos, fechas y relaciones mediante etiquetas
  legibles, omitiendo acciones técnicas, inicializaciones, valores equivalentes,
  IDs internos y JSON.
- La revisión `d8f3a6c1b5e2` actualiza las claves foráneas y elimina los datos de
  prueba anteriores; el seed regenera 13 visitas asociadas al catálogo propio.

Validaciones: aceptación visual y funcional del usuario, 37 pruebas backend
focalizadas, 161 pruebas frontend, `typecheck`, build de producción y
`git diff --check` correctos.

### ISS-35: admitir becarios en Participaciones relevantes

- Participaciones relevantes admite como participante a un investigador o un
  becario, con identidad inequivoca por rol e ID, validaciones de actividad,
  claves foraneas y restriccion de integridad en registros y snapshots.
- La API, auditoria, filtros, deteccion de duplicados, busqueda global,
  exportacion XLSX y Memorias contemplan ambas categorias y presentan nombres
  legibles sin exponer identificadores internos.
- El formulario reemplazo el selector extenso por busqueda por nombre, apellido
  o iniciales, filtro de categoria, resultados de a 9 y una tarjeta de seleccion.
- El home adopto la tabla compartida con 9 filas, filtros horizontales, acciones
  individuales e historial diferido paginado de a 3 eventos. El detalle conserva
  auditoria, historial, permisos y navegacion aprobada.
- La revision `c35e8a1b7d42` actualizo el esquema y el dataset ficticio se
  regenero despues de retirar participaciones de prueba huerfanas.

Validaciones: aceptacion visual y funcional del usuario, 10 pruebas backend
focalizadas de Participaciones relevantes, 75 pruebas backend relacionadas, 156
pruebas frontend, `typecheck`, build de produccion y `git diff --check`
correctos.

### ISS-34: estandarizar Artículos de divulgación

- Artículos de divulgación reemplazó las tarjetas, la selección masiva y el
  panel lateral por la tabla compartida con 9 filas, búsqueda y filtros
  horizontales por estado, UCT y año.
- Cada fila conserva la navegación al detalle y ofrece acciones individuales de
  edición y baja lógica según el estado y los permisos vigentes.
- El historial se carga al expandir, pagina de a 3 eventos y distingue carga,
  error recuperable y vacío. Home y detalle presentan fechas y UCT con etiquetas
  legibles, sin acciones técnicas, inicializaciones, IDs ni JSON.
- El formulario conserva el envío exclusivo de diferencias, vincula los errores
  del contrato a sus controles y evita mensajes duplicados.
- Se verificó y cubrió mediante regresión que el título de un artículo puede
  repetirse y no constituye una restricción de unicidad.

Validaciones: aceptación visual y funcional del usuario, prueba focalizada 5/5,
150 pruebas frontend, `typecheck`, build de producción, 5 pruebas backend de
Artículos de divulgación y `git diff --check` correctos.

### ISS-33: estandarizar Distinciones recibidas con la grilla común

- Distinciones recibidas reemplazó las tarjetas, la selección masiva y el panel
  lateral por la tabla compartida con 9 filas, búsqueda y filtros horizontales
  por estado, proyecto y año.
- Cada fila conserva la navegación al detalle y ofrece acciones individuales de
  edición y baja lógica según el estado y los permisos vigentes.
- El historial se carga al expandir, pagina de a 3 eventos y distingue carga,
  error recuperable y vacío. Home y detalle presentan fechas y proyectos con
  etiquetas legibles, sin acciones técnicas, inicializaciones, IDs ni JSON.
- El formulario conserva el envío exclusivo de diferencias y muestra cada error
  de validación una sola vez junto al control correspondiente.

Validaciones: aceptación visual y funcional del usuario, prueba focalizada 5/5,
145 pruebas frontend, `typecheck`, build de producción, 28 pruebas backend
focalizadas y `git diff --check` correctos.

### ISS-32: separar el contrato y estandarizar Trabajos en revistas

- Se incorporó el catálogo independiente Tipo de revista con los valores de
  prueba Nacional e Internacional, endpoints protegidos, auditoría e historial.
  Trabajos en revistas dejó de depender de Tipo de reunión científica.
- El modelo, API, snapshots, búsqueda, exportaciones y frontend reemplazaron la
  fecha genérica por `fecha_publicacion`, presentada como Fecha de publicación.
- Las altas y ediciones requieren al menos un autor. Una petición inválida no
  persiste el trabajo, por lo que el reintento corregido no produce un falso
  conflicto de título duplicado.
- El home adoptó la tabla compartida con 9 filas, búsqueda, filtros, acciones
  individuales e historial diferido de 3 eventos. Home y detalle presentan tipos,
  fechas y eventos de autores con etiquetas legibles.
- La revisión `b4e7c1d9a320` actualiza el esquema y el dataset de testing se
  regeneró con las nuevas clasificaciones.

Validaciones: aceptación visual y funcional del usuario, 50 pruebas backend
focalizadas, 140 pruebas frontend, `typecheck`, build de producción y
`git diff --check` correctos.

### ISS-31: presentar relaciones legibles en el historial de Proyectos

- Home y detalle muestran vinculaciones y desvinculaciones de investigadores y
  becarios como acciones directas acompanadas por el nombre correspondiente, sin
  etiquetas de valor anterior/nuevo, IDs ni JSON.
- Las asignaciones de `coordinador_id` se presentan como `Coordinador asignado`
  seguido del nombre del investigador. Los cambios ordinarios conservan su
  comparacion anterior/nuevo.
- Se incorporo una opcion optativa en la tarjeta compartida de historial para que
  cada modulo presente eventos de accion sin modificar a los demas consumidores.

Validaciones: aceptacion funcional del usuario, prueba focalizada 2/2, 135
pruebas frontend, `typecheck`, build de produccion y `git diff --check` correctos.

### ISS-30: estandarizar Trabajos en reuniones con la grilla comun

- Trabajos en reuniones reemplazo las tarjetas, seleccion masiva y panel lateral
  por la tabla compartida con 9 filas, busqueda, filtros, navegacion y acciones
  por registro condicionadas por estado y permisos.
- La barra horizontal alinea chips y selectores y reutiliza el scrollbar compacto
  local del patron aprobado.
- El historial se carga al expandir, pagina de a 3 eventos y distingue carga,
  error recuperable y vacio. Omite acciones tecnicas, inicializaciones y valores
  equivalentes, y normaliza objetos para evitar representaciones invalidas.
- Las vinculaciones y desvinculaciones de autores muestran la accion, el nombre y
  la categoria directamente, sin pares de valor anterior/nuevo.
- Se agrego `frontend/CONVENCIONES_PANTALLAS.md` como contrato transversal para
  adaptar homes, formularios, detalles e historiales de los modulos restantes.

Validaciones: aceptacion visual y funcional del usuario, prueba focalizada 5/5,
135 pruebas frontend, `typecheck`, build de produccion, 46 pruebas backend
focalizadas y `git diff --check` correctos.

### ISS-28: estandarizar Registros de propiedad con la grilla comun

- Registros de propiedad reemplazo las tarjetas, la seleccion masiva y el panel
  lateral por la tabla compartida, con 9 filas por pagina, busqueda, chips de
  estado, filtros de tipo y fecha, navegacion y acciones por registro segun
  permisos y estado.
- La barra de filtros mantiene el espaciado y desplazamiento horizontal del
  patron de Proyectos cuando el ancho disponible no alcanza.
- Cada fila permite expandir un historial diferido de 3 eventos por pagina. Home
  y detalle omiten acciones, inicializaciones y valores sin cambios.
- Se verifico el contrato plano de `tipo_registro` y `grupo`; la presentacion
  defensiva de valores estructurados evita mostrar `[object Object]` en columnas,
  filtros, etiquetas e historial.
- El alta no genera cambios de inicializacion y una actualizacion sin diferencias
  no persiste auditoria. Se agregaron regresiones backend para ambas garantias.

Validaciones: aceptacion visual y funcional del usuario, 130 pruebas frontend,
`typecheck`, build de produccion, 6 pruebas backend de Registros de propiedad y
`git diff --check` correctos.

### ISS-27: estandarizar Actividades en Docencia con la grilla comun

- Actividades en Docencia reemplazo las tarjetas y la seleccion masiva por la
  tabla compartida de Personal y Proyectos, con 9 filas por pagina, busqueda,
  filtros, ordenamiento, navegacion desde la fila y acciones por registro segun
  permisos y estado.
- Rol y grado academico se normalizan desde el contrato `{ id, nombre }`; los
  filtros usan un desplazamiento horizontal compacto y mantienen los chips
  centrados.
- El historial diferido muestra 3 eventos por pagina y, al igual que la tarjeta
  del detalle, permanece informativo. El grado inicial ya no se presenta como un
  cambio y los cambios reales muestran los nombres anterior y nuevo.
- Editar y eliminar conservaron sus contratos. PUT y DELETE respondieron 200 en
  pruebas, y la eliminacion mantiene baja logica y confirmacion transaccional.

Validaciones: aceptacion visual del usuario, 125 pruebas frontend, `typecheck`,
build de produccion, 38 pruebas backend de Produccion/Docencia y
`git diff --check` correctos.

### ISS-26: reformular Proyectos con tabla e historial legible

- Proyectos reemplazó el listado anterior por la tabla compartida de 9 filas, con
  búsqueda, filtros, ordenamiento, acciones por registro e historial diferido de
  3 eventos por página. El formulario conserva la nomenclatura y el icono de
  remoción utilizados en Personal.
- El listado backend admite paginación, filtros y ordenamiento sin romper el
  contrato plano anterior. Edición y cierre bloquean exclusivamente la fila del
  proyecto, corrigiendo el error de PostgreSQL causado por `FOR UPDATE` sobre
  relaciones opcionales cargadas mediante `LEFT JOIN`.
- La composición inicial del personal ya no se registra como un cambio. Las
  vinculaciones y desvinculaciones posteriores conservan y muestran el nombre de
  la persona sin exponer JSON ni identificadores internos.
- El usuario validó manualmente la estructura visual, las acciones de edición,
  cierre y el historial sin vinculaciones iniciales. La comprobación visual final
  permaneció a cargo del usuario.

Validaciones: 31 pruebas backend de Proyectos, 119 pruebas frontend, `typecheck`,
build de producción, consulta real de bloqueo en PostgreSQL y `git diff --check`
correctos.

### ISS-25: reformular Personal con una tabla reutilizable

- Se incorporo `Table.tsx`, una tabla generica, controlada, responsive y
  accesible con toolbar, busqueda, chips, orden, expansion, estados uniformes y
  paginacion. Personal reemplazo las tarjetas por una tabla de 9 filas con
  navegacion desde la fila, acciones con iconos e historial diferido de 3 eventos.
- El listado canonico `GET /api/v1/personal/all` pagina, filtra, busca y ordena en
  base de datos. Sin parametros de paginacion conserva el contrato plano anterior;
  el contrato paginado devuelve filas normalizadas y metadata estandar.
- El alta muestra las tres clases de registro de forma visible y la edicion
  mantiene la clase informativa. Categoria UTN y Programa de Incentivos son
  opcionales, admiten eliminacion con `null` y registran los cambios en auditoria.
- Los formularios conservan el envio exclusivo de diferencias y ahora vuelven
  directamente desde edicion cuando no existen cambios reales; la confirmacion
  de borrador permanece para modificaciones pendientes.
- El usuario valido busqueda, filtros, paginacion suavizada, acciones, navegacion
  por fila, historial y salida de formularios sin cambios. El manual de usuario
  permanece fuera del alcance de esta etapa.

Validaciones: 32 pruebas backend de Personal, 117 pruebas frontend, `typecheck`,
build de produccion y `git diff --check` correctos. Se revisaron permisos,
estados accesibles, foco, responsive y reduccion de movimiento.

### ISS-01: simplificar la gestion de Catalogos

- Catalogos muestra un selector de tipo y una grilla compacta de valores; retiro
  filtros por grupo/etiqueta, contadores y advertencias repetidas.
- Cada fila consulta su historial al abrir la accion correspondiente y lo pagina
  de a 3; el listado conserva 9 valores por pagina y distingue Vigente/Inactivo.
- Altas y cambios de nombre exigen al menos una letra Unicode en frontend y en
  los servicios backend de los catalogos administrados. Se preservan IDs,
  referencias y registros anteriores; se actualizaron los README tecnicos.

Validaciones: 112 pruebas frontend, typecheck, build de produccion, 8 pruebas
backend focalizadas y suite backend completa de 457 pruebas con 1 incidencia
preexistente de limpieza SQLite en Windows (`test_doble_refresh_concurrente_solo_rota_una_vez`).
El usuario valido la interfaz y las acciones de crear, editar y eliminar Tipos de Personal.
El manual de usuario queda a cargo del usuario al finalizar todos los modulos.

### ISS-19: contextualizar errores de formularios y validar nombres de personas

- Los formularios de Auth, Grupo, Personal, Produccion, Proyectos, Recursos,
  Transferencia y Memorias muestran errores por campo mediante `details.fields`
  y mensajes generales accionables, sin clasificar campos por texto libre.
- Los nombres y apellidos de personas, directivos, autores y adoptantes aceptan
  letras Unicode y espacios; frontend y backend rechazan cifras y signos.
- Auth renueva credenciales tras cambiar la contrasena. La creacion y asignacion
  de directivos usa una transaccion; Erogaciones permite corregir fechas y
  editar otros campos con cambios parciales.
- Se corrigio la edicion de segmentos y separadores del calendario. El borrador
  de Erogaciones y la confirmacion de salida se consolidaron en ISS-22.

Validaciones: 114 pruebas frontend, `typecheck`, build de produccion y pruebas
backend focalizadas; el usuario confirmo los flujos manuales de nombres,
sesion, fechas, erogaciones y formularios. La prueba de rollback de directivos
paso en PostgreSQL. La suite backend completa se ejecuto en Docker; tres
pruebas de despliegue requieren archivos de la raiz que no se montan en el
contenedor y pasan desde el host.

### ISS-22: persistir borradores de formularios en backend

- Los formularios principales guardan un único borrador por usuario, módulo y
  registro en el servidor, con recuperación, descarte y confirmación al salir.
  La lista identifica los borradores y se actualiza al guardarlos o borrarlos.
- Se retiró el almacenamiento de borradores y adoptantes de `localStorage`.
  El backend limita tamaño y vigencia, rechaza claves sensibles y aísla los
  borradores por usuario y rol.
- El usuario validó los formularios y el listado, incluida Transferencias tras
  corregir su ruta en ISS-24.

Validaciones: 111 pruebas frontend, `typecheck`, build de producción, 7 pruebas
backend de borradores y prueba manual de los módulos. Los borradores vencidos
se eliminan al consultar o guardar; la limpieza periódica de usuarios inactivos
queda como límite operativo.

### ISS-23: unificar la paginación de los listados

- Los 18 listados paginados usan páginas numeradas centradas debajo de los
  resultados; Erogaciones y Planificaciones dejaron de ubicarla al borde inferior.

Validaciones: auditoría de los 18 listados, 111 pruebas frontend, `typecheck`,
build de producción y validación manual de los módulos.

### ISS-24: corregir Participaciones y la carga de Transferencias

- Participaciones presenta el nombre del evento con mayúsculas consistentes en
  home y detalle, sin alterar el valor guardado.
- Transferencias consulta la ruta GET con barra final y evita el 308 que enviaba
  al navegador al nombre interno de Docker. La prueba de contrato cubre la ruta.

Validaciones: 111 pruebas frontend, `typecheck`, build de producción y prueba
manual de Transferencias. El proxy respondió directamente desde backend sin
redirección al usar la ruta corregida.

### ISS-18: ocultar referencias internas en mensajes visibles de la interfaz

- Los errores visibles usan mensajes publicos seguros o un fallback accionable;
  ya no agregan `request_id` ni referencias de seguimiento. Se retiro la opcion
  que podia mostrar esas referencias y la exportacion sin consumidores.
- Se reforzaron las pruebas frente a SQL, identificadores malformados y cuerpos
  desconocidos, y se revisaron los consumidores y la documentacion de frontend.
- El usuario confirmo un POST 400 real de Proyectos: el ID aparecio en la
  cabecera y el log del backend, pero no en la UI. Tambien confirmo un 500
  simulado con mensaje generico en la UI y sin informacion interna.

Validaciones: 104 pruebas frontend, typecheck, build:production (2668 modulos),
git diff --check y 17 pruebas backend focalizadas correctas. El 500 fue
simulado en el navegador y no genero log de backend; la correlacion real se
verifico con el 400. Dos pruebas ajenas de `tests.test_api_responses` siguen
fallando por expectativas antiguas sobre detalles arbitrarios del backend.

### ISS-21: indicar campos obligatorios en todos los formularios

- Se revisaron los formularios de autenticación, catálogos, grupo, memorias,
  personal, producción, proyectos, recursos y transferencia. Los campos que
  impiden guardar sin valor muestran el asterisco rojo existente de `Field`.
- Se marcaron también los campos condicionales de becas, directivos y
  coordinador, y controles con etiqueta propia. Los campos opcionales
  permanecen sin marca. No se cambiaron reglas de validación ni contratos API.
- Se actualizó la documentación de frontend de los módulos afectados. La
  comprobación visual de Proyectos y Documentación fue confirmada por el
  usuario tras reiniciar el contenedor de desarrollo.

Validaciones: 104 pruebas frontend, typecheck, build:production con 2668
módulos, 74 pruebas backend focalizadas y git diff --check correctos. El build
por defecto requirió ejecutarse fuera del sandbox local porque esbuild no podía
leer `vite.config.ts` dentro de él; terminó correctamente.

### ISS-17: permitir presentaciones futuras sin referencias internas

- Los trabajos en reuniones admiten fechas de presentación futuras en altas y
  ediciones para registrar actividades ya programadas; conservan formato civil
  y límite institucional inferior del 01/01/2010.
- El formulario informa explícitamente que acepta presentaciones programadas y
  mantiene los errores seguros y accionables sin mostrar la referencia interna
  de seguimiento.
- Se actualizaron los contratos documentados y las regresiones de frontend y
  backend. La aceptación manual fue confirmada por el usuario.

Validaciones: 4 pruebas backend focalizadas, 103 frontend, typecheck,
build:production con 2668 módulos y git diff --check correctos.

### ISS-16: configurar períodos y snapshots de memorias por UCT

- Cada memoria pertenece a una UCT y admite un rango inclusivo configurable,
  incluso entre años. Se impiden solapamientos dentro de la misma UCT y se
  permite una memoria operativamente activa por UCT.
- ADMIN y GESTOR pueden crear y corregir períodos antes del primer cierre;
  LECTURA conserva consulta y recibe 403 ante mutaciones. La UI incorpora el
  selector de UCT, atajo de año calendario, rangos completos y errores visibles.
- La ruta de `Nueva` usa la misma autorización ADMIN/GESTOR que el home y deja de
  redirigir a gestores autorizados. El detalle muestra `Cerrar memoria` de forma
  explícita; `Seleccionar`, destinado a la baja múltiple, sigue limitado a ADMIN.
- ADMIN y GESTOR pueden pasar la memoria a revisión o cerrarla. El rango no
  provoca un cierre automático: la transición explícita congela los snapshots.
  Reapertura y baja continúan reservadas a ADMIN.
- El historial presenta la sigla de la UCT en lugar de su ID, también para
  asignaciones anteriores que ya habían guardado el identificador técnico.
- El cierre congela entidades según UCT y vigencia histórica, incluido el fin
  funcional de proyectos y las bajas lógicas. Las horas corresponden al valor
  vigente al final del período; si no existe evidencia histórica quedan nulas.
- La sección de elementos conserva el diseño anterior: muestra cantidades y abre
  cada módulo filtrado por los registros incluidos, sin desplegables de datos en
  las tarjetas. Los snapshots continúan disponibles para reglas y exportación.
- Se congelan contexto institucional, autoridades, planificación, fecha de alta
  y campos de cada entidad. UI y Excel leen la versión cerrada sin reconstruirla
  desde datos actuales. Cambios de período, estado y reaperturas quedan auditados.
- Migración reversible `e16a0b2c4d60` aplicada al PostgreSQL local. Para poder
  ejecutarla se transfirió al usuario de la aplicación la propiedad de las cinco
  tablas afectadas, permiso REFERENCES sobre `grupo_utn` y CREATE en `public`.
- Contratos, permisos, reglas temporales y limitaciones se documentaron en los
  módulos de memorias, grupo, personal, proyectos, producción, recursos y
  transferencia de backend, y en memorias/grupo de frontend.

Validaciones: 25 pruebas backend focalizadas, 119 de Memorias, 101 frontend, typecheck,
build:production, migración upgrade/downgrade temporal y aplicación local.
La suite backend completa ejecutó 416 pruebas: 412 correctas y cuatro incidencias
ajenas ya existentes (dos expectativas obsoletas del filtrado seguro de detalles,
una tilde esperada por Search y un archivo SQLite concurrente retenido en Windows).
`aaferrando` no existe en la base local, por lo que no se asignó ni elevó un rol.
La aceptación visual y el circuito con ese usuario quedan pendientes del usuario.

### ISS-14: agregar un enlace opcional al trabajo

- Congresos/reuniones y revistas permiten crear, editar y quitar un enlace
  HTTP/HTTPS opcional, hasta 2048 caracteres, con DOI mediante URL completa.
  Validaciones frontend/backend y errores asociados al campo; apertura segura
  y accesible desde detalle en pestaña nueva.
- Cambios reales auditados; snapshots conservan el enlace original y exportaciones
  de memoria/grupo lo incluyen sin alterar las columnas de la plantilla.
- Migración reversible d14e8f0a3c51 aplicada a PostgreSQL local de testeo:
  cuatro columnas nullable, 13 trabajos de cada tipo conservados con enlace null.
- Documentados contratos, permisos y validaciones en producción y memorias.

Validaciones: 65 tests backend correctos, tres de enlaces reejecutados tras
validar hosts inválidos, 97 frontend, typecheck, build:production y diff --check.
Upgrade/downgrade y snapshots/Excel inmutables probados en SQLite temporal.
HTTP autenticado 200 y módulos Vite actualizados; backend/frontend reiniciados.
Dos fixtures de snapshots actualizados al campo nuevo tras la primera ejecución.
Build inicial limitado por sandbox; compilación autorizada posterior correcta.
Revisión de navegador a cargo del usuario. No se implementa el plan de ISS-16.


### ISS-13: sustituir Fecha de inicio por Fecha de presentación

- Trabajos en congresos/reuniones y snapshots usan fecha_presentacion.
  Actualizados formulario, detalle, home, historial, filtro anual, búsqueda,
  exportaciones, seed y contratos; revistas mantiene su contrato.
- Compatibilidad temporal de entrada con fecha_inicio; valores contradictorios
  se rechazan sin escritura. Nuevas respuestas/eventos usan el nombre nuevo;
  historial antiguo conservado y presentado con la nueva etiqueta.
- Migración reversible c13d7e9a2b40 aplicada a PostgreSQL local de testing.
  Las trece fechas existentes se conservaron exactamente, sin regenerar datos.
- Pertenencia anual inclusiva por fecha de presentación, verificada para
  31 de diciembre y 1 de enero y en exportación XLSX.

Validaciones: 62 tests backend, 96 frontend, typecheck, build:production y
git diff --check correctos. Migración/downgrade con preservación de valores
probados en SQLite; consultas Docker autenticadas HTTP 200 y módulos Vite
actualizados. Revisión de navegador a cargo del usuario. El primer test XLSX
asumía otro formato de fecha; expectativa ajustada al contrato ISO existente.

### Agregado

#### ISS-12: investigadores y becarios como autores de trabajos

- Autoría común `autores` en congresos y revistas, identificada por rol/id.
  Únicamente investigadores y becarios; Personal y externos se rechazan.
- Backend con integridad referencial, permisos, transacciones atómicas,
  auditoría y snapshots de autores congelados. Formularios con altas/bajas
  locales, guardado consolidado y envío de diferencias reales.
- Buscador por nombre, apellido o iniciales sin tildes, filtro por categoría,
  nueve resultados y Ver más. Añadir requiere un botón explícito; escribir,
  perder foco o Enter en búsqueda no incorpora autores ni envía el formulario.
- Detalles, búsqueda global y exportaciones XLSX muestran autores.
  Corregida la ruta de la plantilla de memorias; contratos documentados.
- Revisiones de esquema aplicadas en PostgreSQL local hasta `b12c8d5e7f90`.
  Seed idempotente: 13 trabajos y 26 asociaciones por tipo. Entorno regenerable
  por decisión del usuario; downgrade estructural sin recuperación de datos.
- Frontend Docker actualizado y módulos servidos comprobados por HTTP.

Validaciones: 95 tests frontend, 18 backend de autores/historial y regresión
previa de 85 tests backend; typecheck, build:production y git diff --check
correctos. SQL PostgreSQL upgrade/downgrade y único head verificados. HTTP real:
consultas 200 y Personal rechazado con 400 sin cambios parciales. Revisión
de navegador a cargo del usuario. Incidencia ajena conservada: un test de
búsqueda espera `numerico` mientras la API devuelve `numérico`.

### Corregido

#### ISS-09: feedback visible durante acciones asincronas

- Button centraliza texto de progreso, icono animado, aria-busy y role=status.
- ConfirmDialog espera promesas, bloquea confirmar/cancelar y sus campos durante
  la operacion, conserva errores seguros y recupera los controles al terminar.
- Integrado en guardados de formularios, altas/ediciones de catalogos,
  eliminaciones y desvinculaciones, reaperturas, exportacion Excel, busqueda
  y reintentos de tipos de personal y candidatos de proyectos.
- UCT mantiene feedback durante todo el guardado consolidado de directivos.
  El cierre de proyectos utiliza la confirmacion comun y la reapertura por
  seleccion informa progreso y evita peticiones concurrentes.
- Documentados diez modulos y el contrato comun. Pruebas de regresion de los
  componentes reales para progreso, bloqueo inmediato, fallo y recuperacion.

Validacion: 85 tests frontend, typecheck, build de produccion y diff check.
Pruebas de navegador a cargo del usuario. Sin cambios de contrato backend.
Preservados cambios previos ajenos.

#### ISS-09: evitar validaciones de fechas duplicadas

- Corregidos 19 campos de fechas en 15 formularios de Recursos, Personal,
  Proyectos, Grupo, Memorias, Transferencia y Produccion.
- Field muestra el error una sola vez; Calendar/DatePicker conserva la ayuda
  de formato o rango. Eliminados los parrafos redundantes de fechas de Docencia.
- Documentadas las convenciones de validacion en los siete modulos afectados.
- Los estados de botones quedan para la siguiente etapa acordada.

Validaciones: 83 tests frontend, typecheck, build de produccion y diff check
correctos. Comprobacion de renderizado Field/Calendar: un solo mensaje y
role=alert en 20 campos con ayuda literal, incluidos los 19 corregidos.
Pruebas de navegador a cargo del usuario; sin cambios de contrato backend.
Se preservan cambios previos ajenos.

#### ISS-08 e ISS-10 — Seguimiento de listado, validaciones y fecha de fin

- Investigador invalida Personal y candidatos de proyectos después de guardar;
  el listado combinado muestra primero las altas recientes entre todos los subtipos.
- Los tres formularios de Personal muestran Guardando con icono animado,
  deshabilitan el envío mientras esperan y recuperan el botón ante errores.
- Personal y Proyectos muestran avisos generales y enfocan el primer campo
  inválido, tanto para validaciones locales como para errores del servidor.
- Se permite el alta completa de proyectos históricos con fecha de fin pasada
  o de hoy, incluyendo coordinador e integrantes; las participaciones iniciales
  conservan el período del proyecto. Las fechas futuras se admiten en alta.
  Los proyectos previamente cerrados siguen requiriendo reapertura para editar.
- Se valida localmente el orden inicio-fin. Documentación de ambos módulos y
  seguimientos integrados en sus archivos de tareas, sin archivos temporales ni logs.

Validaciones: 46 tests backend, 83 frontend, typecheck y build de producción
correctos; git diff --check correcto. Se probaron formularios y React Query real
con caché vigente, errores, foco y prevención de doble envío. Pruebas de navegador
y PostgreSQL a cargo del usuario. Persisten warnings ajenos de Query.get y
ciclos SQLite; se preservaron cambios previos. Sin commits ejecutados.

Incidencia de entorno: un intento de build fue rechazado por acceso de esbuild
al directorio padre; la repetición del comando habitual terminó correctamente,
sin cambiar permisos ni configuración.

#### ISS-10 — Habilitar la asignación del coordinador de un proyecto

- Guardado de campos, coordinador e integrantes en una sola transacción POST/PUT,
  con rollback completo y bloqueo del agregado durante cambios en PostgreSQL.
- Elegibilidad de investigadores activos sin baja lógica; IDs inválidos,
  duplicados y coordinadores externos al proyecto se rechazan con errores por campo.
- Reemplazo del coordinador sin reconstruir participaciones ni alterar fechas;
  conservación visible de asignaciones inactivas y desvinculación con soft delete.
- Formulario con carga, error/reintento, vacío e instrucciones; IDs temporales
  rechazados antes de guardar, payload parcial y ausencia de peticiones sin cambios.
- Auditoría de coordinador y eventos relacionales dentro del guardado, contratos
  documentados y snapshots de memorias preservados.

Validaciones: 42 tests backend, 82 frontend, typecheck, build de producción y
git diff --check correctos. Pruebas de navegador a cargo del usuario. PostgreSQL
y concurrencia pendientes en Docker; SQLite no verifica FOR UPDATE. Warnings
preexistentes de Query.get y ciclos de claves foráneas SQLite; launcher del venv
con ruta antigua, se utilizó Python instalado con sus paquetes. Script y logs
temporales eliminados. Cambios previos preservados; tasks continúa ignorado.
Sin commits ejecutados.

### Documentado

#### ISS-10: cierre aceptado de asignacion del coordinador

- El usuario acepta el cierre definitivo de ISS-10 el 2026-09-13.
- Completados coordinador e integrantes con guardado consolidado, preservacion
  del historial, altas con fecha de fin y feedback de guardado.
- Cierre y aceptacion registrados en tasks/finished/ISS-10.md; sin trabajo de
  implementacion pendiente. Las mejoras globales de botones corresponden al
  seguimiento de ISS-09.

Validaciones registradas: 46 tests backend de Personal/Proyectos; 85 frontend,
typecheck, build de produccion y diff check correctos. Pruebas de navegador
a cargo del usuario. El agente no las declara ejecutadas. Persisten las
incidencias previas documentadas del launcher del venv y warnings SQLite.
tasks/ sigue ignorado por la configuracion existente; no se cambia esa regla.

#### ISS-08 — Unificar la tarea y sus seguimientos

- Se integraron los documentos de alta PTAA, feedback de fechas/sesión y horas
  semanales/catálogo en `tasks/finished/ISS-08.md`, en orden de implementación.
- Se conservaron los cambios, archivos, validaciones, incidencias y estados de
  aceptación manual de cada etapa, junto con la metadata histórica.
- Se retiraron los dos archivos de seguimiento redundantes y se corrigió el
  espacio sobrante de `ISS-04 .md`, ahora `ISS-04.md`, sin cambiar su contenido.
- Se registró en AGENTS.md la convención `ISS-XX.md`: un archivo por issue y
  seguimientos dentro del mismo documento, en orden temporal.

Validaciones: contenido original preservado en la consolidación, contenido de
ISS-04 idéntico por SHA256 y revisión de nombres y referencias. No se modificó
código ni se ejecutaron commits. `tasks/` continúa ignorado por Git según la
configuración existente del usuario.

#### ISS-05 a ISS-16 — Normalizar documentos de tareas pendientes

- Se normalizó `ISS-05.md` con el frontmatter utilizado por las tareas del
  proyecto; su definición y resolución funcional se registran en la entrada
  específica de ISS-05.
- Se dividió el documento agregado de ISS-06 a ISS-16 en once archivos
  independientes, cada uno con metadata, alcance, criterios de aceptación,
  pruebas mínimas y mensaje de commit sugerido.
- ISS-06 a ISS-16 permanecen pendientes; esta reorganización no representa su
  implementación funcional.

Validaciones:

- presencia de un archivo independiente por cada issue entre ISS-06 e ISS-16;
- verificación de identificadores, secciones y listas de tareas por documento;
- codificación UTF-8 y ausencia del archivo agregado original;
- `git diff --check`: correcto.

### Corregido

#### ISS-09 (seguimiento) — Evitar error duplicado de fecha de inicio

- En el formulario de proyecto, el calendario muestra la ayuda de formato y
  `Field` conserva el único mensaje de error de fecha de inicio.
- Se mantiene la validación existente; el usuario detectó la duplicación al
  intentar guardar el formulario vacío durante la prueba manual.

Validaciones: 81 pruebas frontend, `npm run typecheck`,
`npm run build:production` y `git diff --check`: correctos.
Pendiente confirmación visual del usuario.

#### ISS-09 — Implementar mensajes de error accionables (pendiente prueba manual)

- Se conserva el contrato existente de errores y se normalizan mensajes públicos,
  campos inválidos y códigos HTTP de dominio/autenticación.
- Los errores inesperados incluyen una referencia correlacionable con los logs,
  sin reflejar SQL, trazas ni información de conexión.
- Los formularios muestran los errores del servidor junto al control y enfocan
  el primer campo inválido; los campos desconocidos conservan el aviso general.
- Se mantiene la regla alfanumérica del código de proyecto y las validaciones
  existentes. No se incorpora validación en tiempo real.
- Se actualizan los README transversales y de los módulos afectados.

Validaciones: 81 pruebas frontend, typecheck, build de producción y comprobación
de whitespace correctos. 89 pruebas backend de errores, proyectos, autenticación,
cookies, refresh no concurrente, permisos, personal, grupo, recursos, producción,
transferencia, catálogos y logs. Pendiente comprobación manual en navegador.
La prueba concurrente de refresh presenta una incidencia previa de limpieza
SQLite en Windows, ajena a ISS-09; no se declara validada la suite backend completa.
Los cambios se separan en commits por módulo a petición del usuario.
No se crearon herramientas auxiliares en esta continuación.

#### ISS-08 (seguimiento) — Validar horas semanales y usar tipos reales del catálogo

- Horas enteras de 1 a 168 en alta/edición de Personal, Becario e Investigador,
  con validación compartida de dominio frontend/backend y error de campo 400.
- Se unificaron PTAA/Profesional bajo clase Personal; el tipo se selecciona desde
  IDs/nombres reales del catálogo activo, sin filtrar ni asumir "Profesional".
  Se conservan clases especializadas de Becario/Investigador y rutas existentes.
- Catálogo con refresh al montar, feedback de carga/error/vacío y reintento;
  tipos anteriores no disponibles visibles pero deshabilitados en edición.
- Pruebas: 76 frontend (incluido formulario real con catálogo arbitrario y límites),
  31 backend de Personal/auditoría/permisos; TypeScript y build producción correctos.
- Manual Docker pendiente del usuario. No se alteran datos existentes ni historial;
  se exige corregir horas inválidas en el formulario antes de guardar. Advertencias
  ajenas SQLite/launcher venv ya documentadas. Se preservaron textos nuevos del
  calendario y se adecuaron sus tests sin cambiar esos textos.

#### ISS-08 (seguimiento) — Feedback de fechas y renovación de sesión

- Calendar muestra errores de formato y rango, resalta y asocia accesiblemente
  el mensaje al campo; conserva la fecha confirmada al rechazar el valor.
- La renovación mantiene la sesión ante fallos de red, errores HTTP distintos
  de 401 y respuestas malformadas; ofrece diálogo con reintento. Mantiene el
  vencimiento definitivo y la invalidación por 401, sin eludir permisos backend.
- El indicador de renovación se alineó a la derecha de `Continuar sesión`; mantiene
  bloqueo, anuncio accesible y respeto por reducción de movimiento. El usuario
  validó manualmente la aparición del diálogo y la renovación.
- Se documentaron los comportamientos en frontend Personal, auth y módulos.
- Validaciones: 73 tests frontend, TypeScript, build producción y 17 tests backend
  correctos. Test concurrente adicional falla en limpieza SQLite por WinError 32;
  advertencia ajena de ciclos SQLite y launcher venv antiguo sin modificar.
- Prueba visual/Docker pendiente del usuario; no se confirmó el status HTTP del
  deslogueo original. La corrección cubre el fallo temporal identificado en código.

#### ISS-08 — Corregir el alta de personal técnico administrativo y de apoyo

- Se corrigió la ruta del alta: `POST /api/v1/personal` sin barra final;
  la ruta anterior devolvía 404 antes de llegar al service.
- Se protegieron inserción, flush e historial de horas con rollback completo.
- Referencias a tipo y grupo deben existir y estar activas; errores 400
  incluyen campos para feedback local. Las horas requieren enteros positivos.
- El formulario conserva datos ante fallos, muestra errores por campo y mueve
  el foco; PTAA y Profesional usan el rol persistido `personal` en edición.
- La búsqueda enlaza al detalle de personal con la ruta completa.
- Se documentaron los contratos en frontend y backend y se agregaron pruebas.

Validaciones: 28 pruebas backend del bloque Personal y 69 frontend correctas;
TypeScript y build de producción correctos. Las integraciones de alta,
consultas y rollback se ejecutaron sobre SQLite aislado.

Limitaciones: prueba manual y validación contra PostgreSQL pendientes del
usuario, quien levantará Docker. `agent-browser` no está disponible. SQLite
advierte ciclos de claves foráneas al limpiar tablas globales, sin fallos.
ISS-09 conserva pendiente su alcance transversal. No se ejecutó commit.

#### Rango institucional de fechas — Validar ítems desde 2010

- Se centralizó `2010-01-01` como límite inferior de las fechas vinculadas con
  la actividad del grupo en frontend y backend.
- El calendario reutilizable aplica el rango por defecto en Grupo, Personal,
  Producción, Proyectos, Recursos, Transferencia y Memorias; los filtros de
  búsqueda quedan excluidos porque no crean ni modifican ítems.
- Los services rechazan payloads anteriores al rango institucional y conservan
  las reglas particulares sobre fechas futuras y orden de períodos.
- El equipo directivo impide además inicios o finalizaciones futuras y exige que
  la finalización no preceda al inicio.
- Se documentó el contrato transversal y su aplicación en cada módulo afectado.

Validaciones:

- frontend: typecheck correcto y 66 de 66 pruebas correctas en el host;
- build productivo frontend dentro de Docker: correcto, con 2659 módulos;
- backend focalizado dentro de Docker: 11 de 11 pruebas correctas;
- compilación de módulos y tests backend dentro de Docker: correcta;
- regresión backend dentro de Docker: 352 pruebas correctas y 3 incidencias
  ajenas por archivos de infraestructura del repositorio no montados en `/app`;
- la suite frontend no inicia dentro de su contenedor porque la versión de Node
  de esa imagen no admite `--experimental-strip-types`; la misma suite pasa en
  el host;
- la validación manual de pantallas queda reservada para el usuario.

#### ISS-06 — Evitar el cierre intempestivo de la sesión

- El backend informa la expiración del access token, la sesión renovable y el
  umbral configurable de advertencia sin exponer el refresh token fuera de su
  cookie `HttpOnly`.
- El frontend comparte una única renovación concurrente, reintenta cada solicitud
  original una sola vez y renueva por actividad únicamente cuando el access token
  está próximo a vencer.
- Se agregó un aviso accesible con acciones para continuar o cerrar la sesión, y
  el vencimiento conserva una ruta interna completa para restaurarla tras el login.
- Proyectos y configuración de UCT conservan borradores versionados por usuario,
  módulo y registro, con recuperación confirmada, descarte explícito y limpieza al
  guardar. Las claves sensibles se excluyen antes de persistir.
- El guardado pendiente del borrador se fuerza al abandonar o desmontar el
  formulario, evitando perder los últimos campos ingresados dentro del debounce.
- La recuperación se presenta como un diálogo modal obligatorio que inhabilita el
  resto de la pantalla hasta recuperar o descartar el borrador existente.
- Se documentaron `JWT_EXPIRATION_MINUTES`,
  `REFRESH_TOKEN_EXPIRATION_MINUTES` y `SESSION_WARNING_SECONDS` junto con el nuevo
  contrato de temporización.

Validaciones:

- frontend: 65 de 65 pruebas correctas;
- build productivo frontend: correcto, con 2659 módulos procesados;
- typecheck frontend: correcto;
- backend focalizado de autenticación ejecutado dentro de Docker: 27 de 27 pruebas
  correctas, incluida la renovación concurrente;
- `git diff --check`: correcto;
- stack Docker de desarrollo saludable para frontend, backend, PostgreSQL y Redis;
- la validación manual de comportamiento y pantallas queda reservada para la
  revisión del usuario al finalizar el flujo de tareas.

#### ISS-05 — Permitir códigos de proyecto alfanuméricos

- `codigo_proyecto` ahora se persiste y expone como texto alfanumérico de hasta 50
  caracteres, tanto en proyectos como en los snapshots de proyectos y
  distinciones utilizados por memorias.
- El alta y la edición comparten la misma validación backend, conservan el código
  real y devuelven errores accionables asociados al campo.
- El formulario dejó de convertir el código con `Number(...)`, valida el contrato
  antes de guardar y mantiene feedback accesible junto al input.
- Se agregó una migración Alembic para convertir las tres columnas involucradas y
  pruebas de contrato, snapshots, migración y validación frontend.

Validaciones:

- backend focalizado: 29 de 29 pruebas correctas;
- frontend: 56 de 56 pruebas correctas;
- build productivo frontend: correcto;
- API con SQLite: alta, edición, listado y snapshot conservan códigos
  alfanuméricos;
- Alembic: una única cabeza activa, `c6e8a1f4b2d9`;
- migración y reversión verificadas en SQLite; DDL PostgreSQL validado offline;
- `git diff --check`: correcto;
- no se ejecutó integración PostgreSQL ni prueba manual en navegador porque el
  stack Docker no estaba activo;
- el typecheck conserva una incidencia preexistente ajena en `CatalogosHome.tsx`
  por la diferencia entre `Histórico` y `Historico`.

#### ISS-04 — Clarificar permisos de sesión y unificar el rol lector

- Se unificó `LECTURA` como identificador canónico del rol lector en base de
  datos, API y frontend, y se actualizaron los datos iniciales generales y de
  testing para no volver a crear el alias `LECTOR`.
- Se agregó una migración reversible que renombra el rol heredado o, si ambos
  nombres existen, reasigna sus usuarios y elimina el duplicado sin dejar
  referencias huérfanas.
- `Mi perfil` ahora muestra una tarjeta transversal con el rol de la sesión, las
  acciones permitidas y sus restricciones. Para `LECTURA` se aclara que puede
  consultar información, pero no agregar, modificar ni eliminar registros.
- Se verificó y documentó que el borrado de equipamiento está habilitado para
  `ADMIN` y `GESTOR`, devuelve `403 FORBIDDEN` para roles de lectura y mantiene
  el soft delete con su trazabilidad.

Validaciones:

- frontend: 49 de 49 pruebas correctas;
- backend focalizado: 19 de 19 pruebas correctas, incluida la normalización de
  roles, los permisos del endpoint y el soft delete de equipamiento;
- build productivo frontend: correcto, con 2650 módulos procesados;
- Alembic: una única cabeza activa, `d7e4a2c9f1b6`;
- suite backend completa: 345 de 346 pruebas correctas; el único error corresponde
  al bloqueo conocido de un archivo temporal SQLite en Windows en la prueba de
  refresh concurrente;
- `git diff --check`: correcto;
- prueba manual y ejecución de la migración contra PostgreSQL no realizadas
  porque Docker no tenía servicios activos;
- el typecheck mantiene una incidencia preexistente en `CatalogosHome.tsx` por la
  diferencia entre los literales `Histórico` y `Historico`.

#### ISSUE-02 — Validar el rango de fecha de incorporación de equipamiento

- Se definió como rango válido desde el `01/01/2010` hasta la fecha actual,
  inclusive.
- Se incorporó la misma validación en el formulario y en el servicio backend para
  altas y ediciones, con límites visibles y mensajes accionables.
- Se documentó el contrato del módulo Recursos y se agregaron pruebas para los
  límites, fechas inexistentes y valores fuera de rango.

Validaciones:

- frontend: 40 de 40 pruebas correctas al cerrar ISSUE-02;
- backend focalizado de Recursos: 17 de 17 pruebas correctas;
- build productivo frontend: correcto;
- suite backend completa: 330 de 331 pruebas correctas; el único error corresponde
  al bloqueo conocido de un archivo temporal SQLite en Windows;
- prueba manual no ejecutada porque Docker no tenía servicios activos.

#### ISS-03 — Corregir desfases de fechas civiles y auditoría UTC

- Se separó el tratamiento de fechas civiles `YYYY-MM-DD` del tratamiento de
  timestamps para impedir corrimientos de día por zona horaria.
- Los timestamps de auditoría se serializan como UTC explícito y se muestran en la
  zona local del navegador, manteniendo compatibilidad con respuestas heredadas.
- Se centralizaron los helpers de fechas y se actualizaron formularios, detalles,
  historiales y filtros anuales de los módulos afectados.
- Se documentó el contrato temporal compartido en frontend y backend.

Validaciones:

- frontend: 45 de 45 pruebas correctas;
- caso Argentina UTC-3: `2026-01-01` conserva el día y
  `2026-09-07T02:13:31Z` se interpreta como `06/09/2026 23:13`;
- backend focalizado: 20 de 20 pruebas correctas;
- build productivo frontend: correcto;
- suite backend completa: 336 de 337 pruebas correctas; el único error corresponde
  al bloqueo conocido de un archivo temporal SQLite en Windows;
- `git diff --check`: correcto;
- prueba manual no ejecutada porque Docker no tenía servicios activos;
- el typecheck mantiene una incidencia preexistente en `CatalogosHome.tsx` por la
  diferencia entre los literales `Histórico` y `Historico`.

- Se corrigieron la ortografía, las tildes y la puntuación de etiquetas, títulos,
  ayudas, placeholders, confirmaciones y mensajes visibles de la interfaz en
  todos los módulos relevados.

## 2026-09-13 - ISS-11: feedback del selector de investigadores en trabajos

- Reuniones y revistas muestran carga inicial, lista vacia y error con Reintentar.
- Bloquean guardar sin datos; conservan opciones en refetch y selecciones ante fallos.
- Componente exclusivo del modulo; contratos, permisos y hooks compartidos intactos.
- Validacion: 88 tests frontend, typecheck y build:production correctos.
- Inspeccion previa: endpoint real HTTP 200 con dos investigadores activos; incidencia original no reproducida.
- Navegador a cargo del usuario; ampliacion de autoria permanece en ISS-12.

Validacion backend: 28 tests correctos de historial de trabajos en reuniones/revistas y errores de dominio de produccion (unittest).
