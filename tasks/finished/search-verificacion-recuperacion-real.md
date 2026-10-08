---
id: search-verificacion-recuperacion-real
title: Verificar recuperacion real de la busqueda global
status: finished
area: fullstack
module: search
priority: alta
risk_level: medio
created_at: 2026-08-18
updated_at: 2026-08-26
closed_at: 2026-08-26
source: frontend-calidad-seguridad
owner: agent
blocked_by: []
related_files:
  - backend/tools/verify_search_retrieval.py
  - backend/modules/search/
  - frontend/src/modules/search/
---

# Objetivo

Ejecutar la verificacion de recuperacion real de los 24 modulos indexados por la
busqueda global contra un entorno con datos activos y registrar resultados
reproducibles.

# Estado y bloqueo

Las pruebas unitarias del modulo finalizaron correctamente, pero el verificador real
no pudo ejecutarse el 2026-08-18 por dos bloqueos de entorno:

- el launcher de Python apunta a una instalacion de Microsoft Store inexistente o
  inaccesible al ejecutar `tools/verify_search_retrieval.py`;
- Docker Compose no puede resolver la configuracion porque
  `MIGRATION_DATABASE_URL` no esta definida.

No se deben inventar valores de conexion ni registrar credenciales en el repositorio.

## Iteracion del 2026-08-22

- Docker Desktop y PostgreSQL funcionan; se uso temporalmente el puerto host
  `55433` porque `5433` pertenece a otro proyecto y no se lo interrumpio;
- se detecto que `backend/entrypoint.sh` era materializado con CRLF en Windows y
  Linux no podia ejecutar su shebang;
- se agrego `.gitattributes` para exigir LF en scripts `.sh`; la imagen reconstruida
  ya ejecuta el entrypoint correctamente;
- la migracion alcanza PostgreSQL, pero la autenticacion de `gidas_admin` falla;
- la comprobacion estructural, sin imprimir valores, confirmo que usuario,
  contrasena y base de `MIGRATION_DATABASE_URL` no coinciden con
  `POSTGRES_ADMIN_USER`, `POSTGRES_ADMIN_PASSWORD` y `POSTGRES_DB` de `.env`;
- el verificador de los 24 modulos no debe ejecutarse hasta corregir esa URL y
  completar migraciones.

## Configuracion manual requerida

En el archivo `.env` de la raiz, reconstruir `MIGRATION_DATABASE_URL` con:

```text
postgresql://<POSTGRES_ADMIN_USER>:<POSTGRES_ADMIN_PASSWORD_URL_ENCODED>@db:5432/<POSTGRES_DB>
```

La contrasena dentro de la URL debe ser exactamente la misma que
`POSTGRES_ADMIN_PASSWORD`, aplicando URL encoding a caracteres reservados. No se
deben cambiar ni borrar volumenes para resolver esta inconsistencia.

## Mejora introducida

- garantiza que los scripts shell conserven formato ejecutable en Docker Linux
  aunque el repositorio se trabaje desde Windows;
- evita detener el PostgreSQL de otro proyecto y mantiene intactos sus datos;
- diagnostica la incoherencia de credenciales sin revelar valores sensibles.

Proximo paso: corregir `MIGRATION_DATABASE_URL`, reiniciar `migrate` y ejecutar los
24 probes de recuperacion real.

## Revalidacion del 2026-08-26

- Compose renderiza correctamente con los archivos de entorno actualizados;
- las imagenes de backend, migraciones y frontend se reconstruyeron correctamente;
- PostgreSQL, Redis y frontend iniciaron saludables;
- la comparacion de la configuracion efectiva, sin imprimir valores, confirmo que
  password, base, host y puerto coinciden;
- el usuario incluido en `MIGRATION_DATABASE_URL` no coincide con el
  `POSTGRES_USER` efectivo del contenedor;
- `migrate` se detuvo para evitar reintentos continuos y no se modificaron ni
  eliminaron volumenes.

Bloqueo actual: reemplazar solamente el usuario de `MIGRATION_DATABASE_URL` por el
mismo valor configurado en `POSTGRES_ADMIN_USER`. Luego recrear `migrate`, confirmar
codigo 0 y continuar con los 24 probes.

## Ejecucion real del 2026-08-26

- se sincronizo de forma no destructiva el rol administrativo historico del volumen
  con la credencial actual, sin imprimirla ni eliminar datos;
- `migrate` termino con codigo `0`, aplico migraciones, ejecuto el seed inicial y
  configuro el rol runtime de minimo privilegio;
