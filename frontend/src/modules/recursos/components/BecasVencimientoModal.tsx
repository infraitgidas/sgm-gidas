import { useEffect, useId, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Button from "@/components/Button";
import { useAuth } from "@/context/AuthContext";
import { getBecasProximasAVencer } from "@/modules/recursos/services/becasService";
import { formatFecha } from "@/utils/dateTime";
import { getLocalIsoDate } from "@/modules/recursos/utils/equipamientoValidation";

export default function BecasVencimientoModal() {
  const { isGestor, user } = useAuth();
  const gestor = isGestor();
  const query = useQuery({
    queryKey: ["becas", "proximas-a-vencer"],
    queryFn: getBecasProximasAVencer,
    enabled: gestor,
    staleTime: 60_000,
  });
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const [index, setIndex] = useState(0);
  const [dismissed, setDismissed] = useState(false);
  const today = getLocalIsoDate();
  const alertsKey = query.data?.map((item) => `${item.vinculacion_id}:${item.fecha_fin}`).join(",") ?? "";
  const key = `becas-vencimiento:${user?.id ?? ""}:${today}:${alertsKey}`;
  const visible = gestor && !dismissed && Boolean(query.data?.length) && sessionStorage.getItem(key) !== "1";

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!visible || !dialog) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    dialog.querySelector<HTMLElement>("button")?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (previousFocus?.isConnected) previousFocus.focus();
    };
  }, [visible]);

  const close = () => {
    sessionStorage.setItem(key, "1");
    setDismissed(true);
  };
  if (!visible) return null;
  const alerts = query.data ?? [];
  const currentIndex = Math.min(index, alerts.length - 1);
  const alert = alerts[currentIndex];
  return <dialog ref={dialogRef} aria-labelledby={titleId} onCancel={(event) => { event.preventDefault(); close(); }}
    className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-lg rounded-2xl border border-amber-200 bg-white p-6 shadow-xl backdrop:bg-slate-950/50">
    <p className="text-xs font-semibold uppercase tracking-wider text-amber-800">Aviso de vencimiento</p>
    <h2 id={titleId} className="mt-2 text-xl font-semibold text-slate-900">Una beca está próxima a finalizar</h2>
    <p className="mt-4 text-sm text-slate-600">{currentIndex + 1} de {alerts.length} avisos</p>
    <div className="my-5 rounded-xl border border-amber-200 bg-amber-50 p-5 text-center" role="status">
      <p className="text-sm font-medium text-amber-900">Tiempo restante</p>
      <p className="mt-1 text-5xl font-bold tabular-nums text-amber-950">{alert.dias_restantes}</p>
      <p className="text-lg font-semibold text-amber-950">{alert.dias_restantes === 1 ? "día" : "días"}</p>
    </div>
    <dl className="space-y-3 text-sm">
      <div><dt className="font-semibold text-slate-800">Becario</dt><dd className="text-slate-600">{alert.becario}</dd></div>
      <div><dt className="font-semibold text-slate-800">Beca</dt><dd className="text-slate-600">{alert.beca}</dd></div>
      <div><dt className="font-semibold text-slate-800">Finaliza el</dt><dd className="text-slate-600">{formatFecha(alert.fecha_fin)}</dd></div>
    </dl>
    <div className="mt-6 flex justify-end gap-2">
      <Button type="button" variant="secondary" onClick={close}>Cerrar</Button>
      {currentIndex < alerts.length - 1 && <Button type="button" onClick={() => setIndex(currentIndex + 1)}>Siguiente aviso</Button>}
    </div>
  </dialog>;
}
