import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import Button from "@/components/Button";
import DatePicker from "@/components/Calendar";
import Field from "@/components/Field";
import SuccessToast from "@/components/SuccessToast";
import { useAuth } from "@/context/AuthContext";
import { HttpError } from "@/lib/http";
import { applyFieldErrors, getApiFieldErrors, getErrorMessage } from "@/lib/httpError";
import { useFuentesFinanciamiento } from "@/modules/catalogos/hooks/useFuenteFinanciamiento";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";
import { useCategoriasErogacion } from "@/modules/recursos/hooks/useCategoriasErogacion";
import { useCotizacionMovimiento } from "@/modules/recursos/hooks/useCotizacionMovimiento";
import {
  createErogacion, getEquipamientosDisponibles, getErogacionById, getSaldosPorFuente,
  updateErogacion,
  type CreateErogacionPayload, type MonedaMovimiento, type TipoMovimiento, type UpdateMovimientoPayload,
} from "@/modules/recursos/services/erogacionesServices";
import DraftLeaveControls from "@/modules/shared/components/DraftLeaveControls";
import DraftRecoveryNotice from "@/modules/shared/components/DraftRecoveryNotice";
import { useFormDraft } from "@/modules/shared/hooks/useFormDraft";
import { formatMovimientoMoney } from "@/modules/recursos/utils/movimientoHistory";
import { equivalenteArs, excedeSaldoDisponible } from "@/modules/recursos/utils/movimientoSaldo";
import { formatFecha, toCivilDateString } from "@/utils/dateTime";

type FormData = {
  tipo_movimiento: TipoMovimiento | "";
  moneda: MonedaMovimiento;
  fecha: string;
  monto: string;
  fuente_financiamiento_id: string;
  categoria_erogacion_id: string;
  equipamiento_id: string;
};

const emptyData: FormData = {
  tipo_movimiento: "", moneda: "ARS", fecha: "", monto: "",
  fuente_financiamiento_id: "", categoria_erogacion_id: "",
  equipamiento_id: "",
};

function normalizarMonto(value: string): string {
  const [entero, decimales = ""] = value.trim().split(".");
  return `${BigInt(entero)}.${decimales.padEnd(2, "0")}`;
}

