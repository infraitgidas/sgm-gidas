# Autenticación y usuarios en backend

## Listados paginados (ISS-89)

`GET /api/v1/auth/usuarios` (ADMIN) y `GET /api/v1/auth/ucts-permitidas`
(usuario autenticado) conservan el array anterior sin `page` ni `per_page`.
Con alguno de esos parametros obtienen total y filas de la pagina en SQL y
responden con `data`, `meta` y `error`. `meta.source = "legacy-list"` se conserva
por compatibilidad. El listado de usuarios mantiene sus filtros y orden;
las UCT permitidas siguen limitadas por la pertenencia activa. La paginacion
no cambia permisos ni expone datos de otras UCT.

## Pertenencia a UCT (security-multitenancy-uct)

El usuario activo debe tener exactamente una pertenencia activa a una UCT
activa para usar los endpoints de datos. ADMIN, GESTOR y LECTURA se limitan a
esa misma UCT; la eleccion de varias UCT queda pendiente. `GET
/api/v1/auth/ucts-permitidas` consulta las UCT permitidas, sin cambiar el
alcance. Las altas de usuarios efectuadas por un ADMIN heredan su UCT. La
tabla `usuario_grupo_utn` conserva estado y auditoria de la pertenencia.

El contrato completo, los errores, las migraciones y las reglas de despliegue
se documentan en [Aislamiento de datos por UCT](../SECURITY_MULTITENANCY_UCT.md).

## Bloqueo de login (ISS-78)

`POST /api/v1/auth/login` cuenta fallos consecutivos por nombre de usuario
ingresado. Los primeros dos fallos devuelven `AUTH_REQUIRED` (401). El tercero
activa un bloqueo de 15 minutos y devuelve `LOGIN_LOCKED` (429), con el encabezado
`Retry-After` en segundos. Durante el bloqueo se rechaza incluso la contraseña
correcta, sin emitir tokens ni cookie. Tras vencer, el contador comienza en cero;
un login correcto también lo limpia.

`LoginAttempt` conserva contador, último fallo, vencimiento y marcas de tiempo en
la base de datos. La clave del registro es un HMAC del nombre de usuario con
`SECRET_KEY`, que debe ser estable entre instancias y reinicios. Se crea estado
también para nombres inexistentes; su secuencia de códigos y mensajes coincide
con la de una cuenta válida. La transacción bloquea la fila por identificador
para serializar intentos concurrentes en PostgreSQL. El evento de bloqueo registra
solo un prefijo del HMAC, sin credenciales ni tokens. El límite de frecuencia por
IP existente sigue aplicándose.

El cambio de contraseña autenticado no levanta un bloqueo de login activo. La
recuperación de contraseña futura deberá definir su propia regla de desbloqueo.
Antes de desplegar, ejecutar la migración `f0a8c1d2e3b4`.

## Errores de autenticación (ISS-09)

Las credenciales inválidas y los tokens no utilizables responden `AUTH_REQUIRED`
(401); los diagnósticos internos de token no se reflejan en la respuesta.
Usuario inexistente: 404; conflictos de usuario/correo o protección del último
administrador: 409; permisos: 403; fallas inesperadas: 500.
Los campos requeridos, contraseña y rol usan `error.details.fields` con las
claves del payload. Se conservan las cookies, protección de origen y reglas de
contraseña existentes. El logout mantiene la limpieza de cookies aunque falle
la revocación. Véase el contrato transversal en `../README.md`.

ISS-19 mantiene las claves HTTP `nombre_usuario`, `mail`, `password`, `rol_id`, `password_actual`, `password_nueva` y `password_confirmacion`. Los mensajes de correo y rol para crear o editar usuarios son públicos y accionables; un fallo no devuelve credenciales ni detalles internos.

## Responsabilidades

El módulo concentra rutas, controladores, servicios y modelos de identidad. Gestiona usuarios, roles, contraseñas, access tokens de corta duración, sesiones de refresh revocables y el alta controlada del primer administrador.

Los nombres canonicos de rol son `ADMIN`, `GESTOR` y `LECTURA`. La migracion
`d7e4a2c9f1b6` renombra el valor heredado `LECTOR`, reasigna sus usuarios si ambos
valores coexistieran y conserva un unico rol lector.

