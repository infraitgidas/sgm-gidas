# Análisis de Usabilidad/UX y Trazabilidad RF/RNF/Reglas de Negocio — SGM-GIDAS vs GIUCT

**Fecha:** 2026-09-04
**Autor:** infraestructura GIDAS
**Alcance:** frontend (`frontend/src`), backend (`backend`), documentación de dominio (`docs/definicion_Dominio_GUICT`)

> Nota: el sistema implementado (SGM-GIDAS — Gestión de Memorias Académicas) es una reinterpretación del dominio GIUCT con foco en "Memorias Académicas", no un cumplimiento 1:1 de la especificación de cátedra. La trazabilidad refleja ambos sentidos: módulos que superan el spec y módulos que quedan cortos.

---

## Introducción — Qué va a leer y cómo interpretarlo

Este documento es un trabajo de revisión sobre el sistema GIDAS. Su propósito es doble: por un lado, evaluar **cómo se siente y qué tan simple resulta usar la aplicación** para quienes trabajan con ella todos los días; por el otro, **contrastar lo que el sistema hace hoy contra lo que el proyecto GIUCT definió originalmente** que debía hacer. En otras palabras: primero miramos la experiencia de uso, después miramos si lo construido responde a lo planificado y a las reglas propias del dominio.

**La primera parte (Sección 1)** trata la usabilidad y la experiencia de usuario. Está escrita usando criterios profesionales reconocidos (las heurísticas de Nielsen, que son los principios clásicos de buen diseño de interfaz) y pautas de accesibilidad. Se divide en tres bloques:

- **Fortalezas:** lo que el sistema hace bien, con la evidencia técnica de cada punto. Es la parte que permite reconocer el trabajo logrado.
- **Gaps identificados:** los puntos débiles, cada uno con una **severidad** que va de 0 a 4. La escala es simple: 0 es un detalle casi imperceptible y 4 un problema grave que bloquea el uso. Ninguno de los hallazgos de este informe llega a 4; la mayoría están en nivel 1–2, es decir, mejoras valiosas pero no urgencias que impidan operar.
- **Priorización:** cómo conviene encarar las mejoras, de las más rápidas y baratas a las más estratégicas.

**La segunda parte (Secciones 2.1 a 2.3)** es la trazabilidad de requerimientos. Para leerla sin formación técnica conviene aclarar tres términos:

- **Requerimientos funcionales (RF):** las funciones concretas que el sistema debe ofrecer (por ejemplo, "cargar una persona" o "registrar un proyecto de investigación").
- **Requerimientos no funcionales (RNF):** atributos de calidad del sistema, como seguridad, rendimiento, disponibilidad o facilidad de mantenimiento.
- **Reglas de negocio (RN):** las condiciones y restricciones propias del mundo real que el sistema debe respetar (por ejemplo, "ninguna baja puede eliminar datos históricos" o "un proyecto no puede cerrarse sin su informe anual").

La **especificación GIUCT** es el documento de referencia del dominio, elaborado en el marco de la cátedra, que describe módulo por módulo qué debería hacer el sistema. La trazabilidad no es otra cosa que el **seguimiento uno a uno de cada exigencia de esa especificación hacia el sistema construido**, para saber con precisión qué está cubierto y qué no.

Cada tabla se interpreta con un semáforo de estados:

| Estado | Significado |
|---|---|
| ✅ | Implementado y verificado |
| 🟡 | Implementado parcialmente (existe, pero le faltan partes) |
| ❌ | No implementado |
| ⚠ | No constatado en el código (requiere verificación a fondo) |
| n/a | No aplica (el dominio se reinterpretó y la regla perdió sentido) |

Una aclaración importante para no leer mal este informe: **GIDAS no es una copia literal de la especificación GIUCT, sino una reinterpretación con alcance propio** (foco en memorias académicas, seguridad y auditoría). Por eso la tabla no es una lista de "faltas": hay módulos donde el sistema hace **más** de lo pedido (como informes y trazabilidad) y otros donde la especificación exigía procesos complejos que hoy no están (como el ciclo de vida formal de los proyectos de investigación). En la Sección 3, "Lectura ejecutiva", se resume en pocas líneas el estado general, para quien quiera ir directo a las conclusiones sin leer las tablas completas.

---

