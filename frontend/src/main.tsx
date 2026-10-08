import { Component, lazy, Suspense, type ReactElement, type ReactNode } from "react";
import { createRoot } from "react-dom/client";


import { createBrowserRouter, RouterProvider, useLocation, useParams } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Navigate } from "react-router-dom";

import "./styles/index.css";

import AppLayout from "@/layouts/AppLayout";
import LoadingSkeleton from "@/components/LoadingSkeleton";
const Home = lazy(() => import("@/modules/dashboard/pages/Home"));
const UctForm = lazy(() => import("@/modules/grupo/pages/UctForm"));
const NotFound = lazy(() => import("@/modules/shared/pages/NotFound"));

// auth
const Login = lazy(() => import("@/modules/auth/pages/Login"));
const Register = lazy(() => import("@/modules/auth/pages/Register"));
const Landing = lazy(() => import("@/modules/auth/pages/Landing"));
import { AuthProvider } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";

// nuevas páginas
const PersonalLanding = lazy(() => import("@/modules/personal/pages/PersonalHome"));
const PersonalDetalle = lazy(() => import("@/modules/personal/pages/PersonalDetalle"));
const BecasHome = lazy(() => import("@/modules/recursos/pages/BecasHome"));
const BecasForm = lazy(() => import("@/modules/recursos/pages/BecasForm"));
const BecasDetalle = lazy(() => import("@/modules/recursos/pages/BecasDetalle"));
const ProyectosLanding = lazy(() => import("@/modules/proyectos/pages/ProyectosHome"));
const ProyectosForm = lazy(() => import("@/modules/proyectos/pages/ProyectosForm"));
const DocenciaLanding = lazy(() => import("@/modules/produccion/pages/DocenciaHome"));
const DocenciaForm = lazy(() => import("@/modules/produccion/pages/DocenciaForm"));
const DocenciaDetalle = lazy(() => import("@/modules/produccion/pages/DocenciaDetalle"));
const TrabajosReunionHome = lazy(() => import("@/modules/produccion/pages/TrabajosReunionHome"));
const TrabajosReunionForm = lazy(() => import("@/modules/produccion/pages/TrabajosReunionForm"));
const ErogacionesLanding = lazy(() => import("@/modules/recursos/pages/ErogacionesHome"));
const ErogacionesForm = lazy(() => import("@/modules/recursos/pages/ErogacionesForm"));
const ErogacionesDetalle = lazy(() => import("@/modules/recursos/pages/ErogacionesDetalle"));
const EquipamientoLanding = lazy(() => import("@/modules/recursos/pages/EquipamientoHome"));
const EquipamientoForm = lazy(() => import("@/modules/recursos/pages/EquipamientoForm"));
const EquipamientoDetalle = lazy(() => import("@/modules/recursos/pages/EquipamientoDetalle"));
const ObjetosLanding = lazy(() => import("@/modules/catalogos/pages/ObjetosFinHome"));
const SearchPage = lazy(() => import("@/modules/search/pages/SearchPage"));
const DocumentacionDetalle = lazy(() => import("@/modules/produccion/pages/DocumentacionDetalle"));
const DocumentacionForm = lazy(() => import("@/modules/produccion/pages/DocumentacionForm"));
const DocumentacionLanding = lazy(() => import("@/modules/produccion/pages/DocumentacionHome"));
const PersonalForm = lazy(() => import("@/modules/personal/pages/PersonalForm"));
const ProyectosDetalle = lazy(() => import("@/modules/proyectos/pages/ProyectosDetalle"));
const RegistrosPropiedadHome = lazy(() => import("@/modules/produccion/pages/RegistrosPropiedadHome"));
const RegistrosPropiedadForm = lazy(() => import("@/modules/produccion/pages/RegistrosPropiedadForm"));
const RegistrosPropiedadDetalle = lazy(() => import("@/modules/produccion/pages/RegistrosPropiedadDetalle"));
const TrabajosReunionDetalle = lazy(() => import("@/modules/produccion/pages/TrabajosReunionDetalle"));
const TrabajosRevistasHome = lazy(() => import("@/modules/produccion/pages/TrabajosRevistasHome"));
const TrabajosRevistasForm = lazy(() => import("@/modules/produccion/pages/TrabajosRevistasForm"));
const TrabajosRevistasDetalle = lazy(() => import("@/modules/produccion/pages/TrabajosRevistasDetalle"));
const ArticulosDivulgacionLanding = lazy(() => import("@/modules/produccion/pages/ArticulosDivulgacionHome"));
const ArticulosDivulgacionForm = lazy(() => import("@/modules/produccion/pages/ArticulosDivulgacionForm"));
const ArticulosDivulgacionDetalle = lazy(() => import("@/modules/produccion/pages/ArticulosDivulgacionDetalle"));
const TransferenciasForm = lazy(() => import("@/modules/transferencia/pages/TransferenciasForm"));
const TransferenciasDetalle = lazy(() => import("@/modules/transferencia/pages/TransferenciasDetalle"));
const TransferenciasHome = lazy(() => import("@/modules/transferencia/pages/TransferenciasHome"));
const DistincionesHome = lazy(() => import("@/modules/produccion/pages/DistincionesHome"));
const DistincionesForm = lazy(() => import("@/modules/produccion/pages/DistincionesForm"));
const DistincionesDetalle = lazy(() => import("@/modules/produccion/pages/DistincionesDetalle"));
const ParticipacionesHome = lazy(() => import("@/modules/proyectos/pages/ParticipacionesHome"));
const ParticipacionesForm = lazy(() => import("@/modules/proyectos/pages/ParticipacionesForm"));
const ParticipacionesDetalle = lazy(() => import("@/modules/proyectos/pages/ParticipacionesDetalle"));
const VisitantesHome = lazy(() => import("@/modules/grupo/pages/VisitantesHome"));
const VisitantesForm = lazy(() => import("@/modules/grupo/pages/VisitantesForm"));
const VisitantesDetalle = lazy(() => import("@/modules/grupo/pages/VisitantesDetalle"));
const MemoriasHome = lazy(() => import("@/modules/memorias/pages/MemoriasHome"));
const MemoriaForm = lazy(() => import("@/modules/memorias/pages/MemoriaForm"));
const MemoriaDetalle = lazy(() => import("@/modules/memorias/pages/MemoriaDetalle"));
const MemoriaVersionDetalle = lazy(() => import("@/modules/memorias/pages/MemoriaVersionDetalle"));
const InformesHome = lazy(() => import("@/modules/informes/pages/InformesHome"));
const InformeForm = lazy(() => import("@/modules/informes/pages/InformeForm"));
const InformeDetalle = lazy(() => import("@/modules/informes/pages/InformeDetalle"));

