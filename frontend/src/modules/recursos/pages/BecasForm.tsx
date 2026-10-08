import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import Button from "@/components/Button";
import Field from "@/components/Field";
import LoadingSkeleton from "@/components/LoadingSkeleton";
import SuccessToast from "@/components/SuccessToast";
import { useFuentesFinanciamiento } from "@/modules/catalogos/hooks/useFuenteFinanciamiento";
import { applyFieldErrors, getErrorMessage } from "@/lib/httpError";
import { createBeca, getBecaById, updateBeca, type BecaPayload } from "@/modules/recursos/services/becasService";
import { getLocalIsoDate } from "@/modules/recursos/utils/equipamientoValidation";

type FormData = { nombre_beca: string; descripcion: string; fecha_alta_grupo: string; fuente_financiamiento_id: string };
const empty: FormData = { nombre_beca: "", descripcion: "", fecha_alta_grupo: "", fuente_financiamiento_id: "" };

export default function BecasForm() {
  const { id } = useParams<{ id: string }>();
  const isEdit = Boolean(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const initial = useQuery({ queryKey: ["beca", id], queryFn: () => getBecaById(Number(id)), enabled: isEdit });
  const { fuentes, isLoading: loadingFuentes, isError: fuentesError } = useFuentesFinanciamiento();
  const [form, setForm] = useState<FormData>(empty);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState("");
  const mutation = useMutation({
    mutationFn: (payload: BecaPayload | Partial<BecaPayload>) => isEdit ? updateBeca(Number(id), payload) : createBeca(payload as BecaPayload),
    onSuccess: async (beca) => {
      await queryClient.invalidateQueries({ queryKey: ["becas"] });
      navigate(isEdit ? `/becas/${beca.id}` : "/becas", { state: { successMessage: isEdit ? "Beca actualizada con éxito." : "Beca creada con éxito." } });
    },
  });

  useEffect(() => {
    if (!initial.data) return;
    setForm({
      nombre_beca: initial.data.nombre_beca ?? "",
      descripcion: initial.data.descripcion ?? "",
      fecha_alta_grupo: initial.data.fecha_alta_grupo ?? "",
      fuente_financiamiento_id: initial.data.fuente_financiamiento_id?.toString() ?? "",
    });
  }, [initial.data]);

  const setField = (key: keyof FormData, value: string) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => { const next = { ...current }; delete next[key]; return next; });
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};
    const name = form.nombre_beca.trim().replace(/\s+/g, " ");
    if (!name) nextErrors.nombre_beca = "Ingrese el nombre de la beca.";
    else if (name.length > 100 || !/[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]/.test(name)) nextErrors.nombre_beca = "Ingrese un nombre válido de hasta 100 caracteres.";
    if (form.descripcion.trim().length > 2000) nextErrors.descripcion = "La descripción no puede superar 2000 caracteres.";
    if (!form.fecha_alta_grupo || form.fecha_alta_grupo < "2010-01-01" || form.fecha_alta_grupo > getLocalIsoDate()) nextErrors.fecha_alta_grupo = "Ingrese una fecha válida entre 2010 y hoy.";
    if (form.fuente_financiamiento_id && !fuentes.some((item) => item.id === Number(form.fuente_financiamiento_id))) nextErrors.fuente_financiamiento_id = "Seleccione una fuente disponible.";
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      const first = Object.keys(nextErrors)[0];
      window.requestAnimationFrame(() => document.querySelector<HTMLElement>(`[data-error-field="${first}"]`)?.focus());
      return;
    }
    const payload: BecaPayload = {
      nombre_beca: name,
      descripcion: form.descripcion.trim() || null,
      fecha_alta_grupo: form.fecha_alta_grupo || null,
      fuente_financiamiento_id: form.fuente_financiamiento_id ? Number(form.fuente_financiamiento_id) : null,
    };
    const original: BecaPayload = {
      nombre_beca: initial.data?.nombre_beca ?? "",
      descripcion: initial.data?.descripcion || null,
      fecha_alta_grupo: initial.data?.fecha_alta_grupo || null,
      fuente_financiamiento_id: initial.data?.fuente_financiamiento_id ?? null,
    };
    const changes = Object.fromEntries(Object.entries(payload).filter(([key, value]) => value !== original[key as keyof BecaPayload])) as Partial<BecaPayload>;
    if (isEdit && !Object.keys(changes).length) {
      navigate(`/becas/${id}`, { state: { successMessage: "No hubo cambios para actualizar." } });
      return;
    }
    try {
      await mutation.mutateAsync(isEdit ? changes : payload);
    } catch (cause) {
      applyFieldErrors(cause, setErrors, ["nombre_beca", "descripcion", "fecha_alta_grupo", "fuente_financiamiento_id"]);
      setServerError(getErrorMessage(cause, "Lo sentimos, no pudimos guardar los cambios. Verifique los datos e intente nuevamente."));
    }
  };

  if (initial.isLoading || loadingFuentes) return <LoadingSkeleton variant="form" label="Cargando beca..." />;
  if (isEdit && (initial.isError || !initial.data)) return <p role="alert">Lo sentimos, no pudimos recuperar la información. Intente nuevamente.</p>;

  return <>
    <section className="w-full">
      <h2 className="text-2xl font-semibold md:text-3xl">{isEdit ? "Editar beca" : "Nueva beca"}</h2>
      <form noValidate onSubmit={submit} className="mt-6 space-y-6 rounded-2xl border border-slate-200 bg-white p-6">
        <Field required label="Nombre de la beca" name="nombre_beca" error={errors.nombre_beca}>
          <input className="input w-full" maxLength={100} value={form.nombre_beca} placeholder="Ej.: Beca de investigación" onChange={(event) => setField("nombre_beca", event.target.value)} />
        </Field>
        <Field label="Descripción" name="descripcion" error={errors.descripcion}>
          <textarea className="input w-full" rows={4} maxLength={2000} value={form.descripcion} placeholder="Describa el propósito de la beca" onChange={(event) => setField("descripcion", event.target.value)} />
        </Field>
        <Field required label="Fecha de alta en el grupo" name="fecha_alta_grupo" error={errors.fecha_alta_grupo}>
          <input type="date" className="input w-full" min="2010-01-01" max={getLocalIsoDate()} value={form.fecha_alta_grupo} onChange={(event) => setField("fecha_alta_grupo", event.target.value)} />
        </Field>
        <Field label="Fuente de financiamiento" name="fuente_financiamiento_id" error={errors.fuente_financiamiento_id}>
          <select className="input w-full" value={form.fuente_financiamiento_id} onChange={(event) => setField("fuente_financiamiento_id", event.target.value)}>
            <option value="">Sin fuente de financiamiento</option>
            {fuentes.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
          </select>
        </Field>
        {fuentesError && <p role="alert" className="text-sm text-rose-700">No pudimos cargar las fuentes. Intente nuevamente.</p>}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" loading={mutation.isPending} disabled={fuentesError}>{isEdit ? "Guardar cambios" : "Crear beca"}</Button>
          <Button type="button" variant="secondary" onClick={() => navigate(isEdit ? `/becas/${id}` : "/becas")}>Volver</Button>
        </div>
      </form>
    </section>
    <SuccessToast open={Boolean(serverError)} message={serverError} variant="error" onClose={() => setServerError("")} />
  </>;
}
