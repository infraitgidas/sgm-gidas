# ESPECIFICACIONES DE DESARROLLO
## Sistema GIUCT — Gestión Integral de Unidades Científicas Tecnológicas

> *Para equipos de 2–3 estudiantes de 3er año · Formato User Story + Caso de Uso + Rúbrica de Competencias*  
> *Universidad Tecnológica Nacional · Agosto 2026*

| Campo | Detalle |
|---|---|
| **Proyecto** | GIUCT — Sistema de gestión de actividades I+D+i para UCT de UTN |
| **Audiencia** | Estudiantes de 3er año, Ingeniería en Sistemas / Tecnicatura / Licenciatura |
| **Modalidad** | Equipos de 2–3 personas por módulo, con integración al final del cuatrimestre |
| **Stack sugerido** | Java/Python/Node.js + PostgreSQL + HTML/CSS/JS o framework frontend simple |
| **Metodología** | Scrum simplificado: sprints de 2 semanas, demo al final de cada sprint |
| **Formato de spec.** | User Story (US) + Caso de Uso (CU) + Rúbrica de competencias por módulo |

---

## Cómo leer este documento

Cada módulo tiene tres componentes que el equipo debe trabajar juntos:

- **User Stories (US-XXX):** describe QUÉ necesita el usuario y POR QUÉ. Son el punto de partida para planificar el sprint.
- **Casos de Uso (CU-XXX):** describe CÓMO debe comportarse el sistema paso a paso. Son la guía para implementar y probar.
- **Rúbrica de competencias:** criterios con los que el docente evaluará el trabajo entregado. Leela antes de empezar, no después.

> ⚙ **CONVENCIÓN:** Los campos marcados con `*` son obligatorios en el sistema. Un campo obligatorio que el sistema permita dejar vacío es un **defecto de validación** — debe aparecer en los tests.

| Símbolo | Significado |
|---|---|
| ✅ | Criterio de aceptación verificable mediante test o inspección visual |
| ⚠ | Regla de negocio importante — si se ignora, el módulo falla en la demo |
| 🔗 | Dependencia con otro módulo — coordinar con el equipo responsable |
| 📝 | Nota técnica de implementación — sugerencia del arquitecto/docente |
| 🎯 | Competencia profesional que esta tarea desarrolla |

---

# MÓDULO 0 — Autenticación, Roles y Permisos

**Equipo:** Transversal (integra con todos los módulos)  
**Descripción:** Base de seguridad del sistema. Sin este módulo operativo, ningún otro puede integrarse correctamente.

---

## User Stories

### US-001 · Registro e inicio de sesión de usuario

| Campo | Valor |
|---|---|
| **Como** | administrador del sistema |
| **Quiero** | registrar nuevos usuarios con email, contraseña y rol asignado |
| **Para que** | el sistema controle quién puede acceder a cada módulo |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado un usuario nuevo, cuando el admin completa nombre, email institucional y rol, entonces el sistema crea la cuenta y envía confirmación.
- **AC-2** — Dado un usuario registrado, cuando ingresa sus credenciales correctas, entonces el sistema le otorga acceso al menú según su rol.
- **AC-3** — Dado un usuario con credenciales incorrectas, cuando intenta ingresar 3 veces consecutivas, entonces el sistema bloquea la cuenta por 15 minutos.
- **AC-4** — Dado un usuario autenticado, cuando cierra sesión, entonces su token queda inválido y no puede reutilizarse.

> 📝 **Nota técnica:** Usar hashing bcrypt para contraseñas. NO almacenar contraseñas en texto plano. Token de sesión con expiración de 8 horas.

---

### US-002 · Control de acceso por rol

| Campo | Valor |
|---|---|
| **Como** | sistema |
| **Quiero** | verificar que cada usuario solo acceda a las pantallas y operaciones de su rol |
| **Para que** | no haya acceso no autorizado a datos sensibles |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 5 |

**Criterios de aceptación:**

- **AC-1** — Dado un usuario con rol Investigador, cuando intenta acceder al módulo financiero, entonces el sistema muestra "Acceso denegado" y lo redirige.
- **AC-2** — Dado un usuario con rol Director, cuando accede al sistema, entonces puede ver todos los módulos de su UCT.
- **AC-3** — Dado un usuario con rol Becario, cuando inicia sesión, entonces solo puede ver su propia ficha y sus tareas asignadas.
- **AC-4** — Dado cualquier usuario, cuando intenta acceder a una URL protegida sin sesión activa, entonces el sistema lo redirige al login.

> 🔗 **Nota de integración:** Todos los módulos deben verificar el rol del usuario logueado antes de mostrar cualquier formulario de creación o edición.

---

## Casos de Uso

### CU-001 — Iniciar sesión

| Campo | Detalle |
|---|---|
| **Actor(es)** | Usuario (cualquier rol) |
| **Disparador** | El usuario ingresa sus credenciales en el formulario de login |
| **Precondición** | El usuario tiene una cuenta activa en el sistema |

