---
id: backend-security-nginx-rate-limit
title: Auditar seguridad del backend y endurecer rate limiting en Nginx
status: finished
area: backend-infra
module: security
priority: alta
created_at: 2026-08-12
updated_at: 2026-08-12
finished_at: 2026-08-12
source: user-request
commit_sugerido: "fix(security): reforzar logs y rate limiting del gateway"
owner: agent
related_files:
  - backend/modules/shared/services/logging_config.py
  - backend/tests/test_logging_config.py
  - backend/tools/seed_testing_data.py
  - backend/readme.txt
  - nginx/default.conf
  - nginx/default.dev.conf
  - docs/despliegue_produccion.md
---

# Resultado

- Se amplio la redaccion de credenciales, tokens, cookies y secretos.
- Los tracebacks se omiten en logs JSON de produccion, conservando el tipo de excepcion.
- Se valido y normalizo `X-Request-ID` antes de reflejarlo.
- La herramienta de seed de testing dejo de imprimir contrasenas.
- Nginx responde limites excedidos con JSON, `429`, `Retry-After: 30` y `Cache-Control: no-store`.
- El rechazo de Nginx se realiza mediante una ubicacion interna antes de `proxy_pass`.
- Flask-Limiter se conserva como defensa en profundidad.

# Hallazgo pendiente

La auditoria estatica encontro 307 respuestas que construyen el campo `error`
desde `str(...)` en controladores. No todas representan una fuga: varias son
validaciones de dominio esperadas. Sin una taxonomia de excepciones, las fallas
internas pueden mezclarse con ellas y revelar detalles. Existen 23 coincidencias
en `auth`, zona restringida que no se modifico. Se registro una tarea separada.

# Archivos modificados

- `backend/modules/shared/services/logging_config.py`
- `backend/tests/test_logging_config.py`
- `backend/tools/seed_testing_data.py`
- `backend/readme.txt`
- `nginx/default.conf`
- `nginx/default.dev.conf`
- `docs/despliegue_produccion.md`

# Validaciones

- Suite backend completa en imagen de produccion: 206 tests, OK.
- `nginx -t` con `nginxinc/nginx-unprivileged:1.27-alpine`: exitoso.
- `git diff --check`: sin errores.
- El entorno virtual local estaba incompleto; la validacion definitiva se hizo en Docker.

# Mensaje de commit propuesto

```text
fix(security): reforzar logs y rate limiting del gateway
```

## Mejoras introducidas

- Limita abuso y concurrencia antes de consumir recursos del backend.
- Mantiene respuestas y logs seguros para diagnostico sin filtrar informacion.
