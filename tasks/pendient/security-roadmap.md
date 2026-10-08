---
id: security-roadmap
title: Ejecutar roadmap de riesgos de seguridad y calidad
status: pendient
area: cross-cutting
module: security
priority: critica
risk_level: gobernanza
execution_order: 0
created_at: 2026-08-12
updated_at: 2026-08-26
source: security-audit
commit_sugerido: "docs(security): ordenar plan de mitigacion de riesgos"
owner: coordinator-agent
blocked_by: []
related_tasks:
  - security-deployment-acceptance
  - auth-refresh-cookie-http-only
  - backend-excepciones-dominio-tipadas
  - infra-https-lan-nginx
  - infra-ci-cd-pipeline-produccion
  - frontend-code-splitting
  - infra-observabilidad-plataforma
---

# Objetivo

Ordenar las tareas pendientes para reducir primero probabilidad e impacto de
compromiso, evitando trabajo duplicado y maximizando calidad por contexto usado.

# Orden de necesidad

## 1. Sesion con cookie HttpOnly

- Riesgo: alto; robo de tokens ante XSS.
- Objetivo: refresh inaccesible a JavaScript y access token en memoria.
- Paralelizacion: coordinador + backend + frontend + testing.
- Tarea: `auth-refresh-cookie-http-only.md`.

## 2. Excepciones de dominio seguras

- Riesgo: medio-alto; posible divulgacion de detalles internos.
- Objetivo: separar mensajes funcionales de fallas inesperadas.
- Ejecucion: secuencial por modulo, commits pequenos.
- Tarea: `backend-excepciones-dominio-tipadas.md`.

## 3. HTTPS en LAN

- Riesgo: alto si se usan credenciales sobre una red no confiable.
- Objetivo: cifrar trafico y habilitar cookies `Secure` reales.
- Dependencia externa: DNS/certificados del laboratorio.
- Tarea: `infra-https-lan-nginx.md`.

La tarea 1 puede desarrollarse antes, pero no debe considerarse validada para
produccion hasta probarla sobre HTTPS.

## 4. CI/CD de seguridad

- Riesgo: medio; regresiones y dependencias vulnerables sin deteccion automatica.
- Objetivo: ejecutar tests backend, typecheck/build, audit y validaciones Docker.
- Tarea: `infra-ci-cd-pipeline-produccion.md`.

## 5. Performance frontend

- Estado: completado el 2026-08-26.
- Resultado: carga diferida por modulos sin cambiar rutas ni permisos; bundle
  inicial reducido de 1.284,65 kB a 338,48 kB y sin chunks mayores a 500 kB.
- Evidencia: `tasks/finished/frontend-code-splitting.md`.

## 6. Observabilidad integral

- Riesgo: operativo; deteccion y respuesta tardias.
- Objetivo: centralizar señales sin registrar datos sensibles.
- Solo iniciar tras decisiones de capacidad, acceso y retencion.
- Tarea: `infra-observabilidad-plataforma.md`.

# Reglas de eficiencia multiagente

- Paralelizar solo archivos y contratos independientes.
- Un coordinador congela contratos antes de delegar.
- Ningun agente repite auditorias completas ya validadas sin cambio relacionado.
- Cada agente recibe solo tarea, archivos, contrato e invariantes necesarios.
- Los resumentes deben ser estructurados y cortos: cambios, pruebas, riesgos, siguiente paso.
- El agente de testing mantiene independencia y no aprueba su propio codigo.
- Si dos ramas necesitan el mismo archivo, se serializan mediante el coordinador.

# Criterio de cierre del roadmap

- Riesgos altos mitigados o aceptados explicitamente.
- Evidencia de pruebas vinculada en cada tarea.
- Documentacion backend/frontend actualizada.
- Commits por modulo, sin cambios mezclados.
- Pendientes externos claramente bloqueados y con responsable.

# Revision final de despliegue actualizada el 2026-08-24

La evidencia y el checklist operativo quedaron consolidados en
`docs/revision_seguridad_despliegue.md`.
Las condiciones de aprobacion separadas entre desarrollo y servidor quedaron
definidas en `tasks/in-progress/security-deployment-acceptance.md`.

Bloqueantes confirmados antes de datos reales:

- HTTPS confiable y redireccion desde HTTP.
- aislamiento multi-UCT con pertenencia y alcance definidos.
- provision, permisos, rotacion y responsables de secretos en el servidor.

Controles presentes que requieren validacion en el host final:

- backend, PostgreSQL y Redis sin puertos publicados en Compose productivo;
- JWT firmado, issuer/audience y expiracion configurables;
- refresh token `HttpOnly`, `Secure`, rotativo, revocable y validado por origen;
- CORS restrictivo, headers defensivos, rate limiting y errores genericos.
