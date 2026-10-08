import type { Rol } from "@/modules/auth/services/authService";

export type RoleCapabilities = {
  label: string;
  summary: string;
  allowed: string[];
  restricted: string[];
};

const CAPABILITIES: Record<Rol, RoleCapabilities> = {
  ADMIN: {
    label: "Administrador",
    summary: "Tiene permisos de administración y gestión general del sistema.",
    allowed: [
      "Consultar, agregar, editar y eliminar registros.",
      "Administrar usuarios y sus roles.",
      "Gestionar estados, reaperturas y exportaciones de memorias.",
    ],
    restricted: [
      "No puede modificar los snapshots históricos de memorias cerradas.",
    ],
  },
  GESTOR: {
    label: "Gestor",
    summary: "Puede gestionar el contenido operativo del sistema.",
    allowed: [
      "Consultar, agregar, editar y eliminar registros.",
      "Consultar auditorías e historiales de cambios.",
      "Exportar información cuando la operación esté habilitada.",
    ],
    restricted: [
      "No puede administrar usuarios ni modificar sus roles.",
      "No puede ejecutar operaciones de memoria reservadas al administrador.",
    ],
  },
  LECTURA: {
    label: "Lector",
    summary: "Su sesión es de solo lectura.",
    allowed: [
      "Consultar listados, detalles, auditorías e historiales disponibles.",
      "Utilizar la búsqueda y los filtros del sistema.",
    ],
    restricted: [
      "No puede agregar, editar ni eliminar registros.",
      "No puede administrar usuarios ni ejecutar exportaciones reservadas.",
    ],
  },
};

export function getRoleCapabilities(role: Rol): RoleCapabilities {
  return CAPABILITIES[role];
}
