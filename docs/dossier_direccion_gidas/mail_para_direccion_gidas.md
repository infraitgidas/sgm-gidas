Asunto: Dossier de documentación técnica y análisis del sistema GIDAS

Estimados directores de GIDAS:

Por medio del presente se hace entrega del dossier consolidado de documentación técnica correspondiente al Sistema de Gestión de Memorias Académicas (SGM-GIDAS). El sistema se encuentra desplegado y operativo sobre la infraestructura del laboratorio, con acceso interno por LAN y acceso público a través del Portal GIDAS. Junto con el estado operativo, se incluyen los análisis de usabilidad, trazabilidad, seguridad y despliegue realizados, así como la documentación de operación y mantenimiento que respalda la continuidad del servicio.

---

RESUMEN TÉCNICO GENERAL

Para quienes quieran una primera idea sin entrar en los detalles técnicos: el sistema GIDAS es la herramienta digital con la que la UCT organiza su actividad diaria. En un mismo lugar conviven las personas que integran la unidad (investigadores, becarios y personal de apoyo), los proyectos de investigación, la producción científica (publicaciones, presentaciones, distinciones), las transferencias y convenios, los recursos y el financiamiento, y las memorias académicas anuales con su histórico completo. En lugar de papeles sueltos y planillas dispersas, todo queda registrado, ordenado y consultable desde una misma aplicación.

Por dentro, el sistema funciona como una oficina bien organizada con tres áreas que trabajan juntas. La primera es la cara visible: la pantalla que los usuarios ven y usan cada día, cuidada para que las tareas se hagan de forma simple y consistente (las mismas pantallas, los mismos botones y los mismos mensajes en todos los módulos). La segunda es la lógica del negocio: las reglas propias de la UCT, que el sistema valida y respeta automáticamente (por ejemplo, que una baja nunca borre datos históricos, o que cada cambio quede registrado con autor y fecha). La tercera es el archivo central: la base de datos donde se guarda toda la información de forma segura y ordenada.

La seguridad fue una prioridad desde el inicio. El acceso está controlado por perfiles: cada persona ve y modifica únicamente lo que le corresponde según su rol, y esa verificación ocurre también dentro del sistema, no solo en la pantalla. Las contraseñas se almacenan de forma protegida, las conexiones viajan cifradas (HTTPS) y el sistema cuenta con protecciones adicionales contra intentos de acceso indebido o uso abusivo. Además, cada acción importante deja una huella: quién la hizo, cuándo y qué cambió. Esa trazabilidad es la base de la Auditoría y del Historial de cambios que acompañan a cada registro.

La continuidad del servicio también está contemplada. Los datos se respaldan automáticamente todas las semanas y el respaldo llega por correo a los responsables, con un procedimiento probado para restaurarlos si alguna vez hiciera falta. La plataforma está desplegada sobre una infraestructura contenerizada y preparada para recuperarse ante fallos, con integración continua en desarrollo para que cada mejora del sistema pase por controles automáticos antes de llegar a producción.

En resumen: el sistema está en producción, operando con normalidad y con su documentación al día. El dossier que acompaña este correo no solo muestra lo construido, sino también lo que se revisó, lo que se corrigió y los caminos de mejora identificados — porque la gestión de la información de la UCT merece seguir creciendo con la misma solidez con la que arrancó.

---

A continuación se detallan los documentos incluidos, organizados por categoría.

---

ANÁLISIS Y EVALUACIÓN

1. analisis_ux_trazabilidad_giuct.md — Análisis de usabilidad y experiencia de usuario (heurísticas de Nielsen, accesibilidad, priorización de mejoras) y trazabilidad de requerimientos funcionales, no funcionales y reglas de negocio del sistema contra la especificación de dominio GIUCT. Incluye el estado de cumplimiento por módulo.

2. devolucion_tecnica_sistema.md — Evaluación técnica integral del sistema: arquitectura, funcionalidad, seguridad, calidad del código, testing, deuda técnica priorizada, gestión de configuración, estimación de recursos para operación con 10 usuarios y plan de remediación con bloqueantes identificados.

3. revision_seguridad_despliegue.md — Revisión de seguridad para despliegue: matriz de controles (HTTPS, JWT, CORS, headers defensivos, IDOR/BOLA, rate limiting, secretos), estado de cada control, bloqueantes y checklist de habilitación del servidor.

4. analisis_docker_produccion.md — Auditoría de los Dockerfiles y Docker Compose para producción: inventario de archivos auditados, buenas prácticas verificadas, hallazgos priorizados (seguridad, rendimiento, higiene) y estrategia de optimización multi-stage con plan de remediación.

---

DESPLIEGUE E INFRAESTRUCTURA

5. despliegue_entrega_direccion.md — Documento de entrega a la Dirección de GIDAS: estado del sistema desplegado, arquitectura del stack de contenedores, vías de acceso (LAN y Portal/Cloudflare), infraestructura, servicios activos, configuración de red y acceso, y acciones pendientes identificadas.

6. despliegue_produccion.md — Guía operativa completa de despliegue manual del sistema en servidor mediante Docker Compose: arquitectura, requisitos del servidor, configuración de seguridad, arranque, verificación técnica y funcional, operación cotidiana, actualización manual y recuperación ante fallos.

7. despliegue_20260827.md — Registro del despliegue productivo del 27 de agosto de 2026: incidencia resuelta durante el build (fuentes apt/HTTPS), optimizaciones aplicadas al stack Docker/Compose, configuración del alias DNS sgm.gidas.local y verificación de servicios.

---

OPERACIÓN Y MANTENIMIENTO

8. backups_semanal_gidas.md — Backup semanal automatizado de la base de datos PostgreSQL con envío por email a los responsables. Incluye configuración del cron, script de dump, script de envío SMTP, política de retención y procedimiento de restauración.

9. memorias_tecnica.md — Documentación técnica del módulo de Memorias: conceptos del dominio (memoria, versiones, snapshots), reglas de negocio, transiciones de estado, criterios de pertenencia temporal por entidad, endpoints, permisos por rol y restricciones de mantenimiento.

10. excel_memoria_template_summary.md — Análisis comparativo de la plantilla Excel institucional de memorias versus el exportador actual del sistema. Describe diferencias estructurales (estilos, merges, orden de secciones) y la estrategia de implementación recomendada para alinear ambos formatos.

11. configuracion_manual_pendiente.md — Listado de variables de configuración pendientes de agregar o corregir antes del go-live y relación de secretos comprometidos que deben renovarse, con las acciones de verificación posteriores a la rotación.

12. ci_cd.md — Estado de la integración continua (GitHub Actions) y entrega: workflow de validación por pull request, convención de mensajes de commit, estrategia de entrega inicial manual por SSH y configuración pendiente para un pipeline de CD futuro.

---

ESTADO Y SEGUIMIENTO

13. estado_repo_commits_pendientes.md — Estado del repositorio: commits creados localmente aún no publicados, cambios sin commitear correspondientes a optimizaciones y correcciones, y las vías disponibles para resolver la publicación.

14. sesion_trabajo_20260827.md — Registro detallado de la sesión de trabajo del 27 de agosto de 2026: despliegue inicial, resolución de incidencia de build, dos rondas de optimización Docker/Compose, configuración del alias DNS, baseline de datos y pendientes abiertos.

---

Quedo a disposición para profundizar en cualquiera de los temas aquí referidos, realizar una presentación detallada de cada documento o avanzar en la resolución de los pendientes identificados.

Saludos cordiales,

Emanuel - InfraIT- GIDAS