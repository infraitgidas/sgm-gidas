# Entorno de desarrollo (ISS-97)

Usar `docker-compose.dev.yml` junto con `docker-compose.yml`. El backend dispone
de 2 CPU por defecto; `DEV_BACKEND_CPUS`, en el entorno de Compose o en el `.env`
de la raíz, permite ajustar ese límite. El override conserva la memoria backend
de 768 MiB. Los límites productivos se definen en el archivo base.

## Recarga y aplicación de cambios

Flask continúa recargando ante cambios de código de aplicación. La variable
`FLASK_RUN_EXCLUDE_PATTERNS` excluye `/app/tests/*`, `/app/tools/*` y
`/app/migrations/*` para que editar pruebas, herramientas o migraciones no
interrumpa solicitudes. Si un cambio de esas carpetas requiere reinicio del
servidor, hacerlo explícitamente. Editar una migración no la aplica: ejecutarla
exige el procedimiento del entorno y las credenciales correspondientes.

Desde la raíz, validar y aplicar únicamente los servicios afectados:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --no-deps backend frontend
```

La configuración conserva rutas, controllers, services, modelos, permisos,
auditoría e historiales de los módulos. No requiere cambios de esquema o payloads.

## Diagnóstico y validación

- Comprobar `/api/v1/health/ready` y la salud de los contenedores.
- Correlacionar solicitudes mediante `X-Request-ID` y los logs de duración.
- Para `ProgrammingError`, revisar el error PostgreSQL concreto y su fecha.
  En ISS-97 se identificaron consultas históricas a columnas ausentes durante
  cambios de modelos luego revertidos; los endpoints vigentes respondieron 200.
- Revisar `cpu.stat` y `memory.events` del contenedor actual. Son contadores
  acumulados; un OOM de otra instancia no demuestra falta de memoria actual.
- Comparar muestras repetidas, primera solicitud y solicitudes posteriores.
  Distinguir tiempo HTTP, caché, reinicios y renderizado del navegador.

Aceptado por el usuario el 07/11/2026. Validación técnica: 25 pruebas backend;
45 GET antes y 45 después con HTTP 200, más 27 GET posteriores con concurrencia
de 3, todos HTTP 200. Las medianas locales mejoraron, sin acreditar rendimiento
institucional ni tiempos de renderizado. La instrumentación del navegador no
pudo ejecutarse; el usuario aceptó manualmente el ajuste entregado.

Ver también [desarrollo frontend](../frontend/README.md#desarrollo-con-docker-iss-97).
