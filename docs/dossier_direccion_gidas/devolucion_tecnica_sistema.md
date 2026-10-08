# Devolucion Tecnica del Sistema, Estado de Produccion y Estimacion de Recursos

> **Fecha:** 2026-08-27
> **Alcance:** Sistema de Gestion de Memorias Academicas (SGM-GIDAS)
> **Metodo:** Revision de repositorio, arquitectura, pruebas, configuración y documentacion operativa. No se modifico codigo.
> **Documento relacionado:** [Revision final de seguridad para despliegue](./revision_seguridad_despliegue.md), [Configuracion manual pendiente](./configuracion_manual_pendiente.md)

---

## 1. Resumen ejecutivo

El sistema es un monolito modular frontend/backend correctamente desacoplado, con una
postura de seguridad y trazabilidad inusualmente solida para su etapa de desarrollo.
La arquitectura de dominio (snapshots congelados por version de memoria, auditoria por
campo, historial por entidad, API versionada) es coherente y bien ejecutada en la
mayoria de los modulos.

**Veredicto general: APTO PARA ENTRAR EN FASE DE ACEPTACION** con condicion de
resolver 4 bloqueantes operativos antes de servir trafico real: HTTPS, rotacion de
secretos, decision sobre aislamiento multi-UCT y el ciclo de backup/restore. No
existen bloqueantes de arquitectura de codigo.

Para una operacion estable con 10 usuarios el costo de infraestructura es minimo:
una unica VM de 2 vCPU / 4 GB RAM / 40 GB SSD cubre holgadamente el escenario, con
backups y monitoreo simple. El costo no tecnico dominante es la disciplina operativa
(backups, parches, restores).

---

## 2. Evaluacion del sistema

### 2.1 Arquitectura

| Aspecto | Evaluacion |
|---|---|
| Separacion frontend/backend | Correcta. Contrato unico `{data, meta, error}` bajo `/api/v1`, header `API-Version: v1` garantizado por `shared/routes/versioning.py`. |
| Modularidad | 12 modulos espejo backend/frontend. `LazyBlueprints` con imports diferidos; `models_registry.py` unico punto de registro de modelos. |
| Modelo de dominio | Solido. Memoria -> versiones -> snapshots denormalizados por entidad (16 tipos) con regla de pertenencia temporal. Congelar version cerrada para exportacion es la decision correcta. |
| Paginacion | **Deuda conocida**: solo 1 controlador pagina en query (`cargo_controller.py`); el resto depende de un `after_request` legacy que pagina en memoria (carga full-table). Tolerable a 10 usuarios, critica al escalar. |
| Busqueda | Escaneo en memoria de 24 tipos con caps (`SEARCH_*`), sin FTS. Correcta para el volumen actual; reemplazar por FTS/Postgres cuando los datos crezcan. |

### 2.2 Funcionalidad

Cobertura funcional amplia y consistente con el dominio: auth con roles, gestion de
UCT/grupo, personal, produccion, proyectos, recursos, transferencia, catalogos,
memorias con exportacion Excel y busqueda global. El patron frontend
home/form/detalle con `HistorialCambiosCard` (3 items por pagina) esta aplicado en 15
pantallas de detalle.

**Brechas funcionales detectadas:**

- `Beca` carece de snapshot de memoria (unica entidad de contenido excluida del
  mecanismo de congelado).
- `Beca` y `Adoptante` no tienen UI dedicada (CRUD generico / selector dentro de
  transferencia, mientras el backend expone CRUD completo).
- Sin historial de campos: `grupo-utn`, `directivos`, `autores`, `adoptante`.
  El "Historial de directivos" del frontend es una lista de periodos, no eventos de
  auditoria (informacion engañosa si se lee como historial de cambios).
- No existe flujo de recuperacion de contrasena (configuracion SMTP inerte).

### 2.3 Seguridad

Controles implementados y verificados: JWT HS256 con issuer/audience, refresh
rotativo con `jti` y hash persistido, cookie `HttpOnly/Secure/SameSite=Lax` +
validacion Origin/Referer, CORS estricto sin comodines, headers defensivos + CSP en
Flask y Nginx, rate limiting doble (Nginx + Flask-Limiter/Redis), errores seguros
centralizados con `request_id`, excepciones de dominio tipadas, secretos con guardas
duras y soporte `*_FILE`, topologia con un unico puerto publicado, usuarios PG
separados con minimo privilegio y matriz IDOR/BOLA con pruebas negativas dinamicas.

**Pendientes de seguridad expresos:**

