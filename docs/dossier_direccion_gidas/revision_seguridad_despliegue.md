# Revisión final de seguridad para despliegue

Fecha de revisión inicial: 2026-08-18

Última actualización de evidencia: 2026-08-26

Decisión operativa del 2026-08-26: la primera instalación se realizará en una
máquina virtual Linux administrada manualmente por SSH y Docker Compose. Esta
decisión cierra la selección del mecanismo de entrega inicial, pero no sustituye
los controles pendientes de HTTPS, firewall, backups y validación sobre el host.

La calificación temporal sin certificado debe usar `APP_ENV=staging`, origen HTTP
exacto y acceso restringido. `APP_ENV=production` conserva HTTPS y cookie segura
como requisitos cerrados; no se relaja para acomodar la VM.

La topologia fue calificada en un stack aislado con `APP_ENV=staging`: migraciones
terminaron con codigo `0`; PostgreSQL, Redis, backend y frontend alcanzaron estado
saludable; liveness, readiness, frontend y chunk inicial respondieron HTTP `200`.
La busqueda recupero 24 de 24 modulos mediante fixtures ficticios idempotentes. Esta
evidencia valida el mecanismo de despliegue, no los controles externos del host ni
autoriza datos reales por HTTP.

## Alcance y criterio

Esta revisión compara la configuración versionada del repositorio con los controles
mínimos solicitados para desplegar el sistema en servidores facilitados. Un control
se considera completo solo cuando está implementado en código o infraestructura y
puede validarse con la configuración de producción. La existencia de una tarea o
una configuración de ejemplo no equivale a una protección activa.

Las condiciones ejecutables de aprobación, separadas entre responsabilidades de
desarrollo y configuración del servidor, están definidas en
`tasks/in-progress/security-deployment-acceptance.md`.

## Resumen ejecutivo

El repositorio posee una base adecuada de seguridad para un despliegue institucional:
segmentación Docker, base de datos no publicada, JWT firmados, refresh tokens
rotativos, CORS restrictivo en producción, cabeceras defensivas, rate limiting y
arranque que rechaza secretos débiles. Las iteraciones posteriores agregaron
límites en Flask, contratos de error, CSP, pruebas JWT/CORS, validación de topología,
inventario IDOR/BOLA, soporte de secretos por archivo y CI. El despliegue no debe
habilitarse con datos reales hasta resolver y verificar los siguientes puntos:

1. Terminar TLS con un certificado confiable y redirigir HTTP a HTTPS.
2. Definir e implementar el aislamiento multi-UCT antes de usarlo como frontera de
   autorización entre grupos.
3. Inyectar secretos mediante el mecanismo seguro del servidor y no conservarlos
   como variables o archivos legibles más allá de lo necesario.
4. Ejecutar las pruebas backend y las comprobaciones de red sobre el servidor real.

## Matriz de controles

| Control | Estado | Evidencia actual | Acción antes del despliegue |
| --- | --- | --- | --- |
| HTTPS | Pendiente, bloqueante | El Compose publica HTTP y `nginx/gidas.external.conf.example` escucha en puerto 80. Existe una tarea de preparación, pero no hay certificado ni bloque TLS activo. | Definir DNS, certificado, terminación TLS, redirección 80 a 443 y validar login/refresh/logout por HTTPS. |
| Backend no expuesto directamente | Cumple en Compose de producción | `backend` usa `expose: 5000` y una red bridge; solo `nginx` declara `ports`. | Usar solo `docker-compose.yml` en producción. No aplicar el override de desarrollo, que publica backend. Validar con escaneo desde otra máquina. |
| PostgreSQL no expuesto | Cumple en Compose de producción | `db` no declara `ports`; comparte únicamente la red Docker. | No aplicar `docker-compose.dev.yml`, porque ese override publica PostgreSQL. Restringir además el firewall del host. |
| JWT seguro y de corta duración | Desarrollo aprobado; servidor pendiente | HS256 con secreto obligatorio de al menos 32 caracteres, issuer/audience validados y access token de 15 minutos en configuración y plantillas. | Usar secretos independientes y aleatorios, reloj sincronizado y validar expiración/audience en el entorno final. |
| Protección del refresh token | Cumple en diseño; requiere prueba final | Cookie `HttpOnly`, `Secure` en producción, `SameSite=Lax`, path limitado a `/api/v1/auth`, respuestas `no-store`, origen/referer validado, hash persistido, `jti`, rotación y revocación. | Ejecutar pruebas de replay, rotación, logout, cambio de contraseña y origen no permitido sobre HTTPS. Confirmar limpieza periódica de sesiones vencidas. |
| Protección IDOR/BOLA | Desarrollo aprobado para RBAC; multi-UCT diferido | Existe inventario versionado y cobertura dinámica transversal para roles y operaciones. El modelo de pertenencia multi-UCT todavía no está definido. | Mantener las pruebas RBAC en CI y completar `security-multitenancy-uct` antes de prometer aislamiento entre grupos. |
| CORS restrictivo | Cumple si `APP_ENV=production` | Producción rechaza `*` al arrancar y usa `FRONTEND_URLS`; CORS admite credenciales solo para orígenes configurados. | Definir el origen HTTPS exacto, sin comodín, incluyendo puerto si corresponde. Verificar preflight permitido y origen malicioso rechazado. |
| Security headers | Desarrollo aprobado; servidor pendiente | Flask y Nginx aplican headers defensivos y CSP; HSTS queda condicionado a HTTPS validado. | Verificar headers sobre frontend, API y errores del proxy final; activar HSTS después de validar TLS. |
| Límites de tamaño de requests | Desarrollo aprobado; servidor pendiente | Nginx y Flask poseen límites coordinados, contratos 413 y validaciones automatizadas. | Confirmar los valores renderizados y probar el rechazo a través del proxy final. |
| Manejo seguro de errores | Desarrollo aprobado; monitoreo continuo | Existen contratos centralizados, `request_id`, sanitización y cobertura de errores por módulo. | Verificar retención y acceso a logs en el servidor, manteniendo la auditoría en CI. |
| Gestión de secretos | Parcial, bloqueante operativo | Producción falla ante secretos ausentes, débiles o placeholders. `.gitignore` excluye `.env` reales y las variables `VITE_*` se documentan como públicas. | Generar secretos independientes con CSPRNG e inyectarlos mediante el gestor del servidor, Docker secrets o archivos con permisos mínimos. Definir rotación, respaldo y responsable; nunca incluir secretos en imágenes, logs o repositorio. |

