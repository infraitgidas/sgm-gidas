import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  BookOpen,
  Building2,
  CircleAlert,
  Settings,
  UserPlus,
  Users,
} from "lucide-react";
import Button from "@/components/Button";
import { useDirectivos } from "@/modules/grupo/hooks/useDirectivos";
import { useUct } from "@/modules/grupo/hooks/useUct";
import {
  getUsuarios,
  type Usuario,
} from "@/modules/auth/services/usuariosService";

type ActionCardProps = {
  title: string;
  description: string;
  to: string;
  action: string;
  icon: typeof Users;
};

function ActionCard({ title, description, to, action, icon: Icon }: ActionCardProps) {
  return (
    <article className="flex h-full flex-col rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-100 text-slate-700">
        <Icon aria-hidden="true" className="h-5 w-5" />
      </div>
      <h2 className="mt-5 text-lg font-semibold text-slate-900">{title}</h2>
      <p className="mt-2 flex-1 text-sm leading-6 text-slate-600">{description}</p>
      <Link
        to={to}
        state={{ returnTo: "/administracion" }}
        className="mt-5 inline-flex items-center gap-2 text-sm font-semibold text-slate-900 hover:text-slate-600"
      >
        {action}
        <ArrowRight aria-hidden="true" className="h-4 w-4" />
      </Link>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
      <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold text-slate-900">{value}</dd>
    </div>
  );
}

export default function AdministracionHome() {
  const navigate = useNavigate();
  const {
    data: usuarios = [],
    isLoading: usuariosLoading,
    isError: usuariosError,
    refetch: refetchUsuarios,
  } = useQuery<Usuario[]>({
    queryKey: ["usuarios"],
    queryFn: getUsuarios,
  });
  const { uct, isLoading: uctLoading, isError: uctError } = useUct();
  const {
    data: directivos = [],
    isLoading: directivosLoading,
    isError: directivosError,
  } = useDirectivos(uct?.id);

  const activos = usuarios.filter((usuario) => usuario.activo).length;
  const inactivos = usuarios.length - activos;
  const primerAccesoPendiente = usuarios.filter(
    (usuario) => usuario.activo && usuario.primer_login
  ).length;
  const loading = usuariosLoading || uctLoading || (!!uct && directivosLoading);
  const summaryError = usuariosError || uctError || directivosError;

  const pendientes = [
    !uct
      ? {
          title: "Configurar la UCT",
          description: "Complete los datos institucionales para habilitar la operación del sistema.",
          to: "/uct/nueva",
        }
      : null,
    uct && !directivosLoading && directivos.length === 0
      ? {
          title: "Registrar autoridades",
          description: "La UCT todavía no tiene un equipo directivo vigente.",
          to: "/uct/editar",
        }
      : null,
    primerAccesoPendiente > 0
      ? {
          title: "Revisar primeros accesos",
          description: `${primerAccesoPendiente} usuario${primerAccesoPendiente === 1 ? "" : "s"} todavía debe cambiar su contraseña temporal.`,
          to: "/usuarios",
        }
      : null,
  ].filter((item): item is NonNullable<typeof item> => item !== null);

  return (
    <section className="space-y-8" aria-labelledby="administracion-title">
      <header className="flex flex-col gap-4 border-b border-slate-200 pb-5 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500">Administración del sistema</p>
          <h1 id="administracion-title" className="mt-1 text-3xl font-semibold text-slate-900">
            Panel de administración
          </h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
            Gestione accesos, configuración institucional y catálogos desde un único lugar.
            Los módulos operativos mantienen sus permisos y funcionamiento actuales.
          </p>
        </div>
        <Button variant="secondary" size="sm" onClick={() => navigate(-1)}>
          Volver
        </Button>
      </header>

      {summaryError && (
        <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 p-5">
          <p className="font-medium text-rose-900">
            Lo sentimos, no pudimos recuperar todo el resumen administrativo.
          </p>
          <p className="mt-1 text-sm text-rose-700">Intente nuevamente o acceda a cada sección.</p>
          {usuariosError && (
            <Button className="mt-4" size="sm" onClick={() => refetchUsuarios()}>
              Reintentar usuarios
            </Button>
          )}
        </div>
      )}

      <section aria-labelledby="resumen-title" className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 id="resumen-title" className="text-lg font-semibold text-slate-900">Resumen</h2>
            <p className="text-sm text-slate-500">Estado actual obtenido de las funciones existentes.</p>
          </div>
          {loading && <span role="status" className="text-sm text-slate-500">Actualizando...</span>}
        </div>
        <dl className="mt-5 grid grid-cols-2 gap-3 lg:grid-cols-4">
          <Metric label="Usuarios activos" value={usuariosError ? "-" : activos} />
          <Metric label="Usuarios inactivos" value={usuariosError ? "-" : inactivos} />
          <Metric label="Primer acceso pendiente" value={usuariosError ? "-" : primerAccesoPendiente} />
          <Metric label="Autoridades vigentes" value={directivosError ? "-" : directivos.length} />
        </dl>
      </section>

      {pendientes.length > 0 && (
        <section aria-labelledby="pendientes-title" className="space-y-3">
          <div className="flex items-center gap-2">
            <CircleAlert aria-hidden="true" className="h-5 w-5 text-amber-600" />
            <h2 id="pendientes-title" className="text-lg font-semibold text-slate-900">Atención requerida</h2>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            {pendientes.map((pendiente) => (
              <article key={pendiente.title} className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
                <h3 className="font-semibold text-amber-950">{pendiente.title}</h3>
                <p className="mt-1 text-sm leading-6 text-amber-800">{pendiente.description}</p>
                <Link
                  to={pendiente.to}
                  state={{ returnTo: "/administracion" }}
                  className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-amber-950"
                >
                  Resolver
                  <ArrowRight aria-hidden="true" className="h-4 w-4" />
                </Link>
              </article>
            ))}
          </div>
        </section>
      )}

      <section aria-labelledby="gestion-title">
        <h2 id="gestion-title" className="text-xl font-semibold text-slate-900">Gestión administrativa</h2>
        <p className="mt-1 text-sm text-slate-500">Accesos organizados por responsabilidad.</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <ActionCard
            title="Usuarios y accesos"
            description="Consulte usuarios, roles, estados y primeros accesos pendientes."
            to="/usuarios"
            action="Gestionar usuarios"
            icon={Users}
          />
          <ActionCard
            title="Crear usuario"
            description="Genere una cuenta con credencial temporal y el rol correspondiente."
            to="/usuarios/nuevo"
            action="Registrar usuario"
            icon={UserPlus}
          />
          <ActionCard
            title="Organización"
            description="Configure la UCT, sus datos institucionales y autoridades vigentes."
            to={uct ? "/uct/editar" : "/uct/nueva"}
            action={uct ? "Revisar configuración" : "Configurar UCT"}
            icon={Building2}
          />
          <ActionCard
            title="Catálogos"
            description="Administre los valores reutilizados por los módulos funcionales."
            to="/catalogos"
            action="Gestionar catálogos"
            icon={BookOpen}
          />
          <article className="flex h-full flex-col rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-slate-500">
              <Settings aria-hidden="true" className="h-5 w-5" />
            </div>
            <h2 className="mt-5 text-lg font-semibold text-slate-800">Resumen administrativo integrado</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              El servicio backend agregado para auditoría, alertas y estado del sistema queda reservado para una revisión futura.
            </p>
            <span className="mt-5 text-xs font-semibold uppercase tracking-wide text-slate-500">Próxima etapa</span>
          </article>
        </div>
      </section>
    </section>
  );
}
