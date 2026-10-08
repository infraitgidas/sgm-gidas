# Informes por período (ISS-85)

## Vistas y permisos

`InformesHome`, `InformeForm` e `InformeDetalle` atienden las rutas
`/informes/:tipo`, `/informes/:tipo/nuevo`, `/informes/:tipo/:id` y
`/informes/:tipo/:id/editar`. `tipo` vale `investigadores`, `pid` o `uct`.
El menú y las rutas solo están disponibles para `GESTOR`; el backend vuelve
a validar el permiso. En el menú, la navegación y el listado, `pid` se
presenta como "Proyectos".

El home usa la tabla compartida con nueve informes por página, filtro por
Memoria, acciones de ver, editar y eliminar, y mensajes visibles. El listado
muestra título, fecha de realización, autor y período; en Investigadores y
Proyectos, una fila desplegable carga bajo demanda las copias de los registros
vinculados. El detalle muestra
contenido completo, copias de los registros vinculados, nombre y correo de
UCT, tarjeta de período, fecha y autor, auditoría e historial de tres eventos
por página. Editar solo aparece en informes activos.

## Formulario y relaciones

El formulario permite elegir una Memoria y redactar título, resumen,
actividades, resultados y observaciones. Investigadores y proyectos se
buscan mediante candidatos paginados del período; la selección múltiple se
conserva al cambiar de página y se envía junta al guardar. Desde la búsqueda,
la flecha hacia abajo enfoca la primera opción; las flechas, Inicio y Fin
recorren opciones, y Enter o espacio las seleccionan. UCT no tiene selector.

El alta vuelve al home con `successMessage`. La edición compara con el
detalle original y envía solo diferencias reales; sin cambios, no llama al
backend. Una edición guardada vuelve al detalle. Los errores de campo se
asocian a `error.details.fields` y los errores generales muestran un mensaje
accionable. Los vínculos se muestran con los datos copiados al guardar; los
cambios posteriores en el origen no sustituyen esa copia.

## Código y contrato

`services/informesService.ts` define tipos TypeScript y llamadas HTTP;
`hooks/useInformes.ts` encapsula consultas de listas, detalle, historial y
candidatos; `utils/validation.ts` valida el formulario y calcula diferencias.
El contrato completo de payloads, errores y reglas está en
`backend/modules/informes/README.md`. Los informes PID comparten el período
de la Memoria, y el cierre de un proyecto requiere uno que lo vincule en el
período que contiene su fecha de cierre. Guardar el informe no cierra el
proyecto: solo habilita el cierre explícito cuando se elige una fecha válida.

## Validación

La implementación pasó 191 pruebas frontend, `npm run typecheck` y build de
producción. El usuario validó el comportamiento y aprobó la presentación
de los tres tipos de informe; los ajustes posteriores pasaron 12 pruebas
dirigidas y una nueva comprobación de tipos.

## Títulos de detalle (ISS-88)

En InformeDetalle, las etiquetas de datos y los encabezados de tarjetas
usan peso seminegrita y color pizarra oscuro para distinguirse del contenido.
La disposición, los textos, las acciones y el contrato permanecen iguales.
