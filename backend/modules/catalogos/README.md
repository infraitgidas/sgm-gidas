# Modulo backend de catalogos

Gestiona categorias UTN y fuentes de financiamiento con auditoria y baja logica.
La pantalla de Catalogos tambien consume servicios de catalogo de `personal`,
`grupo`, `proyectos`, `produccion`, `recursos` y `transferencia`.

## Nombres descriptivos (ISS-01)

En altas y cambios de nombre de los catalogos administrados desde la pantalla,
los servicios exigen al menos una letra Unicode. Numeros y signos pueden acompanarla.
La regla compartida vive en `modules/shared/services/catalog_name_validation.py`;
devuelve `VALIDATION_ERROR` con `details.fields.nombre` (o `nombre_beca` para becas). No cambia endpoints,
payloads, IDs, relaciones, estados ni filas historicas existentes. Los servicios
conservan sus controles propios de longitud, duplicidad y permisos.

El historial por valor continua en `GET <endpoint>/:id/historial`. Una edicion
mantiene el mismo registro y agrega los cambios de campos; la baja logica conserva
el registro para consultas historicas.

## Contrato de errores

Los services clasifican validaciones (`VALIDATION_ERROR`), recursos inexistentes
(`NOT_FOUND`) y conflictos de duplicidad, estado o relaciones (`CONFLICT`). Las
fallas inesperadas se ocultan mediante `INTERNAL_ERROR` con `request_id`.

## Pruebas

- `tests/test_catalogos_domain_errors.py`
- `tests/test_catalogo_auditoria_service.py`
# Paginacion SQL (ISS-89)

Categoria UTN y fuente de financiamiento conservan el array sin parametros.
Con `page` o `per_page`, sus services cuentan la consulta filtrada y aplican
`LIMIT/OFFSET` antes de serializar. El payload `data`/`meta`/`error`, los
filtros `activos` y `orden`, y el historial de tres cambios se conservan.
