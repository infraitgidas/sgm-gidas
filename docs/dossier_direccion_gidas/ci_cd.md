# Integracion continua y entrega

## Alcance actual

El repositorio usa GitHub Actions para validar cada pull request y cada push a
`main`, `master` o `dev`. Esta etapa es exclusivamente CI: no conecta con
servidores ni realiza despliegues.

El workflow `.github/workflows/ci.yml` ejecuta trabajos independientes para:

- mensajes de commit con formato Conventional Commits;
- suite completa del backend con Python 3.11;
- pruebas, typecheck y build del frontend con Node.js 22;
- render de Compose productivo, validacion de topologia y escaneo de secretos.

## Contratos y seguridad

La validacion de infraestructura copia exclusivamente plantillas versionables en
el runner temporal. No utiliza archivos `.env` reales ni secretos de GitHub. Las
plantillas solo permiten renderizar y validar estructura; no son credenciales
aptas para desplegar.

El workflow solicita solamente permiso de lectura del repositorio. Los trabajos no
publican artefactos, imagenes ni paquetes y no poseen permisos de despliegue.

## Mensajes de commit

Cada commit incluido en el push o pull request debe respetar:

```text
tipo(scope opcional): descripcion breve
```

Tipos admitidos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore` y `revert`. Se admiten cambios incompatibles mediante `!`.

## Entrega elegida para la primera VM

La primera entrega sera manual y controlada mediante SSH. No se agregara un job con
acceso al servidor mientras no se definan infraestructura, aprobadores y gestion de
secretos. El operador debe:

1. conectarse a la VM con una identidad SSH individual;
2. desplegar un tag o commit aprobado y registrar su hash;
3. ejecutar `scripts/validate-vm-deployment.sh .env.production`;
4. crear y comprobar el respaldo cuando sea una actualizacion;
5. ejecutar `docker compose --env-file .env.production up --build -d`;
6. ejecutar `scripts/smoke-vm-deployment.sh .env.production`;
7. registrar version, operador, migracion, healthchecks y resultado funcional.

Esta decision satisface la entrega inicial reproducible sin introducir credenciales
SSH en GitHub. La automatizacion de CD es una mejora futura, no un requisito para
poner la VM tecnicamente operativa.

## Configuracion pendiente para un CD futuro

Antes de agregar despliegue deben definirse:

- ambiente de staging y/o produccion;
- runner hospedado o runner propio con acceso controlado al servidor;
- aprobaciones y responsables del ambiente protegido;
- registro de imagenes, versionado y politica de retencion;
- mecanismo de secretos sin exponerlos al workflow ni a pull requests externos;
- migraciones, healthchecks, rollback y evidencia posterior al despliegue;
- HTTPS, DNS/IP y certificados del ambiente final.

Hasta que esas decisiones existan, no debe agregarse un job de despliegue ni
credenciales de la VM a GitHub.

## Validacion local equivalente

```text
cd backend
python -m unittest discover -s tests -v
cd ..
cd frontend
npm test
npm run typecheck
npm run build
cd ..
docker compose --env-file .env.production config --quiet
python backend/tools/validate_production_topology.py --env-file .env.production
python backend/tools/scan_tracked_secrets.py
```
