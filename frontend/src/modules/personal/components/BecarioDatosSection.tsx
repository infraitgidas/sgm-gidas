import { useState } from "react";
import { CalendarDays, ChevronDown, GraduationCap, User } from "lucide-react";
import { Link, useLocation } from "react-router-dom";
import type { PersonalCompleto } from "@/modules/personal/services/personalCompletoServices";
import { getLocalTodayIso, formatFecha } from "@/utils/dateTime";
import { stripSuccessMessageState } from "@/lib/memoriaNavigation";

const iconClass = "h-5 w-5 shrink-0 text-slate-400";
const cardClass = "min-w-0 rounded-2xl border border-slate-200 bg-white/80 p-5 shadow-sm sm:p-6";

export default function BecarioDatosSection({ data }: { data: PersonalCompleto }) {
  const [showHoras, setShowHoras] = useState(false);
  const location = useLocation();
  const becaNavigationState = { becarioReturnTo: {
    pathname: `/personal/becario/${data.id}`,
    search: location.search,
    hash: location.hash,
    state: stripSuccessMessageState(location.state),
  } };
  const today = getLocalTodayIso();
  const becas = data.becas ?? [];
  const fields = [
    ["Nombre", data.nombre || "Sin registrar"],
    ["Apellido", data.apellido || "Sin registrar"],
    ["DNI", data.dni || "Sin registrar"],
    ["CUIL", data.cuil || "Sin registrar"],
    ["Fecha de alta en el grupo", formatFecha(data.fecha_alta_grupo)],
    ["Tipo de formación", data.relaciones?.tipo_formacion?.nombre || data.tipo_formacion || "Sin registrar"],
  ];

  return <div className="[container-type:inline-size]">
    <div className="grid items-start gap-6 [@container(min-width:1000px)]:grid-cols-[minmax(0,1fr)_330px]">
      <article className={cardClass} aria-labelledby="datos-becario-title">
        <header className="mb-5 flex items-center justify-between gap-3">
          <h3 id="datos-becario-title" className="text-lg font-semibold text-slate-800">Datos del becario</h3>
          <User className={iconClass} strokeWidth={1.5} aria-hidden="true" />
        </header>
        <dl className="grid grid-cols-1 gap-x-6 gap-y-5 text-sm text-slate-500 [@container(min-width:480px)]:grid-cols-2">
          {fields.map(([label, value]) => <div key={label} className="min-w-0">
            <dt className="font-semibold text-slate-800">{label}</dt>
            <dd className="mt-1 break-words">{value}</dd>
          </div>)}
        </dl>
        <div className="mt-6 border-t border-slate-200 pt-5 text-sm text-slate-500">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-semibold text-slate-800">Horas semanales:</span>
            <span>{data.horas_semanales}</span>
            {!!data.historial_horas?.length && <button type="button" onClick={() => setShowHoras(value => !value)}
              aria-expanded={showHoras} aria-controls="becario-historial-horas" aria-label="Ver historial de horas" title="Ver historial de horas"
              className="inline-flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-slate-50 text-slate-600 shadow-sm hover:bg-slate-100">
              <ChevronDown className={`h-4 w-4 transition-transform ${showHoras ? "rotate-180" : ""}`} aria-hidden="true" />
            </button>}
          </div>
          {showHoras && <div id="becario-historial-horas" className="mt-3 space-y-1 border-l border-slate-200 pl-4">
            {data.historial_horas?.map(item => <p key={item.id} className="break-words">
              Horas: {item.horas_semanales} - Período: {formatFecha(item.fecha_inicio)} - {item.fecha_fin ? formatFecha(item.fecha_fin) : "Actual"}
            </p>)}
          </div>}
        </div>
      </article>

      <article className={cardClass} aria-labelledby="becas-asignadas-title">
        <header className="mb-5 flex items-center justify-between gap-3">
          <h3 id="becas-asignadas-title" className="text-lg font-semibold text-slate-800">Becas asignadas</h3>
          <GraduationCap className={iconClass} strokeWidth={1.5} aria-hidden="true" />
        </header>
        {!becas.length ? <div className="flex items-start gap-3 text-sm text-slate-500">
          <GraduationCap className={iconClass} strokeWidth={1.5} aria-hidden="true" />
          <p>Este becario no tiene becas asignadas</p>
        </div> : <ul className="space-y-4">
          {becas.map((beca, index) => {
            const status = !beca.fecha_inicio ? "Sin fecha de inicio"
              : beca.fecha_inicio > today ? "Próxima"
              : beca.fecha_fin && beca.fecha_fin < today ? "Finalizada" : "Activa";
            return <li key={`${beca.id}-${index}`} className="min-w-0 space-y-3 border-t border-slate-200 pt-4 first:border-t-0 first:pt-0">
              <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${status === "Activa" ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>{status}</span>
              <h4 className="break-words text-sm font-semibold text-slate-800">{beca.nombre_beca || "Beca sin nombre"}</h4>
              <p className="flex items-start gap-2 text-sm text-slate-500">
                <CalendarDays className="mt-0.5 h-[18px] w-[18px] shrink-0 text-slate-400" strokeWidth={1.5} aria-hidden="true" />
                <span className="min-w-0 break-words">{beca.fecha_inicio ? formatFecha(beca.fecha_inicio) : "Sin fecha de inicio"} — {beca.fecha_fin ? formatFecha(beca.fecha_fin) : "Sin fecha de fin"}</span>
              </p>
              <dl className="text-sm">
                <dt className="font-medium text-slate-800">Monto percibido</dt>
                <dd className="mt-1 break-words text-slate-500">{beca.monto_percibido != null
                  ? new Intl.NumberFormat("es-AR", { style: "currency", currency: "ARS" }).format(beca.monto_percibido)
                  : "Sin registrar"}</dd>
              </dl>
              <Link to={`/becas/${beca.id}`} state={becaNavigationState} aria-label={`Ver detalle de ${beca.nombre_beca || "la beca"}`}
                className="inline-flex rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 shadow-sm hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-500">Ver detalle</Link>
            </li>;
          })}
        </ul>}
      </article>
    </div>
  </div>;
}