**Flujo principal:**

1. El usuario navega a la pantalla de login.
2. Ingresa email institucional y contraseña.
3. Hace clic en "Ingresar".
4. El sistema verifica credenciales contra la base de datos.
5. El sistema genera un token de sesión y redirige al dashboard según el rol.

**Flujo alternativo / excepciones:**

- **A1** — Si las credenciales son incorrectas → el sistema muestra mensaje de error sin indicar cuál campo falló.
- **A2** — Si el usuario lleva 3 intentos fallidos → el sistema bloquea la cuenta y muestra instrucciones para desbloqueo.
- **A3** — Si el email no existe en el sistema → mismo mensaje de error genérico (no revelar que el email no existe).

| **Postcondición** | El usuario accede al dashboard con las opciones correspondientes a su rol. |
|---|---|

---

## 📊 Rúbrica — Módulo 0: Seguridad y Autenticación

| Competencia | Insuficiente (0–4) | Básico (5–6) | Esperado (7–8) | Avanzado (9–10) |
|---|---|---|---|---|
| Hashing de contraseñas | Contraseñas en texto plano | Usa MD5 o SHA1 sin salt | Usa bcrypt con salt | bcrypt + políticas de caducidad de contraseña |
| Control de acceso por rol (RBAC) | Sin restricciones de acceso | Restricción solo en frontend (bypasseable por URL) | Verificación en backend en cada endpoint | Middleware de autorización reutilizable + tests de penetración básicos |
| Manejo de sesiones | Sin expiración de sesión | Expiración implementada pero no probada | Expiración + invalidación al cerrar sesión | Refresh token + logs de acceso auditables |
| Tests de seguridad | Sin tests | 1–2 tests manuales documentados | Tests automáticos de los 4 criterios de aceptación | Tests de SQL injection y XSS básicos incluidos |

---

# MÓDULO C — Gestión de Recursos Humanos (RRHH)

**Equipo:** Equipo A (2–3 personas)  
**Descripción:** Módulo central del sistema. Todas las entidades (becas, proyectos, publicaciones) referencian personas cargadas aquí.

---

## User Stories

### US-010 · Alta de persona en el sistema

| Campo | Valor |
|---|---|
| **Como** | administrativo de la UCT |
| **Quiero** | registrar los datos personales, académicos e investigativos de un nuevo integrante |
| **Para que** | el sistema tenga un directorio unificado de toda la gente de la UCT |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 13 |

**Criterios de aceptación:**

- **AC-1** — Dado el formulario de alta de persona, cuando completo todos los campos obligatorios (`*`) y guardo, entonces el sistema crea el registro y muestra un mensaje de éxito con el ID asignado.
- **AC-2** — Dado el formulario de alta, cuando dejo vacío un campo marcado (`*`), entonces el sistema no guarda y muestra el error junto al campo faltante.
- **AC-3** — Dado que ingreso un DNI ya existente en el sistema, cuando intento guardar, entonces el sistema rechaza el alta con el mensaje "Ya existe una persona con ese DNI".
- **AC-4** — Dado que un docente dicta 3 materias, cuando cargo sus datos, entonces puedo agregar múltiples filas de cargo+materia+dedicación sin límite fijo.
- **AC-5** — Dado un investigador con categoría UTN, cuando cargo su categoría, entonces el sistema también registra la fecha de obtención y el número de resolución.
- **AC-6** — Dado que la persona tiene pasaporte, cuando marco "Sí tiene pasaporte", entonces el formulario muestra los campos de número y fecha de vencimiento.

> 📝 **Nota técnica:** Modelar la relación Persona–Materia como tabla intermedia (N:M). Una persona puede tener múltiples cargos/materias/dedicaciones.

---

### US-011 · Búsqueda y consulta de personas

| Campo | Valor |
|---|---|
| **Como** | cualquier usuario autenticado |
| **Quiero** | buscar personas por nombre, DNI o categoría de investigador |
| **Para que** | encontrar rápidamente a un integrante sin navegar toda la lista |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado el buscador de personas, cuando ingreso un texto parcial del nombre, entonces el sistema muestra todas las coincidencias en tiempo real (o al presionar buscar).
- **AC-2** — Dado el buscador, cuando filtro por "Categoría UTN = B", entonces el sistema muestra solo las personas con esa categoría.
- **AC-3** — Dado el resultado de búsqueda, cuando hago clic en una persona, entonces veo su ficha completa con todos sus datos.
- **AC-4** — Dado el listado de personas, cuando hago clic en "Exportar CSV", entonces descargo un archivo con todos los registros visibles.

> 🔗 **Nota de integración:** Este buscador debe poder integrarse como campo de autocompletar en los módulos de Becas y PIDs.

---

### US-012 · Gestión de estado activo/inactivo