## Endpoints

Todos los endpoints se publican bajo `/auth`.

| Método | Ruta | Acceso | Uso |
| --- | --- | --- | --- |
| GET | `/primer-usuario` | Público, limitado | Indica si existe un usuario inicial. |
| POST | `/register` | Primer alta o ADMIN | Crea el administrador inicial bajo las reglas del servicio. |
| POST | `/login` | Público, limitado | Valida credenciales y entrega access token más cookie de refresh. |
| GET | `/perfil` | Autenticado | Obtiene la identidad de la sesión. |
| POST | `/refresh` | Cookie y origen confiable | Rota la sesión de refresh y entrega un access token nuevo. |
| POST | `/logout` | Cookie y origen confiable | Revoca la sesión y elimina la cookie. |
| POST | `/cambiar-password` | Autenticado, limitado | Cambia la contraseña y finaliza el primer login. |
| GET/POST | `/usuarios` | ADMIN | Lista o crea usuarios. |
| GET/PUT | `/usuarios/<id>` | Propietario o ADMIN según operación | Consulta o actualiza datos permitidos. |
| DELETE | `/usuarios/<id>` | ADMIN | Aplica la regla de eliminación definida por el servicio. |

## Controles de seguridad

- La autorización se valida en controller/service; no depende del frontend.
- Los seeds generales y de testing crean exclusivamente los tres roles canonicos.
- Las credenciales se validan y almacenan mediante hash, nunca en texto plano.
- La cookie de refresh usa las opciones seguras configuradas por entorno y las operaciones con cookie validan origen.
- Las respuestas de autenticación se marcan `no-store`.
- Login, registro y cambio de contraseña poseen limitación de frecuencia.
- Las sesiones de refresh se registran, reclaman atomicamente, rotan y revocan para
  conservar trazabilidad e impedir dos renovaciones simultaneas del mismo token.
- Las sesiones vencidas o revocadas se purgan conservando el periodo de evidencia
  definido por `REFRESH_SESSION_RETENTION_DAYS`.
- Los errores inesperados devuelven mensajes genéricos y no exponen detalles internos.

## Duracion y contrato de sesion

`POST /api/v1/auth/cambiar-password` revoca las sesiones anteriores y entrega
nuevo access token, tiempos y cookie de refresh `HttpOnly` para la sesión actual.
El refresh token no aparece en el JSON. Una recarga conserva la sesión nueva.

- `JWT_EXPIRATION_MINUTES` define la vigencia del access token (15 minutos por defecto).
- `REFRESH_TOKEN_EXPIRATION_MINUTES` define la vigencia renovable de la sesion (10080 minutos, siete dias, por defecto).
- `SESSION_WARNING_SECONDS` define con cuanta anticipacion el frontend muestra el aviso de vencimiento (300 segundos por defecto).
- Login, registro y refresh devuelven `access_expires_at`, `session_expires_at` y
  `session_warning_seconds`. Son metadatos de temporizacion; los tokens siguen sin
  persistirse en el navegador y el refresh permanece exclusivamente en cookie `HttpOnly`.
- Cada refresh valido rota el token, extiende el vencimiento renovable y rechaza el
  token anterior, por lo que la actividad del usuario puede sostener la sesion sin
  enviar una renovacion por cada evento del navegador.

## Despliegue

En servidores se deben definir secretos y orígenes permitidos mediante variables de entorno, habilitar cookies seguras detrás de HTTPS y conservar la misma topología de proxy para frontend y API. No se deben usar valores de desarrollo en producción.

El scheduler del servidor debe ejecutar diariamente:

```text
flask auth purge-refresh-sessions
```

Antes de activarlo puede comprobarse el alcance con
`flask auth purge-refresh-sessions --dry-run`. El comando no imprime tokens ni
metadatos personales.

## Verificación

Desde `backend/`, ejecutar las pruebas de middleware, expiración, cookies y rotación de refresh incluidas en `tests/test_auth_*.py`. Antes del despliegue también se debe ejecutar la suite completa con la base de datos del entorno de pruebas.
