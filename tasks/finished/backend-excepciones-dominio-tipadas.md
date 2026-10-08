---
id: backend-excepciones-dominio-tipadas
title: Tipar excepciones de dominio y eliminar reflexion generica
status: finished
area: backend
module: api-security
priority: alta
risk_level: medio-alto
execution_order: 2
created_at: 2026-08-12
updated_at: 2026-08-14
finished_at: 2026-08-14
source: security-audit
commit_sugerido: "refactor(api): tipar errores de dominio y ocultar fallas internas"
owner: codex
blocked_by: []
related_files:
  - backend/modules/shared/controllers/responses.py
  - backend/modules/*/services/
  - backend/modules/*/controllers/
---

# Riesgo

Permanecen 284 respuestas fuera de `auth` que reflejan `str(...)`. La mayoria
son `ValueError` de validacion, pero algunos services usan `Exception` para
reglas esperadas y fallas internas. Un error de driver, SQL o infraestructura
podria llegar al cliente; un reemplazo mecanico podria romper UX y estados HTTP.

# Objetivo

- Exponer solo mensajes de excepciones de dominio tipadas.
- Convertir fallas inesperadas en `INTERNAL_ERROR` con `request_id`.
- Registrar fallas mediante logging sanitizado.
- Preservar contratos, navegacion y mensajes accionables.

# Orden modular por riesgo y volumen

1. `memorias`: exportaciones, snapshots y operaciones criticas.
2. `produccion`: mayor volumen de coincidencias.
3. `personal`: datos personales.
4. `recursos`: informacion economica.
5. `grupo` y `proyectos`: relaciones y cierres.
6. `transferencia`, `catalogos`, `dashboard` y `search`.

Cada modulo debe ser una subtarea y un commit independiente.

# Diseño propuesto

- `DomainError` base con codigo estable y status permitido.
- Subtipos: `ValidationError`, `NotFoundError`, `ConflictError`, `ForbiddenError`.
- Handler central que serializa solo tipos conocidos.
- Excepciones desconocidas: log sanitizado + respuesta generica.
- No incluir objetos SQL, payloads, rutas internas ni stack traces en details.

# Proceso por modulo

1. Inventariar excepciones levantadas y estados actuales.
2. Clasificarlas antes de editar controladores.
3. Migrar service y controller juntos.
4. Agregar pruebas de mensajes funcionales y de no divulgacion.
5. Ejecutar tests del modulo y suite completa.
6. Actualizar README backend del modulo.
7. Commit y continuar al siguiente modulo.

# Estado de ejecucion

Completados y validados:

- Infraestructura compartida: `3c13d3d`.
- `memorias`: `04c0cb7`.
- `produccion`: migracion completa en seis commits, ultimo `d51a823`.
- `personal`: `72aa0cf` y `98a4ca4`.
- `recursos`: `996c29c`, suite completa de 252 pruebas correcta.
- `grupo`: `48cf8c6`, controladores migrados al serializador seguro; pruebas
  `tests.test_grupo_domain_errors` correctas (2 pruebas).
- `proyectos`: `3bf72c7`, services y controllers migrados; pruebas de dominio e
  historial correctas (7 pruebas).
- `transferencia`: `6f672dc`, migracion completa; 7 pruebas focalizadas.
- `catalogos`: `290f9c2`, migracion completa; 6 pruebas focalizadas.
- `dashboard`: `e526c80`, migracion completa; 2 pruebas focalizadas.
- `search`: `f645a4f`, migracion completa; 9 pruebas focalizadas.
- Suite backend final: 266 pruebas correctas.

Pendientes: ninguno.

El movimiento original de `tasks/pendient/` a `tasks/in-progress/` permanece
sin commitear porque `tasks/in-progress/` esta ignorado. Al cerrar, agregar el
archivo final con `git add -f` en `tasks/finished/` junto con la metadata de
cierre.

# Criterios de aceptacion

- Ningun `except Exception` devuelve `str(error)`.
- Errores SQL, URLs internas, secretos y tracebacks no llegan a HTTP.
- Las validaciones conocidas conservan mensajes accionables.
- Estados 400, 403, 404, 409 y 500 son coherentes.
- Toda respuesta inesperada contiene un codigo estable y `request_id`.
- Suite backend completa correcta después de cada modulo.

# Commits esperados

```text
refactor(shared): definir excepciones seguras de dominio
refactor(memorias): tipar errores de dominio
refactor(produccion): tipar errores de dominio
refactor(personal): tipar errores de dominio
refactor(recursos): tipar errores de dominio
refactor(grupo): tipar errores de dominio
refactor(proyectos): tipar errores de dominio
refactor(api): completar migracion de errores seguros
```

## Mejoras introducidas

- Distingue validacion, conflicto y ausencia mediante errores de dominio explicitos.
- Reduce uso de excepciones genericas y traducciones inconsistentes en controllers.