## 1. Usabilidad y Experiencia de Usuario

### 1.1 Fortalezas

| Fuerza | Evidencia |
|---|---|
| Consistencia de patrones: 15+ módulos repiten el tríada Home → Form → Detalle con mismas convenciones (paginación 9/pág, Auditoría + Historial en detalle, Volver/Editar) | `ProyectosHome`, `PersonalHome`, `HistorialCambiosCard`, etc. |
| Prevención de errores: dirty-check en edición (no llama al backend sin cambios reales), confirm dialogs, validación por campo que se limpia al corregir | `ProyectosForm` (`initialPayload`), `ConfirmDialog`, `Field` |
| Visibilidad del estado: toasts success/error con auto-dismiss, botones con "Guardando..." + disabled, `role="status"`, evento `gidas:session-expired` | `SuccessToast`, `ProtectedRoute`, `lib/http.ts` |
| Control del usuario: Volver omnipresente, navegación contextual (búsqueda/memoria), Esc cierra sidebar/popovers/calendario | `memoriaNavigation.ts`, `Sidebar`, `Calendar` |
| Reconocimiento: badges de estado, placeholders, filtros con contador | `Tarjeta`, homes |
| Eficiencia: búsqueda global con sugerencias, exportación CSV/PDF/Excel | `SearchPage`, `useExportacion` |
| Accesibilidad base: `role="alert"`, `aria-live`, `aria-expanded/label`, teclado completo en date picker | `Field`, `Calendar`, `AppLayout` |
| Rendimiento percibido: lazy-loading en todas las rutas, skeletons en búsqueda | `main.tsx`, `SearchPage` |

### 1.2 Gaps por heurística de Nielsen (severidad 0–4)

| Heurística | Sev. | Problema | Recomendación |
|---|---|---|---|
| Reconocimiento en vez de recuerdo | 2 | Sin breadcrumbs: en flujos largos (personal → detalle → editar; memoria → versión) se pierde posición | Breadcrumb en rutas de 3+ niveles |
| Consistencia y estándares | 2 | `focus` vs `focus-visible` inconsistente; ruta `proyectos/editar/:id` contradice `/:id/editar`; ruta muerta `trabajosCientInv` + `App.tsx` stub | Unificar, normalizar rutas, eliminar código muerto |
| Ayuda a reconocer errores | 2 | Mensajes base genéricos sin acción sugerida | Mensajes accionables según contexto (ej. "Ir a RRHH" en autocompletados de proyectos) |
| Visibilidad del estado | 2 | "Cargando..." texto plano en casi todos los homes/detalles; exportaciones sin progreso | Skeleton genérico + progreso en exportaciones |
| Consistencia visual | 1 | Gradientes de KPI del dashboard rompen el minimalismo institucional | Unificar tokens de color |

### 1.3 Accesibilidad

| Issue | Sev. | Detalle |
|---|---|---|
| Sin foco-trap en modales/paneles | 2 | `ConfirmDialog`, `AlertDialog`, paneles de filtros no encierran el foco ni lo restauran al cerrar |
| Paneles de filtros sin semántica de diálogo | 2 | Faltan `role="dialog"` y `aria-modal` |
| Errores de campo sin `aria-describedby` | 2 | El error no se asocia al campo para lectores de pantalla |
| Tarjetas clickeables sin semántica de link | 2 | `Tarjeta` sin rol de link/botón |
| Color como único canal parcial | 1 | Badges con texto pero estado comunicado por color |
| Sin skip-link | 1 | El teclado recorre todo el sidebar antes del contenido |
| i18n | — | Textos hardcodeados es-AR; aceptable para la audiencia actual |

### 1.4 Priorización

- Quick wins: unificar `focus-visible`; `aria-describedby` en `Field`; `role="dialog"` en filtros; eliminar rutas muertas; normalizar ruta de edición.
- Mediano: breadcrumbs; foco-trap + restauración de foco; skeleton genérico; semántica de link en tarjetas.
- Estratégico: undo post-eliminación; ayuda contextual; mensaje "Ir a RRHH" en autocompletados; i18n si crece el alcance.

---

## 2. Trazabilidad RF / RNF / Reglas de Negocio vs `docs/definicion_Dominio_GUICT`

