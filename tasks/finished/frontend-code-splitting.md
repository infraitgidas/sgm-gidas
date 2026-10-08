---
id: frontend-code-splitting
title: Reducir bundle inicial mediante carga diferida por modulo
status: finished
area: frontend
module: performance
priority: media
risk_level: bajo
execution_order: 4
created_at: 2026-08-12
updated_at: 2026-08-26
closed_at: 2026-08-26
source: security-audit
commit_sugerido: "perf(frontend): dividir bundle por rutas y modulos"
owner: agent
blocked_by:
  - auth-refresh-cookie-http-only
related_files:
  - frontend/src/main.tsx
  - frontend/src/modules/
  - frontend/vite.config.ts
---

# Riesgo y objetivo

El bundle principal es de aproximadamente 1.28 MB minificado. No es una fuga de
seguridad, pero aumenta tiempo de carga, parseo y superficie descargada antes de
autenticar. El objetivo es cargar por ruta/modulo sin modificar permisos ni UX.

# Alcance

- Medir baseline y rutas mas usadas.
- Incorporar `lazy`/`Suspense` por modulo.
- Evaluar `manualChunks` solo para dependencias estables.
- Mantener feedback accesible durante carga.
- Evitar que chunks revelen secretos; los nombres de modulos no son secretos.

# Criterios de aceptacion

- Bundle inicial por debajo del umbral acordado o reduccion documentada.
- Typecheck y build correctos.
- Navegacion, rutas protegidas y errores de chunks probados.
- Sin renders adicionales significativos ni cambio funcional.

# Mensaje de commit propuesto

```text
perf(frontend): dividir bundle por rutas y modulos
```

# Cierre

Implementacion:

- las paginas de los modulos se cargan con `lazy` e imports dinamicos;
- el layout, la autenticacion y las protecciones permanecen en el bundle base;
- `Suspense` muestra un estado accesible durante la descarga;
- un limite de errores permite reintentar ante fallos de descarga o evaluacion;
- una prueba estructural protege la estrategia frente a regresiones a imports
  estaticos de paginas;
- la arquitectura de carga quedo documentada en `frontend/src/modules/README.md`.

Medicion:

- baseline: 1.284,65 kB minificado y 343,41 kB gzip en el chunk inicial;
- resultado: 338,48 kB minificado y 108,07 kB gzip en el chunk inicial;
- reduccion minificada: 73,7 %;
- ningun chunk supera 500 kB y Vite ya no emite la advertencia de tamano.

Validaciones:

- `npm run typecheck`: exitoso;
- `npm test`: 11 pruebas exitosas;
- `npm run build`: exitoso;
- rutas, permisos y navegacion del router se conservaron sin cambios funcionales.
