# Topologia productiva y roles PostgreSQL

La configuracion productiva solo permite publicar puertos al servicio `nginx`.
`backend`, `frontend`, `db`, `redis` y `email-worker` deben usar exclusivamente `expose` o la red
interna de Compose.

La aplicacion y las migraciones usan identidades PostgreSQL diferentes:

- `MIGRATION_DATABASE_URL`: usuario administrativo usado solo por `migrate`;
- `DATABASE_URL`: usuario indicado por `POSTGRES_APP_USER`, usado por `backend`
  y `email-worker`;
- el usuario runtime tiene DML sobre tablas y secuencias, pero no puede crear
  objetos, bases, roles ni actuar como superusuario.

## Validacion

Desde la raiz del repositorio:

```text
python backend/tools/validate_production_topology.py --env-file .env.production
```

El comando renderiza Compose en memoria y no imprime variables ni secretos. Falla
si un servicio privado publica puertos, si aparece otro servicio publico o si las
identidades runtime y migracion no estan separadas.

El proxy publica en loopback por defecto; Cloudflare Tunnel o un proxy TLS del
host proporciona el acceso HTTPS externo. Una exposición LAN exige decisión
expresa del operador y `GIDAS_ALLOW_LAN_BIND=1` al validar la topología; no
sustituye HTTPS. El validador no comprueba conectividad SMTP ni entrega de correo.
`email-worker` necesita salida de red al SMTP institucional, sin publicar puertos
de entrada. Comparte el entorno del backend, arranca después del migrador y
dispone de healthcheck de heartbeat; ese healthcheck no certifica entrega SMTP.

En `backend/.env.production`, `DATABASE_URL` debe tener esta estructura:

```text
DATABASE_URL=postgresql://gidas_app:<POSTGRES_APP_PASSWORD_URL_ENCODED>@db:5432/gidas_db
```

No se debe copiar la contraseña literal a documentacion, logs ni comandos. Si
contiene caracteres reservados de URL, debe codificarse en el componente password.