| Campo | Valor |
|---|---|
| **Como** | director de la UCT |
| **Quiero** | marcar una persona como inactiva cuando deja de pertenecer a la UCT |
| **Para que** | el sistema mantenga el historial sin perder datos históricos |
| **Prioridad** | 🟡 MEDIA |
| **Story Points** | 5 |

**Criterios de aceptación:**

- **AC-1** — Dado un integrante activo, cuando el director lo marca como "Inactivo" con una fecha y motivo, entonces la persona no aparece en búsquedas de "solo activos" pero sí en búsquedas históricas.
- **AC-2** — Dado un integrante inactivo vinculado a un PID en curso, cuando intento asignarlo a otro PID, entonces el sistema advierte "Esta persona está inactiva. ¿Desea continuar?".
- **AC-3** — ⚠ La baja lógica NUNCA elimina el registro. Los datos históricos deben conservarse.

---

## Casos de Uso

### CU-010 — Registrar nueva persona

| Campo | Detalle |
|---|---|
| **Actor(es)** | Administrativo, Director |
| **Disparador** | El usuario selecciona "Nueva persona" en el menú de RRHH |
| **Precondición** | El usuario tiene rol Administrativo o Director. La persona a registrar no existe en el sistema. |

**Flujo principal:**

1. El usuario hace clic en "Nueva persona".
2. El sistema muestra el formulario con todas las secciones: datos personales, cargo docente, categorías investigador.
3. El usuario completa los campos obligatorios (`*`): nombres, apellidos, DNI, CUIL, email personal, celular, horas semanales de investigación.
4. El usuario agrega opcionalmente: pasaporte, cargo+materia (puede agregar varias), categorías de investigador con fecha y resolución.
5. El usuario hace clic en "Guardar".
6. El sistema valida todos los campos obligatorios y la unicidad del DNI.
7. El sistema guarda el registro y muestra el ID asignado y un resumen de los datos cargados.

**Flujo alternativo / excepciones:**

- **A1** — Si un campo obligatorio está vacío → el sistema resalta el campo en rojo y muestra "Campo requerido".
- **A2** — Si el DNI ya existe → el sistema muestra "DNI duplicado" con un enlace a la ficha existente.
- **A3** — Si el CUIL tiene formato inválido → el sistema muestra "CUIL inválido" (validar XX-XXXXXXXX-X).

| **Postcondición** | La persona queda registrada con estado "Activo" y puede ser referenciada desde otros módulos. |
|---|---|

---

## 📊 Rúbrica — Módulo RRHH: Gestión de Datos y Validaciones

| Competencia | Insuficiente (0–4) | Básico (5–6) | Esperado (7–8) | Avanzado (9–10) |
|---|---|---|---|---|
| Validaciones de formulario (cliente + servidor) | Sin validaciones | Validaciones solo en HTML (bypasseables) | Validaciones en frontend + backend, mensajes claros por campo | Validaciones + feedback visual inmediato + tests automáticos de cada regla |
| Modelo de datos (persona y sus relaciones) | Todo en una tabla plana | Tabla persona con columnas de texto libre para cargos | Tablas normalizadas: Persona, CargoMateria, CategoriaInvestigador | Modelo normalizado + historial de cambios de categoría con timestamps |
| Funcionalidad de búsqueda y filtros | Sin búsqueda, solo listado completo | Búsqueda por un campo con LIKE exacto | Búsqueda parcial por nombre/DNI + filtro por categoría | Búsqueda combinada + exportación CSV + paginación |
| Baja lógica (sin pérdida de datos) | La baja elimina el registro (DELETE) | Campo "eliminado" sin fecha ni motivo | Estado activo/inactivo con fecha y motivo | Estado + auditoría de quién realizó la baja + advertencia en módulos dependientes |

---

# MÓDULO 2 — Gestión de PIDs e Iniciativas de Innovación

**Equipo:** Equipo B (2–3 personas)  
**Descripción:** Core del sistema. Gestiona el ciclo de vida completo de los Proyectos de Investigación & Desarrollo homologados por la SCyTP-UTN.

---

## User Stories

### US-020 · Creación de un nuevo PID

| Campo | Valor |
|---|---|
| **Como** | director de la UCT |
| **Quiero** | registrar un PID con todos sus datos básicos, tipo y equipo de trabajo |
| **Para que** | el sistema cuente con información completa para generar informes anuales |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 13 |

**Criterios de aceptación:**

- **AC-1** — Dado el formulario de PID, cuando selecciono el tipo (TC/EC/PP/PIDA/PIDA-TEEI) y completo los datos obligatorios, entonces el sistema crea el PID con estado inicial "Formulado".
- **AC-2** — Dado el formulario de PID, cuando en el campo "Director del proyecto" empiezo a escribir un nombre, entonces el sistema sugiere personas ya cargadas en RRHH.
- **AC-3** — Dado que la persona buscada no existe en RRHH, cuando intento asignarla como directora, entonces el sistema muestra "Persona no encontrada. Cárguela primero en el módulo RRHH".
- **AC-4** — Dado un PID guardado, cuando agrego un integrante al equipo de trabajo, entonces el sistema registra el rol (Director/Codirector/Investigador/Becario) y el período de participación.
- **AC-5** — ⚠ El período del PID debe estar entre 12 y 36 meses. La prórroga puede extenderlo 12 meses más, pero debe registrarse con justificación.