1. **HTTPS inactivo** — bloqueante. Nginx escucha en HTTP; cookie `Secure` y HSTS
   quedan condicionados a TLS.
2. **Aislamiento multi-UCT no implementado** — decision del 2026-08-22 diferida.
   GESTOR/LECTURA ven datos globales; la matriz IDOR/BOLA esta marcada "parcial" en la
   mayoria de entidades con `grupo_utn_id`.
3. **Secretos a rotar** — `SECRET_KEY`, `JWT_SECRET`, `REFRESH_SECRET` y
   `POSTGRES_*_PASSWORD` aparecieron en salidas diagnosticas
   (`configuracion_manual_pendiente.md:28-56`).

---

## 3. Evaluacion del desarrollo

### 3.1 Proceso y evidencia

- 140 commits en ~4 meses (2026-04-22 a 2026-08-27), mensajes Conventional Commits,
  CI que valida formato de commits.
- CI: unittest backend, test/typecheck/build frontend, `compose config --quiet`,
  validacion de topologia productiva y escaneo de secretos versionados.
- Gestion de tareas por directorio `tasks/` (finished/pendient) — buena disciplina
  de trazabilidad, aunque `tasks/` esta en `.gitignore` (estado local, no
  versionado) y existen **referencias rotas** a `tasks/in-progress/security-deployment-acceptance.md`
  y `tasks/pendient/security-multitenancy-uct.md` en tres documentos.

### 3.2 Calidad y testing

- Backend: 58 archivos de test, **316 casos** cubriendo reglas de negocio, auth,
  auditoria, snapshots (16 entidades), IDOR/BOLA dinamico, headers, topologia y
  errores. Los tests de snapshot no requieren DB real.
- Frontend: 6 archivos de test (21 specs) sobre logica pura e inspeccion estatica.
  **Sin tests de componentes UI ni e2e.**
- Gaps: sin tests dedicados para `autores`, `adoptante`, `directivos`, `cargo`,
  `grupo_utn`, `tipo_contrato`; sin integracion contra PostgreSQL real.

### 3.3 Deuda tecnica priorizada

1. **Contrato de errores de `auth` inconsistente** — validaciones colapsan a
   `INTERNAL_ERROR`/400 con mensaje generico (`auth_controller.py:183-184`,
   `AuthService` lanza `Exception` planas). Rompe la convencion del README e impide
   UX accionable en login/registro.
2. Paginacion en memoria (carga full-table) en todos los listados.
3. Beca sin snapshot; orquestacion de snapshots duplicada en `memoria_service.py`
   (2 listas de 16 llamadas).
4. `search_service.py` monolito de 1232 lineas con bloques casi identicos por tipo.
5. READMEs backend faltantes para `memorias`, `produccion`, `recursos`.

---

## 4. Gestion de la configuracion

**Fortalezas:**

- Plantillas `.env.example` / `.env.testing.example` / `.env.production.example`
  versionadas en backend y frontend; `.env*` ignorados por git.
- Guardas duras en `config.py`: rechazo de secretos placeholder/debiles (<32 chars),
  independencia de `SECRET_KEY`/`JWT_SECRET`/`REFRESH_SECRET`, CORS HTTPS sin
  comodin, `DATABASE_URL` y storage de rate-limit obligatorios. Soporte de secretos
  por archivo (`*_FILE`).
- Topologias Compose claramente separadas: `docker-compose.yml` (produccion,
  hardening: `read_only`, `cap_drop: ALL`, `pids_limit`, `no-new-privileges`,
  logging rotado, healthchecks) y `docker-compose.dev.yml` (override que publica
  puertos y monta codigo en vivo, explicitamente no apto para produccion).
- `migrate` como servicio efimero (roles + `flask db upgrade` + seed) previo a
  `backend`; healthcheck `/health/ready` comprueba PG + Redis antes de recibir
  trafico.
- Scripts de validacion de despliegue (`validate-vm-deployment.sh`,
  `smoke-vm-deployment.sh`).

**Debilidades (gestion de configuracion):**

| Tema | Estado | Riesgo |
|---|---|---|
| Secretos | `.env` en servidor, sin gestor centralizado (Vault/SOPS/1Password) | Medio: depende de disciplina manual; rotacion ya es necesaria |
| Infraestructura como codigo | Sin Ansible/Terraform; despliegue manual por SSH con scripts | Medio: sin reproduccion ni deteccion de drift |
| Backup/restore | Sin automatizacion versionada en el repo | **Alto para produccion** |
| Certificados TLS | Fuera del repo (proxy externo recomendado) | Alto hasta implementarse |
| Docs operativos | `despliegue_produccion.md`, `configuracion_manual_pendiente.md`, `revision_seguridad_despliegue.md` presentes, pero con referencias rotas a tasks | Bajo |
| CI/CD | CI completo; **sin CD** (deploy manual) | Bajo para el equipo actual |