> El PDF v1.1 describe módulos de alto nivel sin RF/RNF numerados; las US/CU del `.md` aportan RF con criterios de aceptación y reglas marcadas con ⚠. Las RNF se infieren de notas técnicas del spec y de `AGENTS.md`.

### 2.1 RF por módulo

| Módulo spec | Estado | Implementación real |
|---|---|---|
| M0 — Autenticación, roles | ✅ (reinterpretado) | `auth` completo (JWT + refresh hasheado HttpOnly, `primer_login`, guards). Roles ADMIN/GESTOR/LECTURA vs Director/Administrativo/Investigador/Becario del spec |
| M.C.a — Personas | ✅ | `personal`: becario/investigador/PTAA/profesional, categorías, cargos/dedicaciones |
| M.C.b — Formación académica | 🟡 Parcial | Tipos de formación dinámicos; sin entidades dedicadas tesista/tesina/PS/PP/ensayo |
| M.C.c — Becas | 🟡 Parcial | `becas` + asignaciones con `monto_percibido`; faltan plan de trabajo 1:N y monto calculado automático |
| M1 — Transferencia | ✅ | `transferencias` + `adoptantes` N:M, tipos de contrato dinámicos |
| M2 — PIDs e iniciativas | 🟡 Parcial | `proyectos` + tipos dinámicos + participaciones; SIN máquina de estados (solo activo/cerrado), sin duración 12–36, sin prórroga, sin homologación |
| M3 — Adquisiciones | 🟡 Parcial | `equipamiento` ✅ · bibliografía → `documentación_bibliográfica` ✅ · licencias ❌ · servicios ❌ |
| M4 — Financiamiento | 🟡 Parcial | Incisos, fuentes, `erogaciones`, saldo por fuente en dashboard; faltan movimientos ingreso/egreso, rendición, multimoneda ARS/USD, saldo calculado SUM |
| M5 — Comunicaciones científicas | ✅ (ampliado) | `produccion` supera el spec: reuniones, revistas, distinciones, divulgación, propiedad, docencia, documentación |
| M6 — Informes y Dashboard | 🟡 Parcial | Dashboard KPI + Recharts ✅, exportación memorias ✅; faltan informes de investigador/PID/UCT por período |

### 2.2 RNF

| RNF | Estado | Evidencia |
|---|---|---|
| Seguridad (hashing, RBAC backend, headers, secretos) | ✅ Fuerte | JWT HS256 + refresh hasheado, guards por rol, rate limits (10/min, 5/h, 90/min), security headers, `_require_production_security` |
| Sesión (expiración + invalidación logout) | ✅ | Refresh con rotación y limpieza |
| Bloqueo 3 intentos → 15 min | 🟡 | Hay rate limiting (mecanismo distinto al bloqueo de cuenta del spec) |
| Auditoría y trazabilidad | ✅ (supera spec) | Soft delete, `AuditoriaCampo`, historial por entidad, snapshot de 16 colecciones al cerrar memoria |
| Rendimiento | 🟡 | Paginación 9/pág ✅, lazy-loading ✅, JOIN/GROUP BY en dashboard ✅; índices/vistas no constatados |
| Disponibilidad/Infraestructura | ✅ | Docker + Compose + healthchecks + nginx + CI/CD |
| Mantenibilidad | ✅ | Modular monolith, 58 archivos de test, documentación por módulo |
| Usabilidad | 🟡 | Consistencia excelente; gaps de accesibilidad y orientación (sección 1) |
| Internacionalización | ❌ | Hardcodeada es-AR |

### 2.3 Reglas de negocio