> 🔗 **Nota de integración:** Depende del Módulo C (RRHH). Todos los integrantes del equipo deben existir previamente en el padrón de personas.

---

### US-021 · Gestión del ciclo de vida del PID

| Campo | Valor |
|---|---|
| **Como** | director de la UCT |
| **Quiero** | avanzar el estado de un PID a través de sus etapas |
| **Para que** | el sistema refleje en qué fase se encuentra cada proyecto en todo momento |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado un PID en estado "Formulado", cuando el director lo marca como "Enviado a evaluación SCyTP", entonces el sistema registra la fecha de envío.
- **AC-2** — Dado un PID en estado "Enviado", cuando llega la resolución de homologación, entonces el administrador puede marcarlo como "Homologado" ingresando el número de resolución.
- **AC-3** — Dado un PID "Homologado", cuando el director lo activa, entonces pasa a "En ejecución" y el sistema registra la fecha de inicio efectiva.
- **AC-4** — Dado un PID "En ejecución" con más de 12 meses, cuando el director carga un informe anual de avance, entonces el PID muestra la fecha del último informe.
- **AC-5** — ⚠ Un PID no puede pasar a "Cerrado" sin tener al menos un informe anual registrado si su duración supera los 12 meses.

> 📝 **Nota técnica:** Implementar como máquina de estados. Estados posibles:  
> `Formulado → En Evaluación → Homologado → En Ejecución → Cerrado → Evaluado Externamente`  
> No toda transición es válida (ej: no se puede pasar de Formulado a Cerrado directamente).

---

### US-022 · Registro de iniciativas de innovación

| Campo | Valor |
|---|---|
| **Como** | director de la UCT |
| **Quiero** | registrar iniciativas de innovación sin homologación con datos similares a los PIDs |
| **Para que** | el sistema gestione también la actividad no financiada de la UCT |
| **Prioridad** | 🟡 MEDIA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado el módulo de iniciativas, cuando selecciono "Nueva iniciativa", entonces el formulario muestra los mismos campos que un PID EXCEPTO los de financiamiento (secciones 15 y 16 del formulario PID).
- **AC-2** — Dado una iniciativa guardada, cuando la vinculo a un PID existente como "antecedente", entonces el sistema registra la relación.
- **AC-3** — Dado el listado de proyectos, cuando filtro por "Tipo = Iniciativa de Innovación", entonces veo solo las iniciativas separadas de los PIDs.

---

## Casos de Uso

### CU-020 — Crear nuevo PID

| Campo | Detalle |
|---|---|
| **Actor(es)** | Director, Administrativo |
| **Disparador** | El director selecciona "Nuevo PID" en el módulo de investigaciones |
| **Precondición** | El usuario tiene rol Director o Administrativo. Existe al menos una persona en RRHH. |

**Flujo principal:**

1. El usuario selecciona "Nuevo PID".
2. Selecciona el tipo de PID del menú desplegable: TC / EC / PP / PIDA / PIDA-TEEI.
3. Selecciona el Programa I&D+i de la SCyTP al que pertenece (lista de los 13 programas).
4. Completa los campos obligatorios: título del proyecto, palabras clave, objetivos generales.
5. En el campo "Director del proyecto" busca y selecciona una persona del padrón RRHH.
6. Agrega los integrantes del equipo, asignando rol y período a cada uno.
7. Ingresa las fechas de inicio y fin previstas (duración 12–36 meses).
8. Hace clic en "Guardar como borrador" o "Enviar a evaluación".
9. El sistema guarda el PID con el estado correspondiente y muestra un resumen.

**Flujo alternativo / excepciones:**

- **A1** — Si la fecha de fin es anterior a la de inicio → error "La fecha de fin debe ser posterior al inicio".
- **A2** — Si la duración supera 36 meses → error "La duración máxima de un PID es 36 meses".
- **A3** — Si el director no existe en RRHH → el campo de búsqueda muestra "Sin resultados" y un botón "Ir a RRHH a cargar la persona".

| **Postcondición** | El PID queda registrado con estado "Formulado" y es visible en el listado de proyectos de la UCT. |
|---|---|

---

## 📊 Rúbrica — Módulo 2: Modelado de dominio y máquina de estados

