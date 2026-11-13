# Autenticación y usuarios en backend

## Contrato consumido por la validacion preventiva (ISS-33)

Credenciales, rol propio, politica de contrasenas, bloqueo de acceso y sesiones mantienen sus validaciones definitivas. La validacion preventiva del cliente no sustituye esos controles.

El frontend reutiliza sus comprobaciones durante la interaccion y muestra
conjuntamente los errores al guardar. Los errores de campo de la API mantienen
`error.details.fields`; los no asociados a un control conservan feedback general.
La etapa no cambia endpoints, payloads, modelos, permisos ni eventos auditados.
Escribir o corregir un campo no genera una mutacion de dominio; la autoridad
definitiva sigue siendo el backend. Aceptado por el usuario el 05/11/2026.

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

El cambio de contraseña autenticado y la recuperación por correo no levantan un
bloqueo de login activo; conserva su vencimiento original.
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
  Su mínimo es de 2 minutos con `APP_ENV=local`, `development`, `docker` o
  `testing`, para probar vencimientos. En los demás entornos, incluidos
  producción y staging, conserva el mínimo de 60 minutos. El máximo sigue
  siendo 43200 minutos. Ajuste aprobado por el usuario el 05/11/2026.
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

## Recuperacion por correo (ISS-53)

Aprobada por el usuario el 06/11/2026. Las rutas siguientes usan el prefijo
`/api/v1/auth` y responden `{data, meta, error}` con `Cache-Control: no-store`.

| Metodo | Ruta | Acceso y payload | Resultado |
| --- | --- | --- | --- |
| POST | `/password-reset/request` | Publico; `{email}` | 202 con mensaje generico, exista o no una cuenta habilitada. |
| POST | `/password-reset/confirm` | Publico; `{token, password_nueva, password_confirmacion}` | 200 con `data.message`; sin login automatico. |
| POST | `/usuarios/<id>/password-reset` | ADMIN con alcance UCT vigente; sin payload | 202; solicita el mismo correo para el usuario activo. |

`password_reset_controller.py` adapta HTTP; `password_reset_service.py` controla
el ciclo de vida y `credentials_policy.py` comparte validaciones entre altas,
ediciones y cambios de password. El correo se normaliza con trim y minusculas;
el indice funcional unico tambien impide duplicados por mayusculas o espacios.
La password requiere al menos 6 caracteres y hasta 72 bytes UTF-8 para bcrypt.

`PasswordResetRequest` registra UUID, usuario, hash SHA256 de un token aleatorio
de 256 bits, fechas de solicitud/activacion/vencimiento/consumo/revocacion,
HMAC de IP, administrador solicitante opcional y referencia al mensaje de outbox.
Solo existe una solicitud no consumida ni revocada por usuario. Solicitar otra
revoca la anterior y cancela cualquier envio pendiente. Cambiar el correo,
desactivar, eliminar o cambiar password tambien invalida los enlaces anteriores.

El token viaja en el fragmento del enlace, nunca en una respuesta API. Su vigencia
de 30 minutos comienza al aceptar SMTP el mensaje. Confirmar bloquea usuario y
solicitud en orden estable, consume una sola vez, actualiza bcrypt y auditoria,
desactiva `primer_login` y revoca todos los refresh con motivo `password_reset`
en una transaccion. Los bloqueos de login existentes conservan su vencimiento.

Los campos incorrectos devuelven 400 `VALIDATION_ERROR` con `details.fields`.
Un token ausente, incorrecto, no activado, vencido, revocado, consumido o asociado
a una cuenta no habilitada devuelve el mismo 400 `INVALID_PASSWORD_RESET_TOKEN`.
La solicitud publica conserva 202 generico ante errores internos de encolado;
estos se registran solo por clase. ADMIN recibe 404 para cuentas no disponibles
y 503 ante imposibilidad de encolar. Se mantienen 401/403 de autenticacion/rol.

Limites configurables: request 5 por 15 minutos por IP y 3 por hora por HMAC del
correo normalizado; confirm 10 por 15 minutos por IP; ADMIN usa el limite de
cambio de password. Un exceso responde 429 con mensaje seguro.

La migracion `e5a7c9d1f3b6` depende de `c3e5a7b9d1f2`, valida duplicados antes
de cambiar datos, normaliza correos y crea ambas tablas e indices. Ante duplicados
aborta sin fusionar cuentas. El downgrade retira tablas e indice funcional; no
restaura mayusculas ni espacios eliminados. El transporte y operacion estan
documentados en [notifications](../notifications/README.md).

La funcionalidad está implementada; la entrega en producción requiere provisionar
SMTP institucional, secretos y URL HTTPS autorizada, además de mantener activo
`email-worker`. El 202 de solicitud pública no confirma entrega de correo, y el
health de la API no prueba SMTP. El procedimiento de configuración y aceptación
del servidor está en la [guía de despliegue](../../../docs/despliegue_produccion.md#recuperación-de-contraseña-en-producción).

`tests/test_auth_password_reset.py` cubre estados, cifrado, permisos, limites,
revocacion, SMTP/TLS, retries y retencion. Las pruebas PostgreSQL se habilitan
con `PASSWORD_RESET_PG_TEST=1`, usan exclusivamente la base dedicada
`gidas_reset_validation` derivada de la URL configurada y schemas temporales;
requieren permiso para crear schemas y la extension `pg_trgm` del metadata global.
Incluyen confirmacion concurrente, claims disjuntos y upgrade/downgrade/upgrade.

## Fixture de recuperacion administrativa (ISS-99)

La prueba de las rutas versionadas crea una UCT y una pertenencia activa real
del destinatario. Ejecuta la politica ORM de aislamiento sin simular la UCT
permitida: ADMIN obtiene 202 para el usuario de su UCT y 404 para un usuario
ajeno; GESTOR conserva 403 y una peticion sin autenticacion conserva 401.

El ajuste corrige los datos de prueba; no modifica autenticacion, endpoints,
payloads, permisos, envio de correo ni el contrato consumido por frontend.
Aceptado el 07/11/2026. Regresion dirigida de esta etapa: 55 pruebas, OK,
19 omitidas por PostgreSQL dedicado. Suite Linux completa: 777 pruebas, OK,
40 omitidas por PostgreSQL dedicado, incluidas las pruebas locales de Busqueda.