| # | Regla | Fuente spec | Estado | Evidencia |
|---|---|---|---|---|
| RN-01 | DNI único | US-010 AC-3 | ⚠ No constatado | Sin validación de unicidad DNI en `personal_service` |
| RN-02 | CUIL formato XX-XXXXXXXX-X | CU-010 A3 | ❌ | No constatado |
| RN-03 | Cargo/materia/dedicación múltiples (N:M) | US-010 AC-4 | ✅ | Modelo personal |
| RN-04 | Pasaporte condicional | US-010 AC-6 | 🟡 | No verificado |
| RN-05 | Categoría investigador con fecha + resolución | US-010 AC-5 | ✅ | Catálogo `categoria_utn` |
| RN-06 | Baja lógica NUNCA elimina | US-012 AC-3 ⚠ | ✅ | `AuditMixin` soft delete |
| RN-07 | Persona inactiva → advertencia al asignar | US-012 AC-2 | ✅ | `_validar_investigador_activo` |
| RN-08 | Duración PID 12–36 meses | US-020 AC-5 ⚠ | ❌ | No hay validación de rango |
| RN-09 | Prórroga máx 12 meses justificada | US-020 AC-5 ⚠ | ❌ | No existe |
| RN-10 | PID no a Cerrado sin informe anual (>12 m) | US-021 AC-5 ⚠ | ❌ | Cierre simplificado |
| RN-11 | Máquina de estados con transiciones válidas | US-021 | ❌ | Solo activo/cerrado |
| RN-12 | Iniciativa sin secciones financiamiento | US-022 AC-1 | n/a | Dominio reinterpretado |
| RN-13 | Director/integrante existe en RRHH | US-020 AC-3 | ✅ | Validación + autocompletar |
| RN-14 | Monto beca = módulos × monto × meses (auto) | US-031 AC-3 ⚠ | ❌ | No existe el cálculo |
| RN-15 | Plan de trabajo ≥ 1 actividad | CU-031 A3 | ❌ | No existe como entidad hija |
| RN-16 | Alerta vencimiento beca < 30 días | US-031 AC-4 | ❌ | No constatado |
| RN-17 | Adoptante ≠ Demandante; UCT no ambas | PDF M1 | ❌ | `demandante` texto libre sin validación |
| RN-18 | Egreso > saldo → saldo insuficiente | US-040 AC-2 ⚠ | ❌ | Sin saldo por inciso |
| RN-19 | Multimoneda ARS/USD + tipo de cambio | US-040 AC-4 ⚠ | ❌ | No constatado |
| RN-20 | Saldo = SUM de movimientos | US-040 nota | ❌ | No hay movimientos |
| RN-21 | Login 3 intentos → bloqueo 15 min | US-001 AC-3 | 🟡 | Rate limit distinto |
| RN-22 | Login mensajes genéricos | CU-001 A1/A3 | ✅ | Mensaje genérico |
| RN-23 | Token 8h + logout invalida | US-001 AC-4 | ✅ | Refresh rotation |
| RN-24 | RBAC backend por endpoint | Rúbrica M0 | ✅ | Guards por rol |
| RN-25 | Paginación homes 9 / historial 3 | AGENTS.md | ✅ | `ITEMS_PER_PAGE=9` |
| RN-26 | Edición solo diffs; sin cambios no llamar backend | AGENTS.md | ✅ | Dirty-check |
| RN-27 | Detalle: Auditoría + Historial + Volver + Editar | AGENTS.md | ✅ | Patrón uniforme |
| RN-28 | Un coordinador activo por proyecto | backend | ✅ | `_validar_unico_coordinador_activo` |
| RN-29 | No vincular a proyecto cerrado | backend | ✅ | `_proyecto_esta_cerrado` |
| RN-30 | Una sola UCT/grupo activo | backend | ✅ | `grupo_service` |
| RN-31 | Mandatos directivos no superpuestos | backend | ✅ | `directivo_service` |
| RN-32 | Memoria única activa, anual, máquina abierta/revisión/cerrada, snapshot 16 colecciones | backend | ✅ | `memoria_service` — supera al spec |
| RN-33 | Erogación número único por grupo | backend | ✅ | `erogacion_service` |
| RN-34 | Docencia: investigador inmutable, historial versionado | backend | ✅ | `actividad_docencia_service` |
| RN-35 | Beca única por fuente (case-insensitive) | backend | ✅ | `_validar_beca_unica` |

---

## 3. Lectura ejecutiva

- **UX:** base sólida; la consistencia de patrones es superior a la media. Los gaps son de orientación (breadcrumbs), accesibilidad avanzada (foco-trap, `aria-describedby`, semántica de diálogos) y feedback más rico. Nada bloquea el uso; todo es incremental.
- **Trazabilidad:** el núcleo administrativo-personal está implementado con solvencia (RRHH, transferencias, producción científica, memorias, auditoría/seguridad superando el spec). Los huecos estructurales están en: (1) ciclo de vida de PID, (2) financiamiento real, (3) becas según spec, (4) adquisiciones incompletas (licencias, servicios).