export default function ErogacionesForm() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const { uct, uctGuard } = useUctGuard();
  const { user } = useAuth();
  const { fuentes } = useFuentesFinanciamiento();
  const { data: categorias = [] } = useCategoriasErogacion();
  const [data, setData] = useState<FormData>(emptyData);
  const { data: cotizacion, isLoading: cotizacionLoading, isError: cotizacionError, refetch: refetchCotizacion } =
    useCotizacionMovimiento(data.fecha, !isEdit && data.moneda === "USD");
  const { data: equipos = [], isError: equiposError, refetch: refetchEquipos } = useQuery({
    queryKey: ["equipamientos-disponibles", uct?.id, id],
    queryFn: () => getEquipamientosDisponibles(uct!.id, isEdit ? Number(id) : undefined),
    enabled: Boolean(uct?.id) && data.tipo_movimiento === "EGRESO",
  });
  const { data: movimiento, isLoading: loadingMovimiento, refetch: refetchMovimiento } = useQuery({
    queryKey: ["erogaciones", id],
    queryFn: () => getErogacionById(Number(id)),
    enabled: isEdit,
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [errorMessage, setErrorMessage] = useState("");
  const [checkingSaldo, setCheckingSaldo] = useState(false);
  const [insufficientBalance, setInsufficientBalance] = useState<string | null>(null);
  const balanceDialog = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = balanceDialog.current;
    if (!dialog) return;
    if (insufficientBalance !== null && !dialog.open) {
      dialog.showModal();
      dialog.querySelector<HTMLButtonElement>("button")?.focus();
    } else if (insufficientBalance === null && dialog.open) {
      dialog.close();
    }
  }, [insufficientBalance]);

  useEffect(() => {
    if (!movimiento) return;
    setData({
      tipo_movimiento: movimiento.tipo_movimiento,
      moneda: movimiento.moneda,
      fecha: movimiento.fecha,
      monto: movimiento.monto,
      fuente_financiamiento_id: movimiento.fuente_financiamiento_id?.toString() ?? "",
      categoria_erogacion_id: movimiento.categoria_erogacion_id?.toString() ?? "",
      equipamiento_id: movimiento.equipamiento_id?.toString() ?? "",
    });
  }, [movimiento]);

  const {
    availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft,
    saveStatus, blocker, requestLeave, keepAndLeave, discardAndLeave,
  } = useFormDraft({
    userId: user?.id,
    module: "recursos-erogaciones",
    recordId: id,
    value: data,
    ready: !isEdit || (!loadingMovimiento && Boolean(movimiento)),
    autosave: false,
    hasContent: (draft) => Object.values(draft).some((value) => value.trim() !== ""),
    onRestore: setData,
  });

  const { mutateAsync, isPending } = useMutation({
    mutationFn: (payload: CreateErogacionPayload | UpdateMovimientoPayload) =>
      isEdit
        ? updateErogacion(Number(id), payload as UpdateMovimientoPayload)
        : createErogacion(payload as CreateErogacionPayload),
    onSuccess: async (saved) => {
      clearDraft();
      await qc.invalidateQueries({ queryKey: ["erogaciones"] });
      await qc.invalidateQueries({ queryKey: ["resumen-financiero"] });
      await qc.invalidateQueries({ queryKey: ["saldos-por-fuente"] });
      await qc.invalidateQueries({ queryKey: ["equipamientos-disponibles"] });
      await qc.invalidateQueries({ queryKey: ["erogacion-historial", saved.id] });
      await qc.invalidateQueries({ queryKey: ["movimiento-financiero-historial", saved.id] });
      navigate(isEdit ? `/movimientos/${saved.id}` : "/movimientos", {
        replace: true,
        state: { successMessage: isEdit
          ? "Movimiento actualizado con éxito."
          : "Movimiento creado con éxito." },
      });
    },
    onError: async (error) => {
      if (data.tipo_movimiento === "EGRESO" && error instanceof HttpError &&
          error.status === 409 && getApiFieldErrors(error).monto && uct) {
        try {
          const saldos = await getSaldosPorFuente(uct.id);
          qc.setQueryData(["saldos-por-fuente", uct.id], saldos);
          setInsufficientBalance(saldos.find((item) => item.fuente_id === Number(data.fuente_financiamiento_id))?.saldo_disponible ?? "0.00");
        } catch {
          setErrorMessage("Lo sentimos, no pudimos consultar el saldo disponible. Intente nuevamente.");
        }
        return;
      }
      if (applyFieldErrors(error, setErrors, [
        "tipo_movimiento", "moneda", "fecha", "monto", "fuente_financiamiento_id", "categoria_erogacion_id", "equipamiento_id",
      ])) return;
      setErrorMessage(getErrorMessage(
        error,
        "Lo sentimos, no pudimos guardar el movimiento. Verifique los datos e intente nuevamente.",
      ));
    },
  });

  const setField = <K extends keyof FormData>(field: K, value: FormData[K]) => {
    setData((previous) => ({ ...previous, [field]: value }));
    setErrors((previous) => ({ ...previous, [field]: "" }));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (isPending || checkingSaldo || !uct) return;
    const nextErrors: Record<string, string> = {};
    if (data.tipo_movimiento !== "INGRESO" && data.tipo_movimiento !== "EGRESO") nextErrors.tipo_movimiento = "Seleccione ingreso o egreso.";
    if (data.moneda === "USD" && !isEdit && !cotizacion) nextErrors.moneda = "No existe una cotización oficial disponible. Seleccione otra fecha o reintente.";
    if (!data.fecha) nextErrors.fecha = "Seleccione la fecha del movimiento.";
    if (!/^\d{1,16}(\.\d{1,2})?$/.test(data.monto.trim()) || Number(data.monto) <= 0) {
      nextErrors.monto = "Ingrese un monto mayor que cero, con hasta dos decimales.";
    }
    if (!data.fuente_financiamiento_id) {
      nextErrors.fuente_financiamiento_id = "Seleccione la fuente de financiamiento.";
    }
    if (data.tipo_movimiento === "EGRESO" && !data.categoria_erogacion_id) {
      nextErrors.categoria_erogacion_id = "Seleccione la categoría de erogación.";
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) return;
    setErrorMessage("");

    const monto = normalizarMonto(data.monto);
    let payload: CreateErogacionPayload | UpdateMovimientoPayload;
    if (!isEdit) {
      payload = {
        tipo_movimiento: data.tipo_movimiento as TipoMovimiento,
        moneda: data.moneda,
        monto, fecha: data.fecha, grupo_utn_id: uct.id,
        fuente_financiamiento_id: Number(data.fuente_financiamiento_id),
        ...(data.tipo_movimiento === "EGRESO" ? {
          categoria_erogacion_id: Number(data.categoria_erogacion_id),
          ...(data.equipamiento_id ? { equipamiento_id: Number(data.equipamiento_id) } : {}),
        } : {}),
      };
    } else {
      if (!movimiento) return;
      const changes: UpdateMovimientoPayload = {};
      if (data.fecha !== movimiento.fecha) changes.fecha = data.fecha;
      if (monto !== normalizarMonto(movimiento.monto)) changes.monto = monto;
      if (Number(data.fuente_financiamiento_id) !== movimiento.fuente_financiamiento_id) {
        changes.fuente_financiamiento_id = Number(data.fuente_financiamiento_id);
      }
      if (data.tipo_movimiento === "EGRESO" &&
          Number(data.categoria_erogacion_id) !== movimiento.categoria_erogacion_id) {
        changes.categoria_erogacion_id = Number(data.categoria_erogacion_id);
      }
      if (data.tipo_movimiento === "EGRESO" &&
          (data.equipamiento_id ? Number(data.equipamiento_id) : null) !== movimiento.equipamiento_id) {
        changes.equipamiento_id = data.equipamiento_id ? Number(data.equipamiento_id) : null;
      }
      if (!Object.keys(changes).length) {
        clearDraft();
        navigate(`/movimientos/${id}`, {
          replace: true, state: { successMessage: "No hubo cambios para actualizar." },
        });
        return;
      }
      payload = changes;
    }

    if (data.tipo_movimiento === "EGRESO") {
      setCheckingSaldo(true);
      try {
        const saldos = await getSaldosPorFuente(uct.id);
        qc.setQueryData(["saldos-por-fuente", uct.id], saldos);
        const saldoFuente = saldos.find((item) => item.fuente_id === Number(data.fuente_financiamiento_id))?.saldo_disponible ?? "0.00";
        const montoArs = data.moneda === "USD" ? equivalenteArs(monto, (isEdit ? movimiento?.tipo_cambio_aplicado : cotizacion?.valor)!) : monto;
        const montoAnterior = isEdit && movimiento?.fuente_financiamiento_id === Number(data.fuente_financiamiento_id) ? movimiento.monto_equivalente_ars ?? movimiento.monto : "0.00";
        if (excedeSaldoDisponible(montoArs, saldoFuente, montoAnterior)) {
          setInsufficientBalance(saldoFuente);
          return;
        }
      } catch {
        setErrorMessage("Lo sentimos, no pudimos consultar el saldo disponible. Intente nuevamente.");
        return;
      } finally {
        setCheckingSaldo(false);
      }
    }
    try {
      await mutateAsync(payload);
    } catch {
      // El callback onError presenta el error del backend o actualiza el saldo del diálogo.
    }
  };

  if (isEdit && loadingMovimiento) return <LoadingSkeleton variant="form" label="Cargando movimiento..." />;
  if (isEdit && !movimiento) return <div role="alert" className="flex items-center gap-3 text-slate-600">Lo sentimos, no pudimos recuperar el movimiento. Intente nuevamente.<Button size="sm" variant="secondary" onClick={() => refetchMovimiento()}>Reintentar</Button></div>;

  return (
    <section className="w-full">
      <h2 className="text-2xl font-semibold leading-none md:text-3xl">
        {isEdit ? "Editar movimiento" : "Nuevo movimiento"}
      </h2>
      {availableDraft && <DraftRecoveryNotice savedAt={availableDraft.saved_at} sourceChanged={sourceChanged} onRestore={restoreDraft} onDiscard={discardDraft} />}
      <DraftLeaveControls blocker={blocker} saveStatus={saveStatus} keepAndLeave={keepAndLeave} discardAndLeave={discardAndLeave} />
      <form noValidate onSubmit={submit} className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6">
        {isEdit && movimiento && <p className="text-sm text-slate-600">Movimiento N.º {String(movimiento.numero_movimiento).padStart(6, "0")}</p>}
        <Field required label="Tipo de movimiento" name="tipo_movimiento" error={errors.tipo_movimiento}>
          {isEdit ? <p className="rounded-lg border border-slate-200 bg-slate-50 p-2">{data.tipo_movimiento === "INGRESO" ? "Ingreso" : "Egreso"}</p> : (
            <select className="input" value={data.tipo_movimiento} onChange={(event) => {
              setData((previous) => ({ ...previous, tipo_movimiento: event.target.value as TipoMovimiento, fuente_financiamiento_id: "", categoria_erogacion_id: "", equipamiento_id: "" }));
              setErrors({});
            }}>
              <option value="">Seleccione el tipo</option>
              <option value="INGRESO">Ingreso</option>
              <option value="EGRESO">Egreso</option>
            </select>
          )}
        </Field>
        <Field required label="Fecha" name="fecha" error={errors.fecha}>
          {isEdit && data.moneda === "USD" ? <>
            <p className="rounded-lg border border-slate-200 bg-slate-50 p-2">{formatFecha(data.fecha)}</p>
            <p className="mt-1 text-xs text-slate-500">La fecha se conserva junto con la cotización histórica aplicada.</p>
          </> : <DatePicker value={data.fecha ? new Date(`${data.fecha}T00:00:00`) : null} maxDate={new Date()} onChange={(date) => setField("fecha", toCivilDateString(date) ?? "")} helperText="DD/MM/AAAA" />}
        </Field>
        {data.tipo_movimiento === "EGRESO" && data.moneda === "ARS" && <Field label="Equipamiento relacionado" name="equipamiento_id" error={errors.equipamiento_id}>
          <select className="input" value={data.equipamiento_id ?? ""} onChange={(event) => {
            const equipoId = event.target.value;
            const equipo = equipos.find((item) => String(item.id) === equipoId);
            const categoriaCapital = categorias.find((item) => item.codigo === "CAPITAL");
            setData((previous) => ({
              ...previous,
              equipamiento_id: equipoId,
              monto: equipo ? movimiento?.equipamiento_id === equipo.id ? movimiento.monto : equipo.monto_invertido : previous.monto,
              categoria_erogacion_id: equipo && categoriaCapital ? String(categoriaCapital.id) : previous.categoria_erogacion_id,
            }));
            setErrors((previous) => ({ ...previous, equipamiento_id: "", monto: "" }));
          }}>
            <option value="">Sin equipamiento relacionado</option>
            {data.equipamiento_id && movimiento?.equipamiento_id === Number(data.equipamiento_id) && !equipos.some((item) => item.id === movimiento.equipamiento_id) && <option value={data.equipamiento_id}>{movimiento.equipamiento?.denominacion ?? "Equipamiento vinculado"}</option>}
            {equipos.map((equipo) => <option key={equipo.id} value={equipo.id}>{equipo.denominacion}</option>)}
          </select>
          {equiposError && <p role="alert" className="mt-2 text-sm text-rose-700">Lo sentimos, no pudimos recuperar el equipamiento. <button type="button" className="underline" onClick={() => refetchEquipos()}>Intente nuevamente.</button></p>}
        </Field>}
        <Field required label="Monto" name="monto" error={errors.monto}>
          <input type="number" min="0.01" step="0.01" readOnly={Boolean(data.equipamiento_id)} className="input" value={data.monto} placeholder="Ej.: 150000.00" onChange={(event) => setField("monto", event.target.value)} />
          {data.equipamiento_id && <p className="mt-1 text-xs text-slate-500">El monto se toma del equipamiento al vincularlo y se conserva como importe histórico.</p>}
        </Field>
        <Field required label="Moneda" name="moneda" error={errors.moneda}>
          {isEdit ? <p className="rounded-lg border border-slate-200 bg-slate-50 p-2">{data.moneda}</p> :
            <select className="input" value={data.moneda} onChange={(event) => setData((previous) => ({ ...previous, moneda: event.target.value as MonedaMovimiento, equipamiento_id: "" }))}>
              <option value="ARS">ARS</option><option value="USD">USD</option>
            </select>}
        </Field>
        {data.moneda === "USD" && <div aria-live="polite" className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700">
          {isEdit && movimiento?.tipo_cambio ? <>
            <p>Cotización oficial diaria utilizada: ARS {movimiento.tipo_cambio_aplicado} / USD</p>
            <p>Fecha de cotización: {formatFecha(movimiento.tipo_cambio.fecha_cotizacion)}</p>
            <p>Equivalente: ARS {data.monto && /^\d+(\.\d{1,2})?$/.test(data.monto) ? equivalenteArs(data.monto, movimiento.tipo_cambio_aplicado!) : "—"}</p>
          </> : cotizacionLoading ? <p>Consultando cotización...</p> : cotizacionError ?
            <p role="alert">Lo sentimos, no pudimos recuperar la cotización. <button type="button" className="underline" onClick={() => refetchCotizacion()}>Intente nuevamente.</button></p> : cotizacion ? <>
            <p>Cotización oficial diaria utilizada: ARS {cotizacion.valor} / USD</p>
            <p>Fecha de cotización: {formatFecha(cotizacion.fecha_cotizacion)}</p>
            <p>Equivalente: ARS {data.monto && /^\d+(\.\d{1,2})?$/.test(data.monto) ? equivalenteArs(data.monto, cotizacion.valor) : "—"}</p>
          </> : <p>Seleccione la fecha para consultar la cotización oficial.</p>}
          <p className="mt-2 text-xs">Banco Central de la República Argentina · {((isEdit ? movimiento?.tipo_cambio : cotizacion)?.serie_bcra === 7927)
            ? "Tipo de Cambio Minorista · Com. B 9791 · Promedio vendedor"
            : `Serie ${(isEdit ? movimiento?.tipo_cambio : cotizacion)?.serie_bcra ?? "—"}`}</p>
        </div>}
        <Field required label="Fuente de financiamiento" name="fuente_financiamiento_id" error={errors.fuente_financiamiento_id}>
            <select className="input" value={data.fuente_financiamiento_id} onChange={(event) => setField("fuente_financiamiento_id", event.target.value)}>
              <option value="">Seleccione una fuente</option>
              {fuentes.map((fuente) => <option key={fuente.id} value={fuente.id}>{fuente.nombre}</option>)}
            </select>
        </Field>
        {data.tipo_movimiento === "EGRESO" && (
          <Field required label="Categoría de erogación" name="categoria_erogacion_id" error={errors.categoria_erogacion_id}>
            <select className="input" value={data.categoria_erogacion_id} onChange={(event) => setField("categoria_erogacion_id", event.target.value)}>
              <option value="">Seleccione una categoría</option>
              {categorias.map((categoria) => <option key={categoria.id} value={categoria.id}>{categoria.nombre}</option>)}
            </select>
          </Field>
        )}
        <div className="flex justify-between pt-6">
          <Button type="button" variant="secondary" size="sm" onClick={() => requestLeave(() => navigate(-1))}>Volver</Button>
          <Button type="submit" size="sm" disabled={isPending || checkingSaldo || !uct} loading={isPending || checkingSaldo} loadingText={checkingSaldo ? "Consultando saldo..." : "Guardando..."}>{isEdit ? "Actualizar" : "Guardar"}</Button>
        </div>
      </form>
      <SuccessToast open={Boolean(errorMessage)} message={errorMessage} onClose={() => setErrorMessage("")} variant="error" />
      <dialog ref={balanceDialog} aria-labelledby="saldo-insuficiente-title" aria-describedby="saldo-insuficiente-description" onCancel={() => setInsufficientBalance(null)} onClose={() => setInsufficientBalance(null)} className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-slate-200 bg-white p-6 shadow-xl backdrop:bg-slate-950/50">
        <h3 id="saldo-insuficiente-title" className="text-xl font-semibold text-slate-900">Saldo Insuficiente</h3>
        <p id="saldo-insuficiente-description" className="mt-3 text-sm text-slate-600">El egreso supera el saldo disponible de la fuente seleccionada. Revise el monto e intente nuevamente.</p>
        <p className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-700">Saldo disponible en la fuente: <strong className="block text-lg text-slate-900">{insufficientBalance === null ? "" : formatMovimientoMoney(insufficientBalance)}</strong></p>
        <div className="mt-6 flex justify-end"><Button type="button" size="sm" onClick={() => setInsufficientBalance(null)}>Aceptar</Button></div>
      </dialog>
      {uctGuard}
    </section>
  );
}
