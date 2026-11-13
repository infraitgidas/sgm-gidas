# Notificaciones por correo

Infraestructura de ISS-53, aprobada el 06/11/2026. Este modulo no expone rutas
HTTP: auth decide permisos, destinatario y solicitud; notifications cifra,
almacena, entrega y mantiene los mensajes. `EmailTransport` permite reemplazar
SMTP sin cambiar el flujo de recuperacion ni su contrato frontend.

## Modelo y entrega

`EmailOutbox` persiste UUID, tipo de mensaje, estado, payload cifrado, intentos,
proximo intento, lease, clase de error y fechas operativas. Estados:
`pending -> processing -> sent`; ante error retorna a pending o termina failed;
una revocacion puede terminar cancelled. Constraints restringen estados e
intentos y exigen payload solo para pending/processing. Se borra el payload al
enviar, fallar definitivamente o cancelar; nunca se registra en logs.

`payload_cipher.py` cifra JSON autenticado con Fernet. La clave debe permanecer
estable mientras existan mensajes pendientes y ser distinta de SECRET_KEY,
JWT_SECRET, REFRESH_SECRET y PASSWORD_RESET_HMAC_KEY. Perderla impide entregar
esos mensajes; cambiarlas exige drenar la cola o invalidar solicitudes pendientes
antes de rotar. No se incluye la clave en el repositorio ni en la base de datos.

`email_worker.py` confirma claims de hasta 20 mensajes antes del I/O mediante
FOR UPDATE SKIP LOCKED. Cada claim posee lease unico recuperable a los 5 minutos.
Antes de enviar verifica lease, solicitud y cuenta; bloquea usuario, solicitud y
mensaje en ese orden para serializar envio y reemplazo. `smtp_transport.py`
entrega texto y HTML, negocia starttls o SSL con certificados verificados y usa
timeout acotado. SMTP aceptado activa el enlace y elimina el payload en una
transaccion. Un rechazo de destinatario cuenta como error de entrega.

Hay cinco reintentos despues del inicial: 1, 5, 15, 60 y 240 minutos. El sexto
fallo termina failed y revoca la solicitud. Una caida puede recuperar el lease;
la aceptacion SMTP seguida de una falla de commit puede duplicar un correo.
Todos esos correos contienen el mismo token de un solo uso. No existe garantia
de entrega exactamente una vez frente a un sistema SMTP externo.

La purga elimina mensajes sent de mas de 7 dias, failed/cancelled de mas de
30 dias y solicitudes consumidas/revocadas/vencidas de mas de 30 dias. La FK
de solicitud a mensaje usa SET NULL. No se guarda correo en las estadisticas.
El worker ejecuta mantenimiento cada hora, emite alertas por conteos de mensajes
demorados/fallidos o cola mayor a 100 y actualiza heartbeat para healthcheck.

## Configuracion y despliegue

API y worker comparten DATABASE_URL, EMAIL_OUTBOX_ENCRYPTION_KEY y
PASSWORD_RESET_HMAC_KEY. Ambos secretos y MAIL_PASSWORD admiten sufijo `_FILE`.
La clave Fernet se genera con `Fernet.generate_key()`; HMAC requiere al menos
32 caracteres aleatorios. Los ejemplos de entorno contienen solo placeholders.

Configurar MAIL_SERVER, MAIL_PORT, MAIL_DEFAULT_SENDER y, si corresponde,
MAIL_USERNAME/MAIL_PASSWORD. SMTP_TLS_MODE admite starttls, ssl o none; none
solo se permite fuera de produccion/staging. SMTP_TIMEOUT_SECONDS admite 1..60
(predeterminado 20), EMAIL_WORKER_POLL_SECONDS 1..60 (predeterminado 5).
PASSWORD_RESET_PUBLIC_URL apunta a la ruta frontend `/restablecer-password`,
sin query, fragmento ni credenciales. En produccion/staging exige HTTPS y un
origen incluido en FRONTEND_URLS. El arranque rechaza configuracion incompleta.

Docker Compose ejecuta `email-worker` con la misma imagen del backend y
ENTRYPOINT_MODE=email-worker despues del migrador. Conserva usuario no root,
filesystem de solo lectura, tmpfs, capacidades reducidas y limites de recursos.
El heartbeat `/tmp/gidas-email-worker-heartbeat` debe tener menos de 120 segundos.
Ese healthcheck verifica actividad reciente del proceso, no conectividad SMTP
ni entrega al destinatario. La configuración se valida al iniciar Flask; `sent`
indica aceptación por SMTP y no garantiza llegada a bandeja de entrada. Las
alertas de cola se escriben en logs: integrarlas con monitoreo externo corresponde
al despliegue. Véase la [guía productiva](../../../docs/despliegue_produccion.md#recuperación-de-contraseña-en-producción)
para verificar parámetros y efectuar la aceptación con correo controlado.
Es compatible con varios workers por los claims disjuntos; los logs solo
contienen IDs operativos, numero de intento y clase de error.

El override de desarrollo agrega Mailpit v1.32.0, SMTP local 1025 e interfaz
8025, ambos publicados solo en loopback. MAILPIT_SMTP_PORT y MAILPIT_UI_PORT
permiten cambiar los puertos publicados. API/worker usan mailpit:1025 sin TLS
ni credenciales; PASSWORD_RESET_PUBLIC_URL predeterminada es
`http://localhost/restablecer-password`, ajustable al origen/puerto del frontend.
Mailpit no se agrega al compose de produccion. No envia correos a destinatarios
externos; los captura para validacion local.

Comandos desde backend con Flask configurado:

```text
flask email-worker
flask email-worker --once
flask email-queue-stats
flask purge-email-outbox
```

La migracion de tablas forma parte de `e5a7c9d1f3b6` en auth. Se verificaron
estados, reintentos, recuperacion de lease, retencion, cifrado, SMTP/TLS y claims
concurrentes con las pruebas de `tests/test_auth_password_reset.py`; el smoke
local comprobo API, PostgreSQL, worker, Mailpit, consumo, revocacion y login.
