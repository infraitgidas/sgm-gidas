# Resumen Tecnico - Plantilla Excel de Memorias

## Archivos inspeccionados
- Generado actual: `memoria.xlsx`
- Plantilla de referencia: `DS2025 - UTN - PLANTILLA MEMORIAS.xlsx`

## Metodo de inspeccion
La inspeccion se hizo antes de modificar el exportador, usando scripts auxiliares para leer la estructura interna del `.xlsx`.

Scripts creados:
- [inspect_xlsx.py](/C:/Users/Benjamin/Sistema%20Gidas/backend/tools/inspect_xlsx.py:1)
- [inspect_xlsx.ps1](/C:/Users/Benjamin/Sistema%20Gidas/backend/tools/inspect_xlsx.ps1:1)

## Hallazgos sobre la plantilla

### Estructura general
- La plantilla tiene `2` hojas:
  - `Hoja1`
  - `Hoja2`
- La hoja principal usa rango efectivo `A1:L296`
- La segunda hoja esta vacia (`A1`)

### Estructura del archivo generado actual
- Tiene `1` sola hoja:
  - `Memorias`
- Usa rango efectivo `A1:L160`

## Comparacion estructural

### Estilos
Plantilla:
- `49` fuentes
- `10` fills
- `25` borders
- `314` `cellXfs`

Generado actual:
- `4` fuentes
- `4` fills
- `2` borders
- `12` `cellXfs`

Conclusión:
- el archivo actual es funcional, pero visualmente mucho mas simple
- la plantilla tiene un diseño considerablemente mas rico y rigidamente maquetado

### Celdas combinadas
Plantilla:
- `227` merges

Generado actual:
- `25` merges

Conclusión:
- la plantilla no es solo una tabla con encabezados
- es una hoja armada como formulario institucional

### Columnas
Ambos usan una base de columnas muy parecida en `A:L`, con anchos compatibles.

Esto indica que:
- el exportador actual ya usa una grilla cercana
- pero no replica la maquetacion ni el layout final de la plantilla

### Formulas
No se detectaron formulas relevantes en ninguno de los dos archivos inspeccionados.

Conclusión:
- la adaptación puede hacerse por maquetado y escritura de valores
- no depende de reconstruir formulas complejas

## Diferencias funcionales visibles

### Titulo
Plantilla:
- `MEMORIAS 2024 DEL GRUPO UTN - GIDAS`

Actual:
- `MEMORIA 2026 - VERSION 2`

Conclusión:
- la plantilla prioriza el anio de memoria y el nombre del grupo
- el actual prioriza identificacion tecnica de memoria/version

### Bloque inicial
Plantilla:
- arranca con `I.- ADMINISTRACIÓN`
- incluye:
  - individualizacion del grupo
  - autoridades
  - organigrama
  - objetivos

Actual:
- arranca con `I.- DATOS DE LA MEMORIA`
- muestra:
  - periodo
  - numero de version
  - estado
  - fechas de apertura/cierre

Conclusión:
- el actual es mas tecnico
- la plantilla es mas institucional y narrativa

### Orden de secciones
Plantilla:
1. `I.- ADMINISTRACIÓN`
2. `2.- PERSONAL`
3. `3.- EQUIPAMIENTO E INFRAESTRUCTURA`
4. `4.- DOCUMENTACIÓN Y BIBLIOTECA`
5. `II.- ACTIVIDADES DE I+D+i`
6. `5.- INVESTIGACIONES`
7. `7.- TRABAJOS PRESENTADOS EN CONGRESOS Y REUNIONES CIENTÍFICAS CON REFERATO`
8. `8.- TRABAJOS REALIZADOS Y PUBLICADOS`
9. `9.- REGISTROS Y PATENTES`
10. `III.- ACTIVIDADES EN DOCENCIA`
11. `IV.- VINCULACIÓN CON EL MEDIO SOCIO PRODUCTIVO`
12. `10.- TRANSFERENCIA AL MEDIO SOCIO PRODUCTIVO`
13. `V.- INFORME SOBRE RENDICIÓN GENERAL DE CUENTAS`
14. `11.- RESUMEN DE INGRESOS Y EGRESOS`
15. `VI - PROGRAMA DE ACTIVIDADES para 2025`

Actual:
- usa un orden mas tecnico y resumido
- no replica varios bloques textuales de la plantilla
- no incluye segunda hoja

## Diferencias de modelado por seccion

### Personal
Plantilla:
- separa:
  - investigadores
  - personal profesional
  - personal tecnico, administrativo y de apoyo
  - becarios y personal en formacion, desagregado por subtipos

Actual:
- ya distingue investigadores, personal y becarios
- pero no replica exactamente la misma composicion visual ni la subdivision de la plantilla

### Proyectos
Plantilla:
- la tabla de investigaciones usa columnas amplias y celdas largas
- incluye:
  - tipo
  - codigo
  - fechas
  - nombre
  - descripcion
  - logros
  - dificultades
  - fuente

Actual:
- tiene una tabla mucho mas sintetica
- no replica aun esa maquetacion textual extendida

### Transferencias
Plantilla:
- agrupa por subtipo contractual:
  - transferencia de tecnologia
  - I+D+i
  - transferencia de conocimientos
  - asistencia tecnica o consultoria
  - servicios tecnicos / ensayos
  - difusion a la comunidad

Actual:
- usa una sola tabla agregada

### Erogaciones
Plantilla:
- separa:
  - `Erogaciones Corrientes`
  - `Erogaciones de Capital`

Actual:
- usa una tabla general de ingresos/egresos

## Conclusión tecnica
La plantilla no puede considerarse un simple cambio cosmetico del workbook actual.

Implica:
- otra jerarquia de secciones
- mas merges
- mas estilos
- encabezados institucionales fijos
- mayor cantidad de bloques textuales
- tablas con layout distinto al exportador actual

## Estrategia de implementación recomendada
La implementacion correcta no es seguir generando una hoja desde cero e intentar "parecerse".

La estrategia recomendada es:
1. usar la plantilla como workbook base
2. conservar sus hojas, merges y estilos
3. escribir los datos del snapshot de memoria sobre posiciones bien definidas
4. reemplazar placeholders por datos reales
5. dejar en blanco o con texto controlado los bloques no aplicables

## Implicancias para el backend
Para que el exportador quede alineado con la plantilla, el servicio de exportacion debe:
- cargar la plantilla desde assets
- poblar `Hoja1`
- mantener el workbook resultante con el estilo original
- consumir solo snapshots de la memoria cerrada

## Estado actual del sistema frente a esta tarea
Ya esta resuelto:
- el Excel se genera desde `Memorias`
- solo desde una version cerrada
- usando datos de snapshot y no tablas vivas

Pendiente para alineacion visual completa:
- adaptar el maquetado del workbook a la plantilla institucional