// Gestión de usuarios
const CambiarPassword = lazy(() => import("@/modules/auth/pages/CambiarPassword"));
const UsuariosHome = lazy(() => import("@/modules/auth/pages/UsuariosHome"));
const UsuariosForm = lazy(() => import("@/modules/auth/pages/UsuariosForm"));
const CatalogosHome = lazy(() => import("@/modules/catalogos/pages/CatalogosHome"));
const MiPerfil = lazy(() => import("@/modules/auth/pages/MiPerfil"));
const AdministracionHome = lazy(() => import("@/modules/administracion/pages/AdministracionHome"));

function editorOnly(element: ReactElement) {
  return <ProtectedRoute allowedRoles={["ADMIN", "GESTOR"]}>{element}</ProtectedRoute>;
}

function RouteLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl px-6 py-8">
      <LoadingSkeleton label="Cargando contenido…" />
    </div>
  );
}

function LegacyProjectEditRedirect() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  return <Navigate to={`/proyectos/${id}/editar${location.search}`} replace state={location.state} />;
}

class RouteErrorBoundary extends Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center px-4" role="alert">
          <div className="max-w-md text-center">
            <p className="text-sm text-slate-700">
              Lo sentimos, no pudimos cargar el contenido. Verifique su conexión e intente nuevamente.
            </p>
            <button
              className="mt-4 rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white"
              type="button"
              onClick={() => window.location.reload()}
            >
              Reintentar
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Definición de rutas
const routes = [
  { path: "/", element: <Landing /> },
  // rutas públicas (sin login)
  { path: "/login", element: <Login /> },
  { path: "/registro", element: <Register /> },

  // rutas protegidas (requieren estar logueado)
  {
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { path: "inicio", element: <Home /> },

      {
        path: "administracion",
        element: (
          <ProtectedRoute requiredRole="ADMIN">
            <AdministracionHome />
          </ProtectedRoute>
        ),
      },

      { path: "busqueda", element: <SearchPage /> },
      { path: "informes/:tipo", element: <ProtectedRoute requiredRole="GESTOR"><InformesHome /></ProtectedRoute> },
      { path: "informes/:tipo/nuevo", element: <ProtectedRoute requiredRole="GESTOR"><InformeForm /></ProtectedRoute> },
      { path: "informes/:tipo/:id", element: <ProtectedRoute requiredRole="GESTOR"><InformeDetalle /></ProtectedRoute> },
      { path: "informes/:tipo/:id/editar", element: <ProtectedRoute requiredRole="GESTOR"><InformeForm /></ProtectedRoute> },

      // UCT
      { path: "uct/nueva", element: editorOnly(<UctForm />) },
      { path: "uct/editar", element: editorOnly(<UctForm />) },

      // Personal
      { path: "personal", element: <PersonalLanding /> },   // landing  
      { path: "becas", element: <BecasHome /> },
      { path: "becas/nueva", element: editorOnly(<BecasForm />) },
      { path: "becas/:id", element: <BecasDetalle /> },
      { path: "becas/:id/editar", element: editorOnly(<BecasForm />) },
      { path: "personal/nuevo", element: editorOnly(<PersonalForm />) },    // formulario
      { path: "personal/:rol/:id", element: <PersonalDetalle /> }, // detalle de personal
      { path: "personal/:rol/:id/editar", element: editorOnly(<PersonalForm />) }, // editar personal
      { path: "becarios/:id/editar", element: editorOnly(<PersonalForm />) }, // editar becario
      { path: "investigadores/:id/editar", element: editorOnly(<PersonalForm />) }, // editar investigador
      { path: "becarios/:id", element: <PersonalDetalle /> }, // detalle de becario
      { path: "investigadores/:id", element: <PersonalDetalle /> }, // detalle de investigador
      { path: "ptaa/:id", element: <PersonalDetalle /> }, // detalle de PTAA
      { path: "profesionales/:id", element: <PersonalDetalle /> }, // detalle de profesional
      // Redirecciones para mantener compatibilidad con URLs anteriores
      {
        path: "investigadores",
        element: <Navigate to="/personal?tipo=INVESTIGADOR" replace />
      },
      {
        path: "becarios",
        element: <Navigate to="/personal?tipo=BECARIO" replace />
      },
      {
        path: "ptaa",
        element: <Navigate to="/personal?tipo=PTAA" replace />
      },
      {
        path: "profesionales",
        element: <Navigate to="/personal?tipo=PROFESIONAL" replace />
      },


      // Proyectos
      { path: "proyectos", element: <ProyectosLanding /> },
      { path: "proyectos/nuevo", element: editorOnly(<ProyectosForm />) },
      { path: "proyectos/:id", element: <ProyectosDetalle /> },
      { path: "proyectos/:id/editar", element: editorOnly(<ProyectosForm />) },
      { path: "proyectos/editar/:id", element: editorOnly(<LegacyProjectEditRedirect />) },
      // Docencia
      { path: "docenciaInvestigador", element: <DocenciaLanding /> },
      { path: "docenciaInvestigador/nuevo", element: editorOnly(<DocenciaForm />) },
      { path: "docenciaInvestigador/:id", element: <DocenciaDetalle /> },
      { path: "docenciaInvestigador/:id/editar", element: editorOnly(<DocenciaForm />) },

      // Trabajos en reuniones científicas
      { path: "trabajosCientInv", element: <TrabajosReunionHome /> },
      { path: "trabajosCientInv/nuevo", element: editorOnly(<TrabajosReunionForm />) },

      //Actividades I+D+I
      //Registros de propiedad  e industrial
      { path: "registros-propiedad", element: <RegistrosPropiedadHome /> },
      { path: "registros-propiedad/nuevo", element: editorOnly(<RegistrosPropiedadForm />) },
      { path: "registros-propiedad/:id", element: <RegistrosPropiedadDetalle /> },
      { path: "registros-propiedad/:id/editar", element: editorOnly(<RegistrosPropiedadForm />) },


      //Trabajos en reuniones científicas
      { path: "trabajos-reunion", element: <TrabajosReunionHome /> },
      { path: "trabajos-reunion/nuevo", element: editorOnly(<TrabajosReunionForm />) },
      { path: "trabajos-reunion/:id", element: <TrabajosReunionDetalle /> },
      { path: "trabajos-reunion/:id/editar", element: editorOnly(<TrabajosReunionForm />) },

      //Trabajos en revistas
      { path: "trabajos-revistas", element: <TrabajosRevistasHome /> },
      { path: "trabajos-revistas/nuevo", element: editorOnly(<TrabajosRevistasForm />) },
      { path: "trabajos-revistas/:id", element: <TrabajosRevistasDetalle /> },
      { path: "trabajos-revistas/:id/editar", element: editorOnly(<TrabajosRevistasForm />) },

      //Artículos de divulgación
      { path: "articulos-divulgacion", element: <ArticulosDivulgacionLanding /> },
      { path: "articulos-divulgacion/nuevo", element: editorOnly(<ArticulosDivulgacionForm />) },
      { path: "articulos-divulgacion/:id", element: <ArticulosDivulgacionDetalle /> },
      { path: "articulos-divulgacion/:id/editar", element: editorOnly(<ArticulosDivulgacionForm />) },




      // Erogaciones / Compras
      { path: "movimientos", element: <ErogacionesLanding /> },
      { path: "movimientos/nuevo", element: editorOnly(<ErogacionesForm />) },
      { path: "movimientos/:id", element: <ErogacionesDetalle /> },
      { path: "movimientos/:id/editar", element: editorOnly(<ErogacionesForm />) },

      // Equipamiento
      { path: "equipamiento", element: <EquipamientoLanding /> },
      { path: "equipamiento/nuevo", element: editorOnly(<EquipamientoForm />) },
      { path: "equipamiento/:id", element: <EquipamientoDetalle /> },
      { path: "equipamiento/:id/editar", element: editorOnly(<EquipamientoForm />) },

      // Objetos y financiamiento
      { path: "objetosfinanciamiento", element: <ObjetosLanding /> },

      // Documentación
      { path: "documentacion", element: <DocumentacionLanding /> },
      { path: "documentacion/nuevo", element: editorOnly(<DocumentacionForm />) },
      { path: "documentacion/:id", element: <DocumentacionDetalle /> },
      { path: "documentacion/:id/editar", element: editorOnly(<DocumentacionForm />) },

      // Transferencias (Vinculación Socio-Productiva)
      { path: "transferencias", element: <TransferenciasHome /> },
      { path: "transferencias/nuevo", element: editorOnly(<TransferenciasForm />) },
      { path: "transferencias/:id", element: <TransferenciasDetalle /> },
      { path: "transferencias/:id/editar", element: editorOnly(<TransferenciasForm />) },

      // Actividades I+D+i
      { path: "distinciones", element: <DistincionesHome /> },
      { path: "distinciones/nuevo", element: editorOnly(<DistincionesForm />) },
      { path: "distinciones/:id", element: <DistincionesDetalle /> },
      { path: "distinciones/:id/editar", element: editorOnly(<DistincionesForm />) },

      { path: "participaciones", element: <ParticipacionesHome /> },
      { path: "participaciones/nuevo", element: editorOnly(<ParticipacionesForm />) },
      { path: "participaciones/:id", element: <ParticipacionesDetalle /> },
      { path: "participaciones/:id/editar", element: editorOnly(<ParticipacionesForm />) },

      { path: "visitantes", element: <VisitantesHome /> },
      { path: "visitantes/nuevo", element: editorOnly(<VisitantesForm />) },
      { path: "visitantes/:id", element: <VisitantesDetalle /> },
      { path: "visitantes/:id/editar", element: editorOnly(<VisitantesForm />) },

      // Memorias
      { path: "memorias", element: <MemoriasHome /> },
      {
        path: "memorias/nueva",
        element: editorOnly(<MemoriaForm />),
      },
      { path: "memorias/:id", element: <MemoriaDetalle /> },
      {
        path: "memorias/:id/versiones/:versionId",
        element: <MemoriaVersionDetalle />,
      },
      

      // Gestión de Usuarios (solo admin)
      {
        path: "cambiar-password",
        element: (
          <ProtectedRoute>
            <CambiarPassword />
          </ProtectedRoute>
        ),
      },
      {
        path: "mi-perfil",
        element: (
          <ProtectedRoute>
            <MiPerfil />
          </ProtectedRoute>
        ),
      },
      {
        path: "usuarios",
        element: (
          <ProtectedRoute requiredRole="ADMIN">
            <UsuariosHome />
          </ProtectedRoute>
        ),
      },
      {
        path: "usuarios/nuevo",
        element: (
          <ProtectedRoute requiredRole="ADMIN">
            <UsuariosForm />
          </ProtectedRoute>
        ),
      },
      {
        path: "catalogos",
        element: (
          <ProtectedRoute allowedRoles={["ADMIN", "GESTOR"]}>
            <CatalogosHome />
          </ProtectedRoute>
        ),
      },

      { path: "*", element: <NotFound /> },
    ],
  },
];

// Cliente de React Query
const queryClient = new QueryClient();

// Retira datos guardados por versiones anteriores antes de mostrar cualquier ruta.
try {
  for (let index = localStorage.length - 1; index >= 0; index -= 1) {
    const key = localStorage.key(index);
    if (key?.startsWith("gidas:form-draft:v1:") || key === "gidas_adoptantes_mock") {
      localStorage.removeItem(key);
    }
  }
} catch {
  // El navegador puede deshabilitar Storage; los borradores nuevos usan el servidor.
}

// basename: la SGM se sirve bajo /sgm-gidas/ en el Portal GIDAS.
const router = createBrowserRouter(routes, {
  basename: import.meta.env.VITE_BASE_PATH?.replace(/\/+$/, "") || "/",
});

// Renderizado de la aplicación
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <RouteErrorBoundary>
        <Suspense fallback={<RouteLoading />}>
          <RouterProvider router={router} />
        </Suspense>
      </RouteErrorBoundary>
    </AuthProvider>
  </QueryClientProvider>
);

