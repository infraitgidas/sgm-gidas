export type BreadcrumbItem = {
  label: string;
  to?: string;
};

const sectionNames: Record<string, string> = {
  administracion: "Administración",
  busqueda: "Búsqueda",
  personal: "Personal",
  becas: "Becas",
  proyectos: "Proyectos",
  docenciaInvestigador: "Actividades en Docencia",
  trabajosCientInv: "Trabajos en Reunión Científica",
  "registros-propiedad": "Registros de Propiedad",
  "trabajos-reunion": "Trabajos en Reunión Científica",
  "trabajos-revistas": "Trabajos en Revistas",
  "articulos-divulgacion": "Artículos de Divulgación",
  movimientos: "Movimientos financieros",
  equipamiento: "Equipamiento e Infraestructura",
  objetosfinanciamiento: "Objetos de financiamiento",
  documentacion: "Documentación y Biblioteca",
  transferencias: "Transferencias",
  distinciones: "Distinciones Recibidas",
  participaciones: "Participaciones Relevantes",
  visitantes: "Visitantes",
  memorias: "Memorias",
  informes: "Informes",
  usuarios: "Usuarios",
  catalogos: "Catálogos",
  "mi-perfil": "Mi perfil",
  "cambiar-password": "Cambiar contraseña",
};

const personalAliases = new Set(["investigadores", "becarios", "ptaa", "profesionales"]);
const personalEditAliases = new Set(["investigadores", "becarios"]);
const detailSections = new Set([
  "proyectos", "docenciaInvestigador", "registros-propiedad", "trabajos-reunion",
  "trabajos-revistas", "articulos-divulgacion", "movimientos", "equipamiento",
  "documentacion", "transferencias", "distinciones", "participaciones",
  "visitantes", "memorias", "becas",
]);
const start: BreadcrumbItem = { label: "Inicio", to: "/inicio" };

function sectionTrail(section: string): BreadcrumbItem[] {
  return [start, { label: sectionNames[section], to: `/${section}` }];
}

export function getRouteBreadcrumbs(pathname: string): BreadcrumbItem[] {
  const segments = pathname.split("/").filter(Boolean);
  const [section, second, third, fourth] = segments;

  if (pathname === "/inicio") return [{ label: "Inicio" }];
  if (pathname === "/") return [{ label: "Portada" }];
  if (pathname === "/login") return [{ label: "Portada", to: "/" }, { label: "Iniciar sesión" }];
  if (pathname === "/registro") return [{ label: "Portada", to: "/" }, { label: "Crear cuenta" }];

  if (section === "uct" && second === "nueva" && segments.length === 2) {
    return [start, { label: "Nueva UCT" }];
  }
  if (section === "uct" && second === "editar" && segments.length === 2) {
    return [start, { label: "Editar UCT" }];
  }

  if (section === "personal" && segments.length === 4 && fourth === "editar") {
    return [...sectionTrail("personal"), { label: "Detalle", to: `/personal/${second}/${third}` }, { label: "Editar" }];
  }
  if (section === "personal" && segments.length === 3) {
    return [...sectionTrail("personal"), { label: "Detalle" }];
  }

  if (personalEditAliases.has(section) && segments.length === 3 && third === "editar") {
    return [...sectionTrail("personal"), { label: "Detalle", to: `/${section}/${second}` }, { label: "Editar" }];
  }
  if (personalAliases.has(section) && segments.length === 2) {
    return [...sectionTrail("personal"), { label: "Detalle" }];
  }

  if (section === "memorias" && segments.length === 4 && third === "versiones") {
    return [...sectionTrail("memorias"), { label: "Detalle", to: `/memorias/${second}` }, { label: "Versión" }];
  }

  if (section === "informes" && second) {
    const labels: Record<string, string> = { investigadores: "Investigadores", pid: "Proyectos", uct: "UCT" };
    const typeLabel = labels[second];
    if (typeLabel) {
      const root = [start, { label: "Informes" }, { label: typeLabel, to: `/informes/${second}` }];
      if (segments.length === 2) return [start, { label: "Informes" }, { label: typeLabel }];
      if (third === "nuevo" && segments.length === 3) return [...root, { label: "Nuevo" }];
      if (segments.length === 3) return [...root, { label: "Detalle" }];
      if (fourth === "editar" && segments.length === 4) return [...root, { label: "Detalle", to: `/informes/${second}/${third}` }, { label: "Editar" }];
    }
  }

  if (section === "proyectos" && segments.length === 3 && second === "editar") {
    return [...sectionTrail("proyectos"), { label: "Detalle", to: `/proyectos/${third}` }, { label: "Editar" }];
  }

  if (detailSections.has(section) && segments.length === 3 && third === "editar") {
    return [...sectionTrail(section), { label: "Detalle", to: `/${section}/${second}` }, { label: "Editar" }];
  }

  if (sectionNames[section] && segments.length === 2 && (second === "nuevo" || second === "nueva")) {
    return [...sectionTrail(section), { label: second === "nueva" ? "Nueva" : "Nuevo" }];
  }
  if (detailSections.has(section) && segments.length === 2) {
    return [...sectionTrail(section), { label: "Detalle" }];
  }
  if (sectionNames[section] && segments.length === 1) {
    return [start, { label: sectionNames[section] }];
  }

  return [start, { label: "Página no encontrada" }];
}