---

## 5. Estado actual para produccion

### 5.1 Bloqueantes (impiden el go-live seguro)

1. **HTTPS/TLS** — sin TLS no tiene sentido servir la cookie de refresh con `Secure`
   ni HSTS. Implementar proxy externo (Nginx/Caddy/Apache o balanceador del proveedor)
   con certificados Let's Encrypt o institucional, y reenviar al Nginx interno.
   - *Estado 2026-08-28:* el **acceso público ya está cubierto por TLS** (dominio
     `gidas.frlp.utn.edu.ar` con wildcard `*.frlp.utn.edu.ar` de DigiCert + túnel
     Cloudflare `*.trycloudflare.com` de Google Trust). **La LAN interna** (`:8080` /
     `sgm.gidas.local`) sigue por **HTTP** → aviso "conexión no segura" esperado.
   - (Documentacion completa en `docs/despliegue_entrega_direccion.md`, secciones
     TLS y 5.3.)
2. **CORS para el acceso por túnel** (nuevo 2026-08-28) — el orígen del túnel
   Cloudflare (`https://thickness-…trycloudflare.com`) **no está en `FRONTEND_URLS`**;
   el backend no emite `Access-Control-Allow-Origin` para ese orígen → **el navegador
   bloquea el login por CORS** (funciona con curl, no en navegador). Bloquea el uso
   del túnel como vía normal. Fix: agregar el orígen (aditivo, con backup). **Diferido
   por coordinación** mientras el túnel use nombre temporal.
3. **Rotacion de secretos** — todos los secretos que aparecieron en diagnosticos
   deben rotarse antes de cargar cualquier dato real.
4. **Aislamiento multi-UCT** — decidir: implementarlo (decision diferida del
   2026-08-22) o documentar formalmente la aceptacion del riesgo con datos reales
   visibles para GESTOR/LECTURA.
5. **Ciclo de backup/restore** — definir y probar antes del go-live (ver seccion 6.3).

### 5.2 Requeridos antes del go-live (no bloqueantes, si recomendados)

- Automatizar la **purga diaria de sesiones refresh** vencidas (existe el comando
  `refresh_sessions`; falta el cron).
- Corregir el contrato de errores de `auth` (UX accionable en login/registro).
- Decidir el flujo de recuperacion de contrasena (SMTP o reseteo administrado).
- Eliminar referencias rotas a `tasks/` inexistentes en la documentacion.
- Validacion final en staging con datos de prueba antes de migrar a productivo.

### 5.3 Riesgo residual aceptable en el primer periodo

Con 10 usuarios y el volumen de datos esperado, las deudas de paginacion en memoria,
búsqueda sin FTS y falta de tests de componentes UI no representan riesgo inmediato.
Deben monitorearse y planificarse antes de superar ~50 usuarios concurrentes o un
volumen de datos que degrade las consultas.

---

## 6. Estimacion de recursos para operacion productiva (10 usuarios)

### 6.1 Perfil de carga asumido

- 10 usuarios institucionales; picos concurrentes realistas 4-6.
- Operacion tipica: formularios CRUD, consulta de historiales, busqueda global,
  gestion de memorias y exportaciones Excel puntuales.
- Carga estimada: del orden de decenas de requests/minuto en pico.

### 6.2 Infraestructura recomendada (una unica VM)

| Recurso | Recomendado | Justificacion |
|---|---|---|
| CPU | **2 vCPU** | Gunicorn actual: 3 workers / 2 threads. 2 vCPU da headroom para exports (openpyxl) y migraciones sin degradar la UI. |
| RAM | **4 GB** | PG 16 (~1 GB), Gunicorn (~0.75 GB), Redis (limit 128 MB), Nginx, sistema (~0.5 GB), headroom para exports y picos. 2 GB quedaria justo; 4 GB es comodo. |
| Disco | **40 GB SSD** | App + imagenes ~6-8 GB; datos estimados 1-3 GB/año (auditoria por campo + snapshots generan crecimiento lineal); logs rotados (10 MB x 5 por servicio); backups locales ~3-5x el tamaño de datos. |
| Red | 1 IP publica, 100 Mbps | Trafico irrelevante a este volumen; obligatorio puerto 443 + 80 para redireccion. |
| Virtualizacion | VM standard del proveedor institucional | No se justifica HA/Kubernetes a esta escala; un unico host con `restart: unless-stopped` alcanza. |

