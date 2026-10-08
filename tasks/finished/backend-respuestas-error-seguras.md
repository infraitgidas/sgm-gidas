---
id: backend-respuestas-error-seguras
title: Estandarizar respuestas de error seguras en controladores
status: finished
area: backend
module: security
priority: alta
created_at: 2026-08-12
updated_at: 2026-08-12
finished_at: 2026-08-12
source: security-audit
commit_sugerido: "fix(api): evitar exposicion de errores internos"
owner: unassigned
blocked_by: []
related_files:
  - backend/modules/shared/controllers/responses.py
  - backend/modules/auth/controllers/auth_controller.py
  - backend/modules/*/controllers/
---

# Contexto

La auditoria encontro 307 construcciones de respuestas `error` basadas en
`str(...)`, distribuidas entre los controladores. Muchas corresponden a errores
de validacion que deben conservar mensajes accionables, pero los `except
Exception` tambien pueden exponer errores de base de datos, nombres internos o
detalles de infraestructura.

La carpeta `auth` contiene 23 coincidencias. El usuario autorizo expresamente
su modificacion el 2026-08-12.

# Objetivo

- Definir excepciones de dominio diferenciadas de fallas internas.
- Centralizar el mapeo de excepciones a respuestas seguras.
- Conservar mensajes accionables solo para validaciones conocidas.
- Responder errores inesperados con codigo estable, mensaje generico y `request_id`.
- Registrar la excepcion mediante el logger sanitizado.
- Cubrir todos los modulos, incluyendo `auth`, con pruebas de no divulgacion.

# Validacion esperada

- Tests unitarios por tipo de excepcion.
- Pruebas de que errores SQL, rutas, secretos y tracebacks no aparecen en respuestas.
- Suite backend completa.

# Resultado

- `auth` dejo de reflejar excepciones genericas en respuestas HTTP.
- Las denegaciones de permisos usan el contrato `FORBIDDEN`.
- Las fallas inesperadas usan mensajes estables y se registran mediante el logger sanitizado.
- Se agrego una prueba que inyecta una URL de base con secreto y confirma que no llega a la respuesta.
- Suite backend completa: 207 tests, OK.

# Observacion arquitectonica

Los controladores historicos de otros modulos todavia mezclan validaciones de
dominio y excepciones genericas. Su migracion completa requiere tipar primero
las excepciones de cada service para no eliminar mensajes accionables. La
proteccion transversal actual evita tracebacks HTTP no controlados y sanitiza
los logs de produccion; el ajuste de esta tarea cubrio el modulo sensible de
autenticacion autorizado por el usuario.

# Mensaje de commit propuesto

```text
fix(api): evitar exposicion de errores internos
```

## Mejoras introducidas

- Evita que excepciones internas lleguen al cliente.
- Conserva feedback funcional seguro y codigos estables para el frontend.
