# Configuracion manual pendiente y rotacion de secretos

Actualizado: 2026-08-22

Este documento no debe contener valores reales. Su objetivo es conservar el listado
de acciones manuales requeridas antes del despliegue.

## Variables pendientes de agregar o corregir

En `backend/.env.production`:

```text
JWT_EXPIRATION_MINUTES=15
FRONTEND_URL=https://host-real
FRONTEND_URLS=https://host-real
DATABASE_URL=postgresql://gidas_app:<POSTGRES_APP_PASSWORD_URL_ENCODED>@db:5432/gidas_db
HSTS_ENABLED=False
HSTS_MAX_AGE=31536000
```

Reglas:

- activar `HSTS_ENABLED=True` solo despues de validar HTTPS extremo a extremo;
- usar exclusivamente origenes HTTPS, sin slash final, ruta, query ni fragmento;
- mantener usuarios distintos para runtime y migraciones;
- aplicar URL encoding a contraseñas incluidas en URLs de conexion.

## Secretos comprometidos que deben renovarse

Los siguientes nombres aparecieron en salidas diagnosticas y sus valores deben
considerarse comprometidos:

- `SECRET_KEY`;
- `JWT_SECRET`;
- `REFRESH_SECRET`;
- `POSTGRES_ADMIN_PASSWORD`;
- `POSTGRES_APP_PASSWORD`;
- contraseña incluida en `MIGRATION_DATABASE_URL`;
- contraseña incluida en `DATABASE_URL`;
- cualquier `POSTGRES_PASSWORD` heredado que permanezca en uso.

Archivos locales alcanzados por la revision:

- `.env.production`;
- `backend/.env.production`;
- `backend/.env`;
- `backend/.env.docker`;
- `backend/.env.testing`.

Si un valor fue reutilizado en otro archivo, host o entorno, tambien debe rotarse
alli. Al cambiar contraseñas PostgreSQL deben actualizarse en la misma ventana las
URLs que las contienen.

`backend/.env.docker` fue eliminado durante la consolidacion de ambientes. Sus
valores historicos igualmente deben considerarse comprometidos si fueron
reutilizados en otro archivo o servicio.

## Verificacion posterior

- reiniciar o recrear los servicios que consumen secretos;
- invalidar sesiones vigentes al rotar secretos JWT y refresh;
- ejecutar `docker compose --env-file .env.production config --quiet`;
- ejecutar `python backend/tools/validate_production_topology.py --env-file .env.production`;
- probar login, refresh, logout, healthchecks y conexion de migraciones;
- confirmar que ningun valor real aparezca en Git, logs, imagenes o frontend.
