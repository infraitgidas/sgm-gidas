# Modulo backend de dashboard

El resumen financiero consulta `MovimientoFinanciero` y
`SaldoFinancieroService`: ingresos, egresos y saldo ARS derivan de movimientos
activos; los egresos se agrupan por categoría `CORRIENTE` o `CAPITAL`. No utiliza
las columnas separadas del modelo anterior. El contrato de la API conserva las
claves públicas del resumen.

Genera el resumen institucional, distribuciones, series y alertas a partir de
datos agregados de los modulos de negocio.

## Contrato

Los filtros invalidos responden `VALIDATION_ERROR`. Una falla inesperada de
consulta o infraestructura se registra de forma sanitizada y responde
`INTERNAL_ERROR` con `request_id`, sin reflejar detalles internos.

## Permisos y pruebas

El resumen admite `ADMIN`, `GESTOR` y `LECTURA`.

- `tests/test_dashboard_domain_errors.py`

## Reutilizacion de consultas del resumen (ISS-94)

`DashboardService.get_resumen` precarga clasificaciones y distinciones
de proyectos, formacion de becarios y contratos de transferencias.
Reutiliza los registros ya filtrados por UCT para contar integrantes por
grupo, en lugar de consultar nuevamente las colecciones de cada grupo.
La cache de alcance ORM conserva predicados, nunca respuestas del panel.

Se mantienen endpoints, filtros de fechas/anios/beca activa, permisos,
importes ARS, distribuciones y series. La comparacion del resumen sin
fechas, del periodo 2026 y de 2025 con beca activa conserva campos y orden;
solo `generado_en` varia por definicion. La medicion local del resumen
paso de 59 a 19 consultas SQL, sin garantizar una latencia universal.
La suite completa incluye las regresiones de aislamiento y finanzas.