| Competencia | Insuficiente (0–4) | Básico (5–6) | Esperado (7–8) | Avanzado (9–10) |
|---|---|---|---|---|
| Modelo de datos del PID | Un solo formulario sin relaciones | PID con FK a persona directora únicamente | PID + tabla intermedia EquipoDeTrabajo (rol, período) + FK tipo/estado | Modelo completo + tabla de historial de cambios de estado con timestamp y usuario |
| Implementación del ciclo de vida (estados) | Sin gestión de estados | Campo estado sin restricciones de transición | Transiciones válidas controladas (no se puede ir de Formulado a Cerrado) | Máquina de estados documentada + tests de cada transición válida e inválida |
| Autocompletar / búsqueda en RRHH | Input de texto libre sin validación | Búsqueda manual con botón "buscar" | Autocompletar que busca en el padrón de personas | Autocompletar + validación que el resultado proviene del padrón (no texto libre) |
| Reglas de negocio (duración, prórroga) | Sin validaciones de fechas | Validación solo que fecha fin > fecha inicio | Validación de rango 12–36 meses + prórroga controlada de 12 meses | Validaciones + alerta automática cuando el PID está a 30 días de vencer |

---

# MÓDULO C.b — Formación Académica y Becas

**Equipo:** Equipo C (2–3 personas)  
**Descripción:** Gestiona tesistas, proyectos finales, pasantías y becas de alumnos/graduados vinculadas a los PIDs de la UCT.

---

## User Stories

### US-030 · Alta de tesista de posgrado

| Campo | Valor |
|---|---|
| **Como** | coordinador de becas / director |
| **Quiero** | registrar a un tesista de posgrado con su director, carrera y vinculación a un PID o iniciativa |
| **Para que** | el sistema refleje el vínculo entre la formación académica y la actividad investigativa de la UCT |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado el formulario de tesista de posgrado, cuando completo nombre, carrera, universidad, título de tesis, director y la vinculación a un PID, entonces el sistema guarda el registro.
- **AC-2** — Dado que el título de la tesis aún no está definido, cuando ingreso la temática principal en el campo título, entonces el sistema acepta ese texto como título provisional.
- **AC-3** — Dado el formulario, cuando en el campo "Director" busco una persona, entonces el sistema busca tanto en el padrón interno de RRHH como permite ingresar un director externo (con nombre y universidad).
- **AC-4** — Dado un tesista guardado, cuando consulto el listado filtrado por "Tipo = Doctorado", entonces aparece en la lista.

> 🔗 **Nota de integración:** El campo "Vinculación con PID o Iniciativa" debe mostrar un selector de los proyectos activos cargados en el Módulo 2.

---

### US-031 · Alta de beca para alumno

| Campo | Valor |
|---|---|
| **Como** | coordinador de becas |
| **Quiero** | registrar una beca asignada a un alumno con su financiador, monto y plan de trabajo |
| **Para que** | el sistema controle el estado y vencimiento de cada beca vigente |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 13 |

**Criterios de aceptación:**

- **AC-1** — Dado el formulario de beca alumno, cuando completo todos los campos obligatorios (`*`) incluido el plan de trabajo, entonces el sistema guarda la beca.
- **AC-2** — Dado el campo "Con financiamiento = Sí", cuando lo selecciono, entonces el formulario despliega: agente financiador`*`, módulos de beca, monto por módulo, cantidad de meses, monto total calculado automáticamente.
- **AC-3** — El monto total debe calcularse automáticamente: `monto_modulo × cantidad_modulos × cantidad_meses`. El usuario no lo ingresa a mano.
- **AC-4** — Dado una beca guardada, cuando la fecha de fin está a menos de 30 días, entonces el sistema muestra una alerta visual en el listado.
- **AC-5** — Dado el plan de trabajo, cuando agrego una actividad con duración estimada, entonces el sistema la registra y permite agregar más actividades ilimitadas.

> 📝 **Nota técnica:** El plan de trabajo puede modelarse como una tabla hija de la beca: `Beca 1→N Actividad(descripción, duración_semanas, estado)`.

---

## Casos de Uso

### CU-031 — Registrar beca de alumno

| Campo | Detalle |
|---|---|
| **Actor(es)** | Coordinador de becas, Director |
| **Disparador** | El coordinador selecciona "Nueva beca" > "Beca Alumno" |
| **Precondición** | El alumno ya existe en el padrón de RRHH. Existe al menos un PID activo al que asignar la beca. |

**Flujo principal:**

1. El coordinador selecciona "Nueva Beca para Alumno".
2. Busca y selecciona al alumno del padrón de RRHH.
3. Selecciona si la beca tiene financiamiento (Sí/No).
4. Si Sí: completa agente financiador, cantidad de módulos, monto por módulo, cantidad de meses. El sistema calcula y muestra el monto total.
5. Completa horas semanales, proyecto asignado, período (desde–hasta), coordinador del becario.
6. Agrega el plan de trabajo: hace clic en "Agregar actividad", ingresa descripción y duración, repite para cada actividad.
7. Hace clic en "Guardar".
8. El sistema valida campos obligatorios y guarda la beca con estado "Activa".

**Flujo alternativo / excepciones:**

