import LoadingSkeleton from "@/components/LoadingSkeleton";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import Button from "@/components/Button";
import SuccessToast from "@/components/SuccessToast";
import { getErrorMessage } from "@/lib/httpError";
import { useUctGuard } from "@/modules/grupo/hooks/useUctGuard";

import FormPTAAProfesional from "./FormPTAAProfesional";
import FormBecario from "./FormBecario";
import FormInvestigador from "./FormInvestigador";

import { getPersonalCompletoByRolAndId } from "@/modules/personal/services/personalCompletoServices";

type Tipo = "" | "PERSONAL" | "BECARIO" | "INVESTIGADOR";

export default function PersonalForm() {
  const { rol: paramRol, id } = useParams<{ rol?: string; id?: string }>();
  const { uctGuard } = useUctGuard();

  const navigate = useNavigate();
  const location = useLocation();

  // Infer role from URL path when :rol param is absent
  // e.g. /becarios/5/editar -> "becario", /investigadores/5/editar -> "investigador"
  const inferredRol = (() => {
    if (paramRol) return paramRol;
    const path = location.pathname;
    if (path.includes("/becarios/")) return "becario";
    if (path.includes("/investigadores/")) return "investigador";
    return undefined;
  })();

  const isEdit = Boolean(id && inferredRol);

  const { data: initialData, isLoading, isError } = useQuery({
    queryKey: ["personal-edit", inferredRol, id],
    queryFn: () => getPersonalCompletoByRolAndId(inferredRol!, Number(id)),
    enabled: Boolean(inferredRol && id),
  });

  const requestedTipo = new URLSearchParams(location.search).get("tipo");
  const [tipo, setTipo] = useState<Tipo>(
    requestedTipo === "PERSONAL" || requestedTipo === "BECARIO" || requestedTipo === "INVESTIGADOR"
      ? requestedTipo : ""
  );
  const [errorTipo, setErrorTipo] = useState(false);

  // 🔥 TOAST STATE
  const [showSuccess, setShowSuccess] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [showError, setShowError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  const handleFormError = (error: unknown) => {
    setErrorMessage(
      getErrorMessage(
        error,
        isEdit
          ? "Lo sentimos, no pudimos actualizar el integrante. Revise los datos e intente nuevamente."
          : "Lo sentimos, no pudimos crear el integrante. Revise los datos e intente nuevamente."
      )
    );
    setShowError(true);
  };

  // 🔥 Escuchar mensaje desde navigate(state)
  useEffect(() => {
    if (location.state?.successMessage) {
      setSuccessMessage(location.state.successMessage);
      setShowSuccess(true);

      // limpiar state
      navigate(location.pathname, { replace: true });
    }
  }, [location.state]);

  useEffect(() => {
    if (!isEdit && (requestedTipo === "PERSONAL" || requestedTipo === "BECARIO" || requestedTipo === "INVESTIGADOR")) {
      setTipo(requestedTipo);
    }
  }, [isEdit, requestedTipo]);

  useEffect(() => {
    const r = inferredRol;
    if (!r) return;

    const rolMap: Record<string, Tipo> = {
      personal: "PERSONAL",
      profesional: "PERSONAL",
      becario: "BECARIO",
      investigador: "INVESTIGADOR",
    };

    const mapped = rolMap[r.toLowerCase()];
    if (mapped) setTipo(mapped);
  }, [inferredRol]);

  if (isLoading) return <LoadingSkeleton variant="form" label="Cargando…" />;
  if (isEdit && isError) {
    return (
      <p className="text-slate-500">
        Lo sentimos, no pudimos recuperar la información. Intente nuevamente.
      </p>
    );
  }

  const handleTipoChange = (value: Tipo) => {
    setTipo(value);
    if (value) setErrorTipo(false);
  };

  return (
    <section className="w-full">
      <h2 className="text-2xl md:text-3xl font-semibold leading-none">
        {isEdit ? "Editar personal" : "Nuevo personal"}
      </h2>

      <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 space-y-6">

        {!isEdit ? (
          <fieldset>
            <legend className="block text-sm font-medium mb-3">
              Clase de registro<span className="ml-1 text-rose-500" aria-hidden="true">*</span>
            </legend>
            <div className="grid gap-3 md:grid-cols-3">
              {([
                ["PERSONAL", "Personal de apoyo, técnico o administrativo", "Funciones de apoyo y gestión institucional."],
                ["BECARIO", "Becario", "Integrantes con formación y becas asociadas."],
                ["INVESTIGADOR", "Investigador", "Integrantes con dedicación y antecedentes de investigación."],
              ] as const).map(([value, label, description]) => (
                <button key={value} type="button" aria-pressed={tipo === value} onClick={() => handleTipoChange(value)}
                  className={`rounded-xl border p-4 text-left outline-none transition motion-reduce:transition-none focus-visible:ring-2 focus-visible:ring-slate-500 ${tipo === value ? "border-slate-800 bg-slate-50 ring-1 ring-slate-800" : "border-slate-200 hover:border-slate-400"}`}>
                  <span className="block text-sm font-semibold text-slate-900">{label}</span>
                  <span className="mt-1 block text-xs leading-5 text-slate-500">{description}</span>
                </button>
              ))}
            </div>

            {errorTipo && (
              <p className="text-red-500 text-sm mt-1">
                Debe seleccionar una clase de registro
              </p>
            )}
          </fieldset>
        ) : (
          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-500">Clase de registro</span>
            <p className="mt-1 font-medium text-slate-900">{tipo === "PERSONAL" ? "Personal de apoyo, técnico o administrativo" : tipo === "BECARIO" ? "Becario" : "Investigador"}</p>
            <p className="mt-1 text-xs text-slate-500">La clase no puede cambiarse porque corresponde a un tipo de registro persistente distinto.</p>
          </div>
        )}

        {!tipo && !isEdit && (
          <div className="border-t border-slate-200 pt-6 flex justify-start">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              className="px-3 py-1 text-xs"
              onClick={() => navigate(-1)}
            >
              Volver
            </Button>
          </div>
        )}

        {tipo === "PERSONAL" && (
          <FormPTAAProfesional
            key={`${tipo}-${id ?? "new"}`}
            initialData={initialData}
            onCancel={() => navigate(-1)}
            onError={handleFormError}
          />
        )}

        {tipo === "BECARIO" && (
          <FormBecario
            key={`${tipo}-${id ?? "new"}`}
            initialData={initialData}
            onCancel={() => navigate(-1)}
            onError={handleFormError}
          />
        )}

        {tipo === "INVESTIGADOR" && (
          <FormInvestigador
            key={`${tipo}-${id ?? "new"}`}
            initialData={initialData}
            onCancel={() => navigate(-1)}
            onError={handleFormError}
          />
        )}
      </div>

      {/* UCT GUARD */}
      {uctGuard}

      {/* 🔥 SUCCESS TOAST */}
      <SuccessToast
        open={showSuccess}
        message={successMessage}
        onClose={() => setShowSuccess(false)}
      />
      <SuccessToast
        open={showError}
        message={errorMessage}
        variant="error"
        onClose={() => setShowError(false)}
      />
    </section>
  );
}
