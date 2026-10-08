import {
  ArrowRight,
  BookOpenCheck,
  ClipboardList,
  History,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import LandingAccessAction from "@/modules/auth/components/LandingAccessAction";
import { useSystemSetup } from "@/modules/auth/hooks/useSystemSetup";
import { getLandingAccessState } from "@/modules/auth/utils/landingAccessState";

type Task = {
  eyebrow: string;
  title: string;
  description: string;
  icon: LucideIcon;
};

const SUPPORT_EMAIL = "gidas@frlp.utn.edu.ar";

const TASKS: Task[] = [
  {
    eyebrow: "Registrar · consultar",
    title: "Registrar y consultar",
    description:
      "Personal, proyectos, producción y recursos organizados en un mismo entorno.",
    icon: ClipboardList,
  },
  {
    eyebrow: "Versionar · conservar",
    title: "Conservar el historial",
    description:
      "Memorias, versiones, períodos y antecedentes disponibles para consulta institucional.",
    icon: History,
  },
  {
    eyebrow: "Gestionar · proteger",
    title: "Administrar el acceso",
    description:
      "Roles ADMIN, GESTOR y LECTURA; las altas quedan bajo administración.",
    icon: ShieldCheck,
  },
];

const ACCESS_PROFILES = [
  {
    role: "ADMIN",
    description: "Usuarios, configuración y operaciones reservadas.",
  },
  {
    role: "GESTOR",
    description: "Altas y ediciones de registros institucionales.",
  },
  {
    role: "LECTURA",
    description: "Consulta de información, detalles e historial.",
  },
];

export default function Landing() {
  const { user, loading: sessionLoading } = useAuth();
  const {
    data: needsInitialAdmin,
    isFetching: setupFetching,
    isError: setupError,
    refetch: refetchSetup,
  } = useSystemSetup(!sessionLoading && !user);

  const accessState = getLandingAccessState({
    sessionLoading,
    userExists: Boolean(user),
    setupError,
    needsInitialAdmin,
  });

  async function handleRetry() {
    await refetchSetup();
  }

  return (
    <div className="min-h-screen bg-[#F6F6FB] text-slate-900">
      <LandingHeader />

      <main>
        <section className="border-b border-slate-200 bg-white">
          <div className="mx-auto grid w-full max-w-7xl items-center gap-12 px-5 py-14 sm:py-16 md:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)] md:gap-12 lg:gap-24 lg:px-10 lg:py-20">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Sistema institucional
              </p>
              <h1 className="mt-5 max-w-3xl text-4xl font-semibold leading-[1.02] tracking-[-0.04em] text-slate-950 sm:text-5xl lg:text-6xl">
                Sistema de Gestión de Memorias Académicas
              </h1>
              <p className="mt-6 max-w-2xl text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
                Registrá, consultá y versioná la información académica y de
                investigación de la UCT para organizar memorias institucionales
                con trazabilidad.
              </p>

              <div className="mt-8">
                <LandingAccessAction
                  state={accessState}
                  retrying={setupFetching}
                  supportEmail={SUPPORT_EMAIL}
                  onRetry={handleRetry}
                />
              </div>
            </div>

            <AccessProfiles />
          </div>
        </section>

        <section aria-labelledby="tasks-heading" className="border-b border-slate-200">
          <div className="mx-auto w-full max-w-7xl px-5 py-12 sm:py-14 lg:px-10 lg:py-16">
            <div className="max-w-3xl">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Recorridos del sistema
              </p>
              <h2
                id="tasks-heading"
                className="mt-4 text-3xl font-semibold tracking-[-0.03em] text-slate-950 sm:text-4xl"
              >
                Una entrada para cada tarea
              </h2>
              <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
                La información se organiza alrededor de lo que necesitás
                registrar, consultar y conservar.
              </p>
            </div>

            <div className="mt-10 divide-y divide-slate-200 border-y border-slate-200">
              {TASKS.map((task, index) => (
                <TaskRow key={task.title} task={task} index={index} />
              ))}
            </div>

            <SupportPanel />
          </div>
        </section>
      </main>

      <LandingFooter />
    </div>
  );
}

function LandingHeader() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex min-h-16 w-full max-w-7xl items-center justify-between gap-5 px-5 lg:px-10">
        <div className="flex items-center gap-3">
          <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-slate-950 text-white">
            <BookOpenCheck className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <p className="text-sm font-semibold leading-5 text-slate-950">
              GIDAS · UTN FRLP
            </p>
            <p className="text-xs text-slate-500">Gestión académica</p>
          </div>
        </div>
        <p className="hidden text-xs font-medium text-slate-500 sm:block">
          UTN Facultad Regional La Plata
        </p>
      </div>
    </header>
  );
}