- **A1** — Si no selecciona un alumno del padrón → error "Debe seleccionar una persona registrada en RRHH".
- **A2** — Si la fecha de fin es anterior a la fecha de inicio → error de fechas.
- **A3** — Si el plan de trabajo está vacío → error "Debe ingresar al menos una actividad en el plan de trabajo".

| **Postcondición** | La beca queda registrada y aparece en el listado de becas activas con indicador de vencimiento si corresponde. |
|---|---|

---

## 📊 Rúbrica — Módulo C.b: Relaciones entre entidades y reglas de negocio

| Competencia | Insuficiente (0–4) | Básico (5–6) | Esperado (7–8) | Avanzado (9–10) |
|---|---|---|---|---|
| Modelo de datos (beca y plan de trabajo) | Plan de trabajo como texto libre | Tabla beca con campo "actividades" como texto largo | Beca + tabla Actividad hija (1:N) con descripción y duración | Modelo completo + estado por actividad (pendiente/en curso/completada) |
| Cálculo automático de monto total | El usuario ingresa el monto total a mano | Cálculo en frontend sin validación en backend | Cálculo en backend + mostrado en pantalla antes de guardar | Cálculo + recálculo automático al cambiar cualquier campo componente + test |
| Vinculación formación–PID | Sin vinculación | Campo de texto libre para escribir el PID | Selector de PIDs activos del Módulo 2 (FK) | FK controlada + alerta si el PID al que está vinculado pasa a Cerrado |
| Alerta de vencimiento | Sin alertas | La fecha de fin se muestra pero sin resaltar | Indicador visual de "próximo a vencer" (< 30 días) | Indicador + ordenamiento por urgencia + filtro "solo vencidos" y "próximos a vencer" |

---

# MÓDULO 4 — Gestión de Fuentes de Financiamiento y Rendición de Cuentas

**Equipo:** Equipo D (2–3 personas)  
**Descripción:** Registra ingresos y egresos por inciso, mantiene saldos actualizados y permite rendir cuentas de cada fuente de financiamiento.

---

## User Stories

### US-040 · Registro de ingresos y egresos por inciso

| Campo | Valor |
|---|---|
| **Como** | administrativo de la UCT |
| **Quiero** | registrar un ingreso de fondos en un inciso específico del Programa 18 o fuente propia |
| **Para que** | el sistema mantenga el saldo actualizado de cada inciso en tiempo real |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado el módulo de financiamiento, cuando registro un ingreso con monto, fecha, fuente, inciso y responsable, entonces el saldo de ese inciso aumenta automáticamente.
- **AC-2** — Dado un inciso con saldo $0, cuando registro un egreso mayor al saldo disponible, entonces el sistema advierte "Saldo insuficiente en este inciso" y no permite guardar.
- **AC-3** — Dado el historial de movimientos, cuando filtro por inciso y período, entonces veo todos los ingresos y egresos con el saldo acumulado.
- **AC-4** — ⚠ El sistema debe soportar montos en pesos (ARS) y en dólares (USD). Cada movimiento registra la moneda y el tipo de cambio del día.

> 📝 **Nota técnica:** Modelar: `Inciso(código, nombre) ← FinanciamientoFuente(tipo) ← Movimiento(ingreso/egreso, monto, moneda, tipo_cambio, fecha, responsable)`. El saldo se calcula sumando movimientos — **NO** se almacena como campo editable.

---

### US-041 · Rendición de cuentas

| Campo | Valor |
|---|---|
| **Como** | director de la UCT / administrativo |
| **Quiero** | ver un resumen de ingresos y egresos por fuente de financiamiento y por inciso en un período dado |
| **Para que** | la UCT pueda rendir cuentas a la SCyTP con datos precisos y sin recalcular manualmente |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado el módulo de rendición, cuando selecciono una fuente de financiamiento y un período, entonces el sistema muestra: saldo inicial, total ingresos, total egresos, saldo final.
- **AC-2** — Dado el reporte de rendición, cuando hago clic en un egreso, entonces veo el detalle: fecha, monto, moneda, tipo de cambio, responsable, descripción.
- **AC-3** — Dado el reporte, cuando hago clic en "Exportar PDF", entonces el sistema genera un documento con encabezado de la UCT, período y tabla de movimientos.
- **AC-4** — Dado que tengo movimientos en dólares, cuando veo el resumen, entonces el sistema muestra tanto el monto en moneda original como su equivalente en pesos según el tipo de cambio registrado.

---

## Casos de Uso

### CU-040 — Registrar movimiento financiero

| Campo | Detalle |
|---|---|
| **Actor(es)** | Administrativo, Director |
| **Disparador** | El usuario accede al módulo de financiamiento y selecciona "Nuevo movimiento" |
| **Precondición** | Existen al menos un inciso y una fuente de financiamiento cargados en el sistema. |

**Flujo principal:**

