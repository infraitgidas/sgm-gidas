---
id: auth-refresh-cookie-http-only
title: Migrar sesion a refresh cookie HttpOnly y access token en memoria
status: finished
area: frontend-backend
module: auth
priority: critica
risk_level: alto
execution_order: 1
created_at: 2026-08-12
updated_at: 2026-08-13
source: security-audit
commit_sugerido: "fix(auth): proteger renovacion de sesion con cookie http only"
owner: coordinator-agent
blocked_by: []
related_files:
  - backend/config.py
  - backend/modules/auth/controllers/auth_controller.py
  - backend/modules/auth/services/auth_service.py
  - backend/modules/auth/models/refresh_token_session.py
  - backend/tests/test_auth_refresh_tokens.py
  - frontend/src/lib/http.ts
  - frontend/src/modules/auth/services/authService.ts
  - frontend/src/context/AuthContext.tsx
---

# Riesgo y motivo de prioridad

El access token y el refresh token se persisten en `localStorage`. Cualquier XSS
que logre ejecutarse en el origen podria leer ambos y mantener acceso hasta que
la sesion sea revocada. La auditoria actual no encontro sinks XSS directos, por
lo que no existe evidencia de explotacion inmediata, pero el impacto potencial
justifica prioridad critica antes de ampliar integraciones o exposicion de red.

# Objetivo verificable

- Refresh token exclusivamente en cookie `HttpOnly`.
- Access token solo en memoria del proceso JavaScript.
- Ningun token en `localStorage`, `sessionStorage`, URL, logs o respuestas de error.
- Rotacion y revocacion actuales preservadas.
- Renovacion transparente tras recargar la pagina.
- Proteccion CSRF coherente con el uso de cookies.

# Decisiones que debe cerrar el coordinador antes de implementar

1. Cookie: nombre `gidas_refresh`, `HttpOnly`, `Secure` en produccion,
   `SameSite=Lax` o `Strict`, `Path=/api/v1/auth`, sin `Domain` salvo necesidad real.
2. Refresh y logout aceptan la cookie; se elimina el fallback JSON en produccion.
3. Login y refresh devuelven solo access token y usuario; nunca refresh token.
4. Access token vive en memoria. Al cargar la SPA, se intenta un refresh con cookie.
5. CSRF: validar `Origin`/`Referer` en refresh y logout y añadir token CSRF si se
   habilitan endpoints de negocio autenticados directamente por cookie.
6. Duracion, renovacion, borrado y reloj deben usar una unica fuente de configuracion.
7. Compatibilidad local: cookie no segura solo fuera de produccion y documentada.

# Organizacion multiagente

Usar cuatro agentes. Tres es el minimo; el cuarto mejora independencia de pruebas.

## Agente 0: coordinador e integrador

Responsabilidad exclusiva:

- leer esta tarea y las reglas del proyecto completas
- congelar el contrato HTTP antes de habilitar implementacion
- definir matriz de endpoints, cookies, estados y errores
- asignar archivos sin solapamiento
- revisar mensajes entre agentes y resolver incompatibilidades
- integrar backend y frontend solo cuando sus pruebas aisladas pasan
- ejecutar validacion final y actualizar documentacion/tarea

No debe reescribir simultaneamente archivos asignados a los agentes 1 o 2.

Entregables iniciales para ahorrar tokens:

- tabla corta request/response de login, refresh y logout
- nombres exactos de cookie y cabeceras
- lista de invariantes de seguridad
- orden de merge: backend, frontend, pruebas integradas

## Agente 1: backend auth

Archivos exclusivos: `backend/config.py`, auth controller/service/model y tests backend.

Trabajo:

- emitir, rotar y borrar cookie con atributos por ambiente
- retirar refresh token de JSON
- leer cookie en refresh/logout
- mantener hash, familia, reutilizacion, revocacion y expiracion
- validar origen para operaciones basadas en cookie
- devolver errores seguros sin revelar estado interno
- agregar pruebas de atributos, rotacion, replay, logout y expiracion
- actualizar documentacion backend

No modifica frontend ni Nginx.

## Agente 2: frontend auth

Archivos exclusivos: cliente HTTP, auth service/context y pruebas frontend si existen.

Trabajo:

- eliminar tokens y usuario sensible persistidos en almacenamiento web
- mantener access token en memoria
- usar `credentials: "same-origin"` donde corresponda
- hidratar sesion mediante refresh al iniciar
- preservar cola unica de refresh y reintento maximo de una vez
- evitar loops entre 401, refresh y logout
- sincronizar logout entre pestanas sin transmitir tokens, por ejemplo BroadcastChannel
- actualizar documentacion frontend

No modifica backend ni Nginx.

## Agente 3: testing y seguridad independiente

Empieza en paralelo sin editar archivos de agentes 1 y 2.

Fase inicial:

- preparar matriz de pruebas y casos de abuso
- revisar contrato propuesto y señalar ambiguedades
- diseñar verificaciones de cookies, CSRF, XSS, replay y concurrencia

Fase posterior a integracion:

- ejecutar tests backend y typecheck/build frontend
- inspeccionar headers reales a traves de Nginx
- confirmar ausencia de tokens en storage, JSON, URL y logs
- probar recarga, multiples pestanas, refresh concurrente, expiracion y logout
- realizar una revision final independiente del diff

Solo agrega tests en archivos acordados o entrega hallazgos al coordinador.

# Secuencia de ejecucion

1. Coordinador cierra contrato e invariantes.
2. Agentes 1, 2 y 3 comienzan en paralelo.
3. Agente 1 entrega backend y pruebas aisladas.
4. Agente 2 entrega frontend compilable contra el contrato congelado.
5. Coordinador integra y resuelve diferencias, sin cambios de alcance silenciosos.
6. Agente 3 valida el flujo integrado y reporta fallos reproducibles.
7. Agentes responsables corrigen; agente 3 repite pruebas.
8. Coordinador cierra documentación, tarea y mensajes de commit.

# Criterios de aceptacion

- `document.cookie` no permite leer el refresh token.
- No existen tokens en localStorage/sessionStorage luego de login, refresh o reload.
- Login/refresh no incluyen refresh token en JSON.
- Cookie de produccion incluye `HttpOnly`, `Secure`, `SameSite` y `Path` restringido.
- Refresh rota token y rechaza reutilizacion de uno anterior.
- Logout revoca servidor y expira cookie incluso si el token ya no es valido.
- Recargar restaura sesion sin mostrar contenido protegido antes de validar.
- Dos refresh concurrentes no causan loops ni revocacion accidental.
- CSRF desde origen no autorizado es rechazado antes de rotar la sesion.
- Logs y errores no contienen cookies ni tokens.
- Tests backend, typecheck, build, Nginx y prueba manual son correctos.

# Riesgos de implementacion y mitigacion

- Bloqueo por `Secure` en desarrollo: configurar por ambiente, nunca degradar produccion.
- CSRF por cookie: restringir SameSite/origen y evaluar token CSRF.
- Carrera de rotacion: una sola promesa de refresh en frontend y transaccion backend.
- Loop 401: un solo reintento marcado por solicitud.
- Sesiones entre pestanas: comunicar solo eventos, nunca credenciales.
- Rollback: frontend y backend deben desplegarse como version compatible; documentar ventana.

# Presupuesto de contexto recomendado

- Coordinador: contrato, integracion y decisiones; evitar cargar servicios no relacionados.
- Backend: solo auth, config y tests asociados.
- Frontend: solo flujo auth y cliente HTTP.
- Testing: contrato, diffs finales y matriz de pruebas.

Cada agente debe enviar resumentes con: archivos, contrato asumido, pruebas, fallos y
pendientes. No debe pegar archivos completos ni repetir contexto ya congelado.

# Commits esperados

```text
fix(auth-backend): emitir refresh token mediante cookie http only
fix(auth-frontend): mantener tokens fuera del almacenamiento web
test(auth): validar cookies rotacion csrf y concurrencia
docs(auth): documentar contrato seguro de sesiones
```

# Cierre

Fecha: 2026-08-13

Implementado:

- refresh token en cookie `gidas_refresh` HttpOnly, SameSite=Lax y Path restringido
- atributo Secure obligatorio en produccion
- access token y usuario de sesion solo en memoria del frontend
- login, registro y refresh sin refresh token en JSON
- restauracion de sesion por refresh, rotacion y logout idempotente
- validacion estricta de Origin/Referer en refresh y logout
- coordinacion de refresh/logout concurrentes mediante single-flight, generacion de sesion y Web Locks
- rate limit dedicado de gateway para logout

Validaciones:

- backend focalizado: 13 pruebas correctas
- backend completo: 214 pruebas correctas
- frontend typecheck y build correctos
- Nginx produccion y desarrollo: sintaxis correcta
- `git diff --check`: correcto

Archivos principales modificados:

- `backend/config.py`
- `backend/modules/auth/controllers/auth_controller.py`
- `backend/modules/auth/services/auth_service.py`
- `backend/tests/test_auth_cookie_contract.py`
- `backend/tests/test_auth_refresh_tokens.py`
- `frontend/src/lib/http.ts`
- `frontend/src/modules/auth/services/authService.ts`
- `frontend/src/context/AuthContext.tsx`
- `nginx/default.conf`
- `nginx/default.dev.conf`

Riesgo residual:

- navegadores sin Web Locks dependen de la tolerancia del backend a renovaciones concurrentes
- la validacion manual completa en navegador sobre HTTPS queda ligada a la tarea `infra-https-lan-nginx`

## Mejoras introducidas

- Retira el refresh token del alcance de JavaScript y del storage del navegador.
- Reduce impacto de XSS y agrega protecciones de origen, cookie y coordinacion.
