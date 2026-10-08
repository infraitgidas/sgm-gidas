# GIDAS UCT – Frontend

## Requisitos
- **Node.js v20.19 o superior** (incluye npm).
  - Verificar instalación:
    ```bash
    node -v
    npm -v
    ```
  - Si no está instalado:
    - Descargar desde [https://nodejs.org/](https://nodejs.org/).
    
- **Git** instalado (para clonar el repo).

## Instrucciones

```bash
# 1. Clonar el repo
git clone <URL_DEL_REPO> gidas-uct
cd gidas-uct

# 2. Instalar dependencias
npm install

# 3. Correr en desarrollo
npm run dev
```

## Arquitectura frontend

El alcance de datos por UCT de la sesion, los contratos y el comportamiento
de cache se describen en [Aislamiento de UCT](UCT_ISOLATION.md).

El frontend se organiza como monolito modular bajo `src/modules`.

Cada modulo contiene, cuando aplica:

- `pages`: vistas de home, formulario y detalle.
- `services`: clientes HTTP, tipos TypeScript y contratos con backend.
- `hooks`: hooks reutilizables del dominio.
- `components`: componentes especificos del dominio.

Modulos actuales:

- `auth`
- `catalogos`
- `dashboard`
- `grupo`
- `memorias`
- `personal`
- `produccion`
- `proyectos`
- `recursos`
- `search`
- `shared`
- `transferencia`

Las implementaciones de dominio y sus imports residen directamente bajo
`src/modules/<modulo>`. Las antiguas fachadas `src/pages`, `src/services` y
`src/hooks` fueron retiradas para evitar dos rutas de acceso al mismo codigo.

Los componentes reutilizables globales permanecen en `src/components`, el layout
global en `src/layouts`, el contexto de autenticacion en `src/context` y los
estilos base en `src/styles`.

El contrato transversal para adaptar homes, formularios, detalles e historiales
se encuentra en [`CONVENCIONES_PANTALLAS.md`](CONVENCIONES_PANTALLAS.md). Incluye
paginacion, filtros, acciones, permisos, estados, accesibilidad y la presentacion
directa de eventos relacionales sin exponer IDs ni JSON.

## Contrato de fechas y horas

- Las fechas civiles recibidas como `YYYY-MM-DD` se parsean con
  `src/utils/dateTime.ts` en calendario local, sin convertirlas a UTC.
- Los formularios generan payloads de fecha civil desde sus componentes locales;
  no deben usar `toISOString()` para campos SQL `Date`.
- Los timestamps de API deben incluir `Z` u otro offset. El frontend los convierte
  a la zona local del navegador para su presentacion.
- El parser de timestamps conserva compatibilidad con respuestas antiguas sin
  zona interpretandolas como UTC, que es la semantica con la que fueron creadas.
- Los filtros de anio usan `getCivilYear` para evitar que `01/01` se atribuya al
  anio anterior en zonas horarias negativas.

## Tabla reutilizable (ISS-25)

`src/components/Table.tsx` expone una tabla generica y controlada. El componente
solo presenta datos y delega consultas, filtros, permisos, navegacion y acciones
de dominio al modulo consumidor.

API principal:

- `TableColumn<T>` define `id`, encabezado y renderizador; admite alineacion,
  prioridad responsive, ordenamiento y clases adicionales.
- `TableProps<T>` recibe filas, `getRowId`, densidad `compact` o `comfortable`,
  estados de carga/error/vacio, orden y paginacion controlados.
- `expandedRowId`, `onToggleRow` y `renderExpanded` permiten contenido diferido
  por fila sin almacenar estado dentro de la tabla.
- `onRowClick` y `getRowTitle` hacen navegable una fila; los controles
  interactivos internos no disparan la navegacion de la fila.
- `refreshing` conserva las filas durante una recarga y comunica la actualizacion
  mediante `aria-busy` y un estado accesible.
- El slot `toolbar` acepta las primitivas exportadas `TableToolbar`,
  `TableSearch`, `TableFilterChip`, `TableActions` y `TableActionButton`.

La tabla incluye `caption`, encabezados con `scope` y `aria-sort`, expansion con
`aria-expanded`, paginacion etiquetada, foco visible, soporte de teclado y
transiciones que respetan `prefers-reduced-motion`. Las columnas `secondary` y
`tertiary` se ocultan progresivamente y el contenedor admite desplazamiento
horizontal.

## Variables de entorno

El frontend usa variables publicas de Vite. Los archivos de referencia son:

- `.env.example`
- `.env.testing.example`
- `.env.production.example`

Variables principales:

- `VITE_APP_ENV`: marca el ambiente visible para el build (`local`, `testing`, `production`).
- `VITE_API_BASE_URL`: URL base versionada de la API. Usar `http://localhost:5000/api/v1` para backend local o `/api/v1` cuando se accede por nginx.
- `VITE_API_URL`: variable legacy aceptada por compatibilidad. Si no termina en `/api/v1`, el cliente HTTP agrega el prefijo versionado.
- `VITE_SERVER_FILTER_PERSONAL`: activa el filtrado del servidor para personal.

Scripts por ambiente:

```bash
npm run dev:testing
npm run build:testing
npm run build:production
```

## Docker y produccion

El frontend se construye con Dockerfile multi-stage:

- `dependencies`: instala dependencias con `npm ci`.
- `build`: genera el bundle estatico de Vite.
- `production`: sirve `dist` con Nginx no privilegiado en el puerto interno 8080.
- `development`: ejecuta Vite para desarrollo local.

En produccion debe usarse `VITE_API_BASE_URL=/api/v1` para que el proxy Nginx del proyecto enrute la API versionada sin exponer el backend al host. Las variables `VITE_*` son publicas y quedan embebidas en el bundle, por lo que no deben contener claves, tokens ni secretos.

Controles aplicados en produccion:

- imagen final sin Node.js ni dependencias de desarrollo.
- servidor Nginx no privilegiado.
- cache de assets estaticos versionados.
- fallback SPA hacia `index.html`.
- contenedor compatible con filesystem read-only, `no-new-privileges` y capacidades Linux reducidas desde Compose.
- el cliente HTTP no imprime cuerpos de error ni respuestas del backend en la consola.
- el estado local corrupto se descarta sin bloquear la aplicacion.
- TypeScript se declara explicitamente para que el typecheck sea reproducible.
- las dependencias deben mantenerse con `npm audit` sin vulnerabilidades conocidas.

La sesion no persiste tokens ni datos del usuario en `localStorage` o
`sessionStorage`. El access token se mantiene solo en memoria y el refresh token
permanece en la cookie `gidas_refresh`, que debe ser `HttpOnly`, `Secure` y
`SameSite` en produccion. Todas las solicitudes usan credenciales same-origin.

Al iniciar la SPA se llama a `POST /api/v1/auth/refresh`; una respuesta valida
restaura el access token y el usuario antes de renderizar rutas protegidas. Las
respuestas 401 comparten una unica renovacion concurrente y cada solicitud se
reintenta como maximo una vez. El logout llama primero al servidor y siempre
limpia el estado en memoria; las otras pestanas reciben solo el evento `logout`
mediante `BroadcastChannel`, nunca credenciales.

Cada login y logout avanza una generacion de sesion para que una renovacion que
ya estaba en vuelo no pueda restaurar un token invalidado. Las pestanas
serializan sus renovaciones y el logout mediante el mismo Web Lock cuando el
navegador lo soporta. La limpieza local y el evento de logout son inmediatos,
pero la expiracion de la cookie espera cualquier rotacion ya iniciada, evitando
que una respuesta de refresh posterior vuelva a establecerla.
En navegadores sin Web Locks, el backend debe conservar su proteccion frente a
renovaciones concurrentes y responder de forma segura a carreras de rotacion.

Para desarrollo con Docker usar el compose de desarrollo desde la raiz del proyecto:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

El archivo `docker-compose.dev.yml` es un override: debe ejecutarse junto con
`docker-compose.yml` para que todos los servicios compartan la misma red.

## Inicio de sesion

El flujo publico y autenticado se organiza asi:

- `/`: landing publica del sistema.
- `/login`: formulario de acceso.
- `/registro`: configuracion del administrador inicial, disponible solo si no existen usuarios.
- `/inicio`: home operativo protegido.

Al abrir una ruta protegida, el sistema mantiene el estado de carga mientras
intenta renovar la sesion mediante la cookie HttpOnly. Si la renovacion falla,
el usuario permanece en el login y no se renderiza contenido protegido.

La landing reutiliza el componente `Footer` existente sin modificarlo. Landing
y login consultan el estado de configuracion inicial; el enlace de registro no
se renderiza salvo que el backend confirme que todavia no existe ningun usuario.

## Historial de directivos

El home de la UCT ofrece un popover no modal para consultar los periodos del
equipo directivo. La consulta se realiza al abrirlo mediante
`GET /api/v1/grupo/directivos/grupo/:grupoId` y presenta 3 registros por pagina.
El popover no usa backdrop y permite continuar interactuando con la pagina.