1. El usuario selecciona "Nuevo movimiento".
2. Selecciona el tipo: Ingreso o Egreso.
3. Selecciona la fuente de financiamiento (Programa 18 / Producidos propios / Otra fuente).
4. Selecciona el inciso correspondiente (lista de incisos disponibles).
5. Ingresa: monto, moneda (ARS/USD), tipo de cambio del día (si es USD), fecha, descripción del concepto, responsable.
6. El sistema calcula el saldo proyectado y lo muestra antes de guardar.
7. El usuario confirma y hace clic en "Guardar movimiento".
8. El sistema actualiza el saldo disponible del inciso.

**Flujo alternativo / excepciones:**

- **A1** — Si es Egreso y el monto supera el saldo disponible → aviso de saldo insuficiente, pide confirmación explícita para continuar o cancela.
- **A2** — Si el tipo de cambio no es ingresado para movimientos en USD → error "El tipo de cambio es obligatorio para movimientos en USD".

| **Postcondición** | El movimiento queda registrado en el historial. El saldo del inciso queda actualizado en la pantalla de resumen. |
|---|---|

---

## 📊 Rúbrica — Módulo 4: Modelado financiero e integridad de datos

| Competencia | Insuficiente (0–4) | Básico (5–6) | Esperado (7–8) | Avanzado (9–10) |
|---|---|---|---|---|
| Modelo de datos financiero (sin saldo almacenado) | Saldo como campo editable en una tabla | Saldo actualizado con UPDATE después de cada movimiento | Saldo calculado como SUM() de movimientos (no almacenado), integridad garantizada | Saldo calculado + vista/view en BD + tests que verifican consistencia del saldo |
| Manejo de multimoneda | Solo pesos, sin tipo de cambio | Campo moneda pero sin tipo de cambio histórico | Monto + moneda + tipo_cambio por movimiento | Conversión calculada dinámicamente + muestra en ambas monedas en reportes |
| Reporte de rendición de cuentas | Sin reporte | Listado sin subtotales por inciso | Reporte con subtotales por inciso, saldo inicial y final | Reporte exportable a PDF con encabezado de la UCT + filtro por período y fuente |
| Validación de saldo suficiente | Permite egresos sin verificar saldo | Aviso pero permite continuar sin confirmación | Aviso con confirmación explícita requerida | Aviso + log del caso + reporte de "incisos en rojo" en el dashboard |

---

# MÓDULO 6 — Informes y Dashboard Ejecutivo

**Equipo:** Equipo E (2–3 personas)  
**Descripción:** Solo consultas y visualizaciones. Sin ABMC. Consolida datos de todos los módulos para apoyar la toma de decisiones.

---

## User Stories

### US-060 · Dashboard de estado general de la UCT

| Campo | Valor |
|---|---|
| **Como** | director de la UCT |
| **Quiero** | ver en una sola pantalla el estado actual de proyectos, personas y financiamiento |
| **Para que** | tener una visión ejecutiva sin necesidad de navegar módulo por módulo |
| **Prioridad** | 🔴 ALTA |
| **Story Points** | 13 |

**Criterios de aceptación:**

- **AC-1** — Dado el dashboard, cuando inicio sesión como Director, entonces veo: cantidad de PIDs por estado (gráfico de torta o barras), cantidad de becas activas, saldo total disponible por fuente de financiamiento.
- **AC-2** — Dado el dashboard, cuando hago clic en un segmento del gráfico de PIDs "En ejecución", entonces el sistema me lleva al listado de PIDs filtrado por ese estado.
- **AC-3** — Dado el dashboard, cuando hay una beca próxima a vencer (< 30 días), entonces aparece una alerta destacada en la pantalla principal.
- **AC-4** — Dado el dashboard, cuando hay un PID que ya debería haber presentado su informe anual, entonces aparece resaltado como "Informe pendiente".

> 📝 **Nota técnica:** Para los gráficos usar Chart.js o una librería similar incluida vía CDN. El dashboard es de solo lectura — no debe tener formularios de edición.

---

### US-061 · Informe de investigador

| Campo | Valor |
|---|---|
| **Como** | director / administrativo |
| **Quiero** | generar un informe individual de un investigador para un período dado |
| **Para que** | poder reportar la actividad de cada integrante a la SCyTP y al Programa de Incentivos |
| **Prioridad** | 🟡 MEDIA |
| **Story Points** | 8 |

**Criterios de aceptación:**

- **AC-1** — Dado el módulo de informes, cuando selecciono "Informe Investigador", elijo la persona y el período (bimestral/trimestral/anual), entonces el sistema genera un reporte con: proyectos en los que participó, publicaciones del período, becarios coordinados, horas declaradas.
- **AC-2** — Dado el informe generado, cuando hago clic en "Exportar", entonces puedo descargarlo en formato PDF o Excel.
- **AC-3** — Dado el informe, cuando un campo no tiene datos para el período seleccionado, entonces muestra "Sin actividad registrada" en lugar de dejar la sección en blanco.