### 6.3 Almacenamiento y backups

- `pg_dump` full diario (comprimido) con retencion: 14 diarios, 4 semanales,
  12 mensuales.
- **Copia offsite** (rsync/borg a otro servidor o almacenamiento institucional);
  el backup local no es backup.
- **Drill de restore trimestral** y uno obligatorio antes del go-live.
- Volumen por dump estimado: decenas de MB; el costo es de disciplina, no de storage.

### 6.4 Monitoreo y observabilidad

- Uptime externo sobre `https://.../api/v1/health/live` (ya existe el endpoint).
- Metricas de host: CPU/RAM/disco via node_exporter/Netdata o script cron con
  alertas simples.
- Alertas minimas: disco > 80%, `health/ready` fallando, saturacion de memoria,
  pico de intentos de login fallidos (el rate limiting ya los limita y loguea).
- Logs: ya estructurados (JSON) con `request_id` y rotacion por servicio. Con un
  solo host, revisar via `docker logs` con retencion es suficiente; agregar
  recoleccion central solo si crece la flota.

### 6.5 Mantenimiento operativo (esfuerzo y cadencia)

| Actividad | Cadencia | Esfuerzo |
|---|---|---|
| Revision de backups y logs | Semanal | ~0.5 h |
| Parches de SO, actualizacion de imagenes Docker y dependencias (pip/npm audit) | Mensual | 2-4 h |
| Drill de restore + revision de seguridad | Trimestral | 2-4 h |
| Bugfixes y evolucion de modulos | Continuo | Variable (mayor al inicio) |

Rutina establecida estimada: **4-8 h/mes** hasta estabilizar, luego 2-4 h/mes.

### 6.6 Costos estimados

| Concepto | Rango |
|---|---|
| VPS/VM 2 vCPU / 4 GB / 40 GB SSD | USD 12-20/mes (cloud) o costo marginal ~0 en servidor institucional |
| Backup offsite | USD 2-5/mes o almacenamiento institucional existente |
| Dominio + TLS | Let's Encrypt gratuito; dominio institucional existente |
| **Total mensual** | **USD 15-25/mes** en cloud, o ~0 marginal en infraestructura UTN |

### 6.7 Umbrales de escala (referencia)

- **~50 usuarios concurrentes:** pasar paginacion a query en BD (deuda conocida),
  evaluar 4 vCPU / 8 GB y FTS para busqueda.
- **~100+ o multiples UCT con datos reales:** resolver aislamiento multi-UCT,
  evaluar PostgreSQL gestionado y separacion backend en 2 instancias con balanceo.

---

## 7. Plan de remediacion priorizado

| Prioridad | Accion | Categoria |
|---|---|---|
| P0 | HTTPS público (ya cubierto por dominio + Cloudflare); **LAN interna a HTTPS** | Seguridad |
| P0 | Habilitar **CORS del túnel** en `FRONTEND_URLS` (login por portal) + migrar a Named Tunnel | Funcionalidad |
| P0 | Rotar todos los secretos expuestos en diagnosticos | Seguridad |
| P0 | Definir ciclo de backup/restore + drill pre-go-live | Operacion |
| P0 | Decidir e implementar (o aceptar formalmente) aislamiento multi-UCT | Seguridad |
| P1 | Automatizar purga diaria de sesiones refresh | Operacion |
| P1 | Corregir contrato de errores del modulo `auth` | Calidad |
| P1 | Snapshot de `beca` + UI dedicada para becas y adoptantes | Funcionalidad |
| P1 | Corregir referencias rotas de `tasks/` en documentacion | Docs |
| P2 | Paginacion en query para listados principales | Performance |
| P2 | READMEs backend `memorias`/`produccion`/`recursos`; tests de componentes UI | Calidad |

---

## 8. Referencias

- `README.md` — estado declarado y convenciones.
- `docs/revision_seguridad_despliegue.md` — bloqueantes de seguridad.
- `docs/configuracion_manual_pendiente.md` — secretos y configuracion manual.
- `docs/despliegue_produccion.md` — guia operativa del servidor.
- `docker-compose.yml` / `docker-compose.dev.yml` — topologias productiva y dev.
- `backend/config.py` — guardas de configuracion.
- `backend/SECURITY_IDOR_BOLA.md` — matriz de autorizacion.
- `.github/workflows/ci.yml` — pipeline de integracion continua.