## Detalle por control

### HTTPS

El proxy interno actualmente escucha HTTP. `REFRESH_COOKIE_SECURE` y HSTS se activan
en producción, por lo que servir el sistema final sin HTTPS rompería la sesión o
forzaría una configuración insegura. La alternativa recomendada es terminar TLS en
el proxy institucional del servidor y enlazar el Nginx del Compose a `127.0.0.1`, o
activar TLS dentro del contenedor con certificados montados en solo lectura.

No se debe activar HSTS durante pruebas con certificados no confiables. Una vez
validado HTTPS, se debe redirigir HTTP a HTTPS y abrir únicamente el puerto necesario.

### Red y exposición

La topología productiva mantiene PostgreSQL, Redis, backend y frontend sin puertos
publicados. `expose` documenta puertos internos y no los publica en el host. El
override de desarrollo cambia deliberadamente este modelo y no debe utilizarse en
el servidor productivo.

La validación final debe realizarse desde otro equipo de la red, no solo mediante
`docker compose ps`: únicamente el proxy TLS debe responder.

### JWT y refresh

Los access y refresh tokens usan secretos separados configurables, algoritmo fijo,
issuer y expiración. El audience es obligatorio en el ejemplo de producción. El
access token vive en memoria del frontend; no se persiste en `localStorage` ni
`sessionStorage`.

Los refresh tokens se almacenan en el navegador como cookie no accesible por
JavaScript y en base de datos solo mediante hash. Cada renovación crea una sesión
nueva y revoca la anterior. Las operaciones basadas en cookie validan `Origin` o
`Referer`, lo que agrega protección CSRF además de `SameSite=Lax`.

### IDOR/BOLA

La autenticación y los roles están centralizados y el inventario versionado cubre
lecturas, mutaciones, historiales, relaciones y exportaciones. La cobertura dinámica
confirma las restricciones de ADMIN, GESTOR y LECTURA. Aun así, un endpoint puede
exigir `GESTOR` y permitir operar sobre otra UCT porque el modelo de pertenencia y
alcance multi-UCT fue diferido explícitamente.

La matriz pendiente debe cubrir como mínimo:

- lectura de detalles e historiales por ID;
- actualización, baja lógica, reapertura, cierre y exportación;
- relaciones y desvinculaciones;
- acceso entre usuarios, roles y UCT diferentes;
- recursos inexistentes frente a recursos no autorizados;
- parámetros de búsqueda, filtros y exportaciones que acepten IDs.

### CORS, headers y errores

CORS debe usar el origen HTTPS exacto. No reemplaza autenticación ni protección
CSRF. Flask y Nginx aplican una CSP sin `unsafe-eval`, además de `nosniff`, política
de frame, referrer y permissions. HSTS permanece condicionado a HTTPS validado.

Los errores inesperados se centralizan para todos los modulos: el detalle queda en
logs internos asociado a un identificador de solicitud y la API responde un codigo
y mensaje estables sin informacion de infraestructura. Este comportamiento debe
mantenerse cubierto por pruebas y verificarse nuevamente en el servidor final.

### Requests y secretos

Nginx y Flask imponen límites coordinados para no depender de una única capa. Los
endpoints JSON aplican además validación de tipo y tamaño, y las respuestas 413 usan
el contrato seguro común.

Los ejemplos `.env` son plantillas, no un almacén de secretos. En el servidor se
deben generar al menos `SECRET_KEY`, `JWT_SECRET`, `REFRESH_SECRET`, credenciales de
PostgreSQL y cualquier credencial SMTP. Deben ser distintos entre sí y entre
ambientes, y su rotación debe contemplar el cierre de sesiones activas.

## Checklist de habilitación del servidor

- [ ] DNS o IP estable definidos y certificado confiable instalado.
- [ ] Solo HTTPS accesible desde la red autorizada; HTTP redirige a HTTPS.
- [ ] PostgreSQL, Redis, backend y frontend no responden desde la LAN.
- [ ] `APP_ENV=production`, `DEBUG=False` y origen CORS HTTPS exacto.
- [ ] Secretos únicos generados e inyectados fuera del repositorio.
- [ ] Access token con duración aprobada y refresh validado contra replay.
- [ ] Límite de request aplicado en Nginx y Flask.
- [ ] Matriz IDOR/BOLA ejecutada para cada módulo y rol.
- [ ] Headers verificados en frontend, API, 4xx y 5xx.
- [ ] Logs no contienen tokens, cookies, contraseñas ni payloads sensibles.
- [ ] Backups cifrados, restauración probada y acceso administrativo restringido.
- [ ] Suites frontend/backend, healthchecks y escaneo de puertos correctos.

## Conclusión

El sistema no está listo todavía para afirmar un nivel de seguridad productivo
completo. Puede pasar a una instancia de preproducción controlada, pero HTTPS, el
aislamiento multi-UCT y la gestión operativa de secretos son condiciones de salida
antes de cargar datos reales. Los controles de desarrollo restantes deben validarse
de nuevo sobre la versión y el host finales.