---

## Casos de Uso

### CU-060 — Consultar dashboard ejecutivo

| Campo | Detalle |
|---|---|
| **Actor(es)** | Director, Administrativo (solo lectura) |
| **Disparador** | El usuario con rol Director accede al sistema |
| **Precondición** | El sistema tiene al menos un PID, una beca y un movimiento financiero cargados. |

**Flujo principal:**

1. El usuario inicia sesión con rol Director.
2. El sistema muestra el dashboard como pantalla principal.
3. El dashboard carga y muestra: panel de PIDs por estado (gráfico), panel de becas activas (cantidad + próximas a vencer), panel financiero (saldo por fuente).
4. El usuario puede hacer clic en cualquier panel para ver el detalle correspondiente.
5. El usuario puede cambiar el período de visualización (mes actual / cuatrimestre / año).

**Flujo alternativo / excepciones:**

- **A1** — Si no hay datos cargados para el período seleccionado → cada panel muestra "Sin datos para este período" en lugar de errores.
- **A2** — Si el usuario tiene rol Investigador → ve solo su panel personal, no el financiero.

| **Postcondición** | El usuario vio el estado actual de su UCT de forma visual y sin necesidad de buscar en cada módulo. |
|---|---|

---

## 📊 Rúbrica — Módulo 6: Consultas, reportes y visualización de datos

| Competencia | Insuficiente (0–4) | Básico (5–6) | Esperado (7–8) | Avanzado (9–10) |
|---|---|---|---|---|
| Consultas SQL y agregaciones | Datos del dashboard obtenidos con múltiples SELECT simples en el código | Consultas con JOIN básicos pero sin optimización | Consultas con JOIN, GROUP BY, COUNT, SUM correctamente estructuradas | Consultas optimizadas + vistas (SQL VIEWs) para los reportes más usados + índices correctos |
| Visualización de datos (gráficos) | Sin gráficos, solo tablas de números | Un gráfico estático (imagen o hardcodeado) | Gráficos dinámicos conectados a datos reales (Chart.js o similar) | Gráficos dinámicos + interactivos (click para drill-down) + filtro por período |
| Exportación de informes | Sin exportación | Exportación como texto plano o pantalla de impresión | Exportación a PDF con datos correctamente formateados | PDF + Excel + encabezado institucional + datos de la UCT autogenerados |
| Integración de datos entre módulos | El dashboard muestra datos de un solo módulo | Dashboard con datos de 2 módulos sin consistencia | Dashboard integra datos de RRHH, PIDs, Becas y Finanzas correctamente | Integración + manejo de casos borde (datos vacíos, períodos sin actividad) |

---

# Criterios de Integración entre Módulos

Los equipos trabajan en paralelo, pero el sistema final debe estar integrado. Estos son los contratos de integración que cada equipo debe respetar:

| Equipo origen | Dato compartido | Equipo destino | Contrato mínimo |
|---|---|---|---|
| **Equipo A (RRHH)** | ID persona + nombre completo | Equipos B, C, D | API o función `getPersonas()` que devuelve lista de personas activas |
| **Equipo B (PIDs)** | ID PID + título + estado | Equipos C, D, E | API o función `getPIDsActivos()` que devuelve PIDs en estado "En ejecución" |
| **Equipo C (Becas)** | Becas activas por PID | Equipo E (Dashboard) | API o función `getBecastActivas()` con fecha de vencimiento |
| **Equipo D (Finanzas)** | Saldo por inciso | Equipo E (Dashboard) | API o función `getSaldosPorInciso()` con monto y moneda |

> ⚠ **CONTRATO DE INTEGRACIÓN:** Cada equipo debe documentar y publicar su interfaz de integración al inicio del Sprint 2, para que los demás equipos puedan depender de ella. Acordar el formato (función compartida, endpoint REST, o tabla de BD con acceso directo) con el docente.

---

# Criterios de Entrega del Proyecto Integrado

Al finalizar el cuatrimestre, la entrega grupal del sistema integrado se evaluará sobre los siguientes criterios:

| Criterio | Peso | Descripción |
|---|---|---|
| **Funcionalidad MVP** | 35% | Los módulos M0, RRHH, PIDs, Becas y Finanzas básicas funcionan de punta a punta sin errores críticos. |
| **Integración entre módulos** | 20% | El autocompletar de personas funciona en PIDs y Becas. El dashboard muestra datos reales de todos los módulos. |
| **Calidad de código y modelo de datos** | 20% | BD normalizada (sin redundancias), código con nombres significativos, sin lógica de negocio en la vista. |
| **Tests y validaciones** | 15% | Los criterios de aceptación de al menos 3 US por módulo están cubiertos por tests automáticos o manuales documentados. |
| **Demo y defensa oral** | 10% | Cada integrante puede explicar las decisiones de diseño y código de su módulo. Se evalúa comprensión, no solo que "funcione". |

---

*— Fin del documento —*
