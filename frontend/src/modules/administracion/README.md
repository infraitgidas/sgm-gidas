# Modulo frontend de administracion

## Alcance actual

`AdministracionHome` concentra la experiencia del rol `ADMIN` sin modificar los
roles, permisos ni contratos existentes. La vista reutiliza las consultas de
usuarios, UCT y directivos para presentar conteos y pendientes accionables.

## Navegacion y permisos

- ruta: `/administracion`
- permiso frontend: solo `ADMIN`
- autoridad final: los endpoints backend conservan sus controles actuales
- el menu del administrador se limita a `Inicio`, `Administracion`, `Memorias`
  y `Busqueda`; Memorias permanece disponible aunque no haya versiones abiertas
- `GESTOR` conserva su acceso directo a catalogos
- el icono de usuario de la barra superior despliega las opciones del perfil
- la identidad, el rol, el perfil, el cambio de contrasena y el cierre de sesion
  se concentran en el pie desplegable del menu lateral
- las mismas acciones quedan disponibles desde el icono superior para ofrecer
  acceso consistente en escritorio y dispositivos moviles

ISS-52 mantiene el acceso a Memorias independiente del estado del período.
El mismo árbol se usa en escritorio y móvil. No se agregan otros módulos al
menú ADMIN ni se modifican los permisos o la navegación de GESTOR y LECTURA.
`tests/administracionNavigation.test.ts` renderiza Sidebar para los tres roles
y comprueba los destinos exactos de ADMIN sin dependencias de consultas de Memorias.

## Secciones

- resumen de usuarios y autoridades
- alertas por UCT, autoridades y primeros accesos pendientes
- accesos a usuarios, alta de usuario, organizacion y catalogos
- aviso de alcance futuro para el resumen administrativo agregado

## Estado futuro

Queda fuera de esta etapa la creacion de un modulo backend
`/api/v1/administracion/resumen`. Antes de incorporarlo se deben revisar
contratos, consultas agregadas, auditoria, observabilidad y datos que puedan
considerarse sensibles.