- backend, PostgreSQL, Redis y frontend alcanzaron estado saludable;
- el verificador se ejecuto correctamente dentro del backend;
- los 24 probes informaron `sin datos activos`: la base recien inicializada no
  contiene registros funcionales para los modulos buscables.

Bloqueo actual: cargar datos funcionales representativos o fixtures aprobados para
los 24 modulos. No se marca recuperacion exitosa inventando datos de negocio.

## Revalidacion posterior al code splitting del 2026-08-26

- `docker exec gidas_backend python -m unittest tests.test_search`: 9 pruebas
  exitosas;
- `docker exec gidas_backend python tools/verify_search_retrieval.py`: codigo `1`
  esperado porque los 24 probes continúan informando `sin datos activos`;
- se revisaron los recursos de carga existentes y
  `backend/tools/seed_testing_data.py` solo genera una cobertura parcial; no es un
  fixture aprobado para validar los 24 modulos;
- `npm run typecheck`, `npm test` y `npm run build`: exitosos luego del ajuste de
  carga diferida del frontend;
- el build genera el chunk de `SearchPage` correctamente y conserva el contrato
  funcional de la busqueda.

Estado exacto: la implementacion y sus pruebas automatizadas funcionan. La
aceptacion de recuperacion real permanece bloqueada exclusivamente por ausencia
de datos representativos aprobados para los 24 modulos. No se cargaron registros
ficticios en la base compartida.

Proximo paso para la etapa de validacion con datos: disponer de una copia anonimizada
o un fixture integral aprobado en una base aislada, ejecutar nuevamente los 24
probes y registrar tipo, identificador y prefijo de URL sin datos personales.

## Validacion en staging aislado del 2026-08-26

- se corrigieron exclusivamente `MIGRATION_DATABASE_URL` y `DATABASE_URL` para
  derivarlas de las identidades administrativa y runtime ya configuradas;
- la comparacion estructural confirmo usuario, password, base, host y puerto sin
  mostrar credenciales;
- migraciones finalizaron con codigo `0` y el rol runtime pudo iniciar el backend;
- backend, PostgreSQL, Redis y frontend alcanzaron estado saludable;
- liveness, readiness, frontend y chunk inicial respondieron HTTP `200` por el
  proxy de staging;
- las 9 pruebas focalizadas de search finalizaron correctamente en un contenedor
  efimero;
- los 24 probes reales se ejecutaron y todos informaron `sin datos activos`.

El entorno ya no bloquea la validacion. El unico pendiente de recuperacion real es
la disponibilidad de datos representativos aprobados para los 24 modulos.

# Preparacion requerida

1. Reparar o recrear `backend/venv` con un interprete Python valido.
2. Configurar `MIGRATION_DATABASE_URL` mediante el mecanismo local seguro previsto
   por el proyecto.
3. Levantar la base y el backend con las migraciones aplicadas.
4. Confirmar que existan datos activos representativos para los 24 probes.

# Ejecucion

Desde `backend/`:

```text
.\venv\Scripts\python.exe tools\verify_search_retrieval.py
```

Si se usa Docker, ejecutar el mismo script dentro del contenedor backend ya
configurado, sin imprimir variables sensibles.

# Criterios de aceptacion

- El script finaliza con codigo `0`.
- Los 24 modulos recuperan al menos un resultado real con tipo y URL esperados.
- Las ausencias por falta de datos se documentan y se corrigen con fixtures o datos
  de prueba; no se consideran un resultado exitoso.
- Se adjunta salida resumida sin credenciales ni datos personales innecesarios.
- Se vuelven a ejecutar `tests.test_search`, typecheck y build.

# Cierre sugerido

```text
test(search): verificar recuperacion real de modulos indexados
```

## Cierre definitivo del 2026-08-26

- `backend/tools/seed_testing_data.py` se amplio con datos ficticios para los 24
  modulos y sus relaciones obligatorias;
- el seed conserva el bloqueo por ambiente y en staging requiere habilitacion
  efimera mediante `ALLOW_TEST_SEED=true`;
- tres ejecuciones sucesivas confirmaron que no se duplican registros;
- los 24 probes recuperaron tipo, identificador y URL esperados;
- las 9 pruebas focalizadas de search finalizaron correctamente;
- la suite backend completa finalizo con 316 pruebas correctas;
- typecheck y 11 pruebas frontend finalizaron correctamente;
- el build frontend finalizo correctamente sin chunks mayores a 500 kB;
- liveness, readiness, frontend y chunk inicial respondieron HTTP `200` en
  staging.

La validacion usa exclusivamente datos ficticios en el volumen aislado de staging.
Los fixtures no forman parte del seed productivo y `ALLOW_TEST_SEED` no debe
persistirse en archivos de entorno ni en Compose.