function AccessProfiles() {
  return (
    <aside
      className="border-t border-slate-200 pt-8 md:border-l md:border-t-0 md:pl-8 md:pt-0 lg:pl-10"
      aria-labelledby="profiles-heading"
    >
      <p
        id="profiles-heading"
        className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500"
      >
        Acceso por perfil
      </p>
      <p className="mt-4 max-w-sm text-sm leading-6 text-slate-600">
        Cada cuenta encuentra el alcance que necesita para trabajar o consultar.
      </p>
      <dl className="mt-6 divide-y divide-slate-200 border-y border-slate-200">
        {ACCESS_PROFILES.map((profile) => (
          <div
            key={profile.role}
            className="grid gap-2 py-4 sm:grid-cols-[4.5rem_minmax(0,1fr)] sm:gap-4"
          >
            <dt className="text-xs font-bold tracking-[0.14em] text-slate-950">
              {profile.role}
            </dt>
            <dd className="text-sm leading-6 text-slate-600">
              {profile.description}
            </dd>
          </div>
        ))}
      </dl>
    </aside>
  );
}

function TaskRow({ task, index }: { task: Task; index: number }) {
  const Icon = task.icon;

  return (
    <article className="grid gap-4 py-6 sm:grid-cols-[5rem_2rem_minmax(12rem,0.8fr)_minmax(0,1.5fr)] sm:items-center sm:gap-5 lg:grid-cols-[6rem_2.25rem_minmax(15rem,0.8fr)_minmax(0,1.5fr)]">
      <div className="flex items-center gap-3 text-xs font-medium tracking-[0.14em] text-slate-500">
        <span>{String(index + 1).padStart(2, "0")}</span>
        <span className="hidden h-px w-7 bg-slate-300 sm:block" aria-hidden="true" />
      </div>
      <span className="grid h-9 w-9 place-items-center rounded-lg border border-slate-300 bg-white text-slate-700">
        <Icon className="h-4 w-4" aria-hidden="true" />
      </span>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
          {task.eyebrow}
        </p>
        <h3 className="mt-1 text-base font-semibold text-slate-950">{task.title}</h3>
      </div>
      <p className="text-sm leading-6 text-slate-600">{task.description}</p>
    </article>
  );
}

function SupportPanel() {
  return (
    <aside className="mt-10 flex flex-col gap-3 rounded-xl border border-slate-300 bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
      <div>
        <h2 className="text-sm font-semibold text-slate-950">¿No tenés acceso?</h2>
        <p className="mt-1 text-sm leading-6 text-slate-600">
          Solicitá orientación a GIDAS para conocer el procedimiento.
        </p>
      </div>
      <a
        href={`mailto:${SUPPORT_EMAIL}`}
        className="inline-flex min-h-11 items-center gap-2 text-sm font-semibold text-slate-950 underline decoration-slate-300 underline-offset-4 transition hover:decoration-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2"
      >
        {SUPPORT_EMAIL}
        <ArrowRight className="h-4 w-4" aria-hidden="true" />
      </a>
    </aside>
  );
}

function LandingFooter() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-5 py-6 sm:flex-row sm:items-end sm:justify-between lg:px-10">
        <div>
          <p className="text-sm font-semibold text-slate-950">GIDAS - UTN FRLP</p>
          <p className="mt-1 text-xs text-slate-500">
            Grupo de I&amp;D aplicado a sistemas informáticos
          </p>
        </div>
        <div className="text-left text-xs text-slate-500 sm:text-right">
          <a
            href={`mailto:${SUPPORT_EMAIL}`}
            className="font-semibold text-slate-700 underline decoration-slate-300 underline-offset-2 transition hover:text-slate-950 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-500 focus-visible:ring-offset-2"
          >
            {SUPPORT_EMAIL}
          </a>
          <p className="mt-1">UTN Facultad Regional La Plata</p>
        </div>
      </div>
    </footer>
  );
}
