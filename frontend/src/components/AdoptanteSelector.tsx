import { useState, useMemo } from "react";
import Button from "@/components/Button";
import SuccessToast from "@/components/SuccessToast";
import { useAdoptantes, useCreateAdoptante } from "@/modules/transferencia/hooks/useAdoptantes";
import type { Adoptante, AdoptantePayload } from "@/modules/transferencia/services/adoptantesServices";
import { applyFieldErrors, focusFieldErrors, getErrorMessage } from "@/lib/httpError";
import { hasOnlyLettersAndSpaces } from "../lib/textValidation";

type Props = {
    selected: Adoptante[];
    onChange: (adoptantes: Adoptante[]) => void;
};

/**
 * Selector múltiple de adoptantes con búsqueda, chips de seleccionados,
 * y formulario inline para crear un adoptante nuevo.
 */
export default function AdoptanteSelector({ selected, onChange }: Props) {
    const { list: allAdoptantes } = useAdoptantes();
    const createMut = useCreateAdoptante();

    const [search, setSearch] = useState("");
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const [showForm, setShowForm] = useState(false);
    const [showError, setShowError] = useState(false);
    const [errorMessage, setErrorMessage] = useState("");
    const [formErrors, setFormErrors] = useState<Record<string, string>>({});

    // Adoptantes no seleccionados aún, filtrados por búsqueda
    const options = useMemo(() => {
        const selectedIds = new Set(selected.map((a) => a.id));
        return allAdoptantes
            .filter((a) => !selectedIds.has(a.id))
            .filter(
                (a) =>
                    !search ||
                    a.nombre.toLowerCase().includes(search.toLowerCase())
            );
    }, [allAdoptantes, selected, search]);

    const add = (adoptante: Adoptante) => {
        onChange([...selected, adoptante]);
        setSearch("");
        setDropdownOpen(false);
    };

    const remove = (id: number) => {
        onChange(selected.filter((a) => a.id !== id));
    };

    // ── Form inline state ──
    const [formNombre, setFormNombre] = useState("");

    const submitNew = async () => {
        if (createMut.isPending) return;
        if (!formNombre.trim()) {
            const next = { nombre: "Ingrese el nombre del adoptante." };
            setFormErrors(next);
            focusFieldErrors(next);
            return;
        }
        if (!hasOnlyLettersAndSpaces(formNombre)) {
            const next = { nombre: "Use solo letras y espacios en el nombre." };
            setFormErrors(next);
            focusFieldErrors(next);
            return;
        }
        setShowError(false);
        const payload: AdoptantePayload = { nombre: formNombre.trim() };
        try {
            const created = await createMut.mutateAsync(payload);
            add(created);
            setFormNombre("");
            setFormErrors({});
            setShowForm(false);
        } catch (err: unknown) {
            if (applyFieldErrors(err, setFormErrors, ["nombre"])) return;
            setErrorMessage(getErrorMessage(err, "Lo sentimos, no pudimos crear el adoptante. Verifique los datos e intente nuevamente."));
            setShowError(true);
        }
    };

    return (
        <div className="space-y-3">
            <label className="block text-sm font-medium">Adoptantes</label>

            {/* Chips seleccionados */}
            {selected.length > 0 && (
                <div className="flex flex-wrap gap-2">
                    {selected.map((a) => (
                        <span
                            key={a.id}
                            className="inline-flex items-center gap-1 rounded-full bg-slate-100 border border-slate-300 px-3 py-1 text-xs"
                        >
                            {a.nombre}
                            <button
                                type="button"
                                onClick={() => remove(a.id)}
                                className="ml-0.5 text-slate-500 hover:text-red-600"
                            >
                                ✕
                            </button>
                        </span>
                    ))}
                </div>
            )}

            {/* Búsqueda + dropdown */}
            <div className="relative">
                <input
                    className="input text-sm"
                    placeholder="Buscar adoptante…"
                    value={search}
                    onChange={(e) => {
                        setSearch(e.target.value);
                        setDropdownOpen(true);
                    }}
                    onFocus={() => setDropdownOpen(true)}
                />

                {dropdownOpen && (search || options.length > 0) && (
                    <ul className="absolute z-20 mt-1 max-h-48 w-full overflow-auto rounded-lg border border-slate-200 bg-white shadow-lg text-sm">
                        {options.length === 0 ? (
                            <li className="px-3 py-2 text-slate-400">Sin resultados</li>
                        ) : (
                            options.map((a) => (
                                <li key={a.id}>
                                    <button
                                        type="button"
                                        className="w-full text-left px-3 py-2 hover:bg-slate-50"
                                        onClick={() => add(a)}
                                    >
                                        {a.nombre}
                                    </button>
                                </li>
                            ))
                        )}
                    </ul>
                )}
            </div>

            {/* Cerrar dropdown al hacer click fuera */}
            {dropdownOpen && (
                <div
                    className="fixed inset-0 z-10"
                    onClick={() => setDropdownOpen(false)}
                />
            )}

            {/* Botón crear nuevo */}
            {!showForm && (
                <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    className="px-3 py-1 text-xs"
                    onClick={() => setShowForm(true)}
                >
                    + Crear nuevo adoptante
                </Button>
            )}

            {/* Formulario inline — solo nombre (lo que soporta el backend) */}
            {showForm && (
                <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 space-y-3">
                    <p className="text-sm font-medium">Nuevo adoptante</p>

                    <div data-error-field="nombre">
                        <label htmlFor="nuevo-adoptante-nombre" className="block text-sm font-medium">Nombre del adoptante *</label>
                        <input
                            id="nuevo-adoptante-nombre"
                            className={`input text-sm ${formErrors.nombre ? "border-red-500" : ""}`}
                            placeholder="Ingrese el nombre"
                            value={formNombre}
                            aria-invalid={Boolean(formErrors.nombre)}
                            aria-describedby={formErrors.nombre ? "nuevo-adoptante-error" : undefined}
                            onChange={(e) => {
                                setFormNombre(e.target.value);
                                if (formErrors.nombre) setFormErrors((previous) => ({ ...previous, nombre: "" }));
                            }}
                        />
                        {formErrors.nombre && <p id="nuevo-adoptante-error" role="alert" className="mt-1 text-sm text-red-600">{formErrors.nombre}</p>}
                    </div>

                    <div className="flex gap-2 justify-end">
                        <Button
                            type="button"
                            variant="secondary"
                            size="sm"
                            className="px-3 py-1 text-xs"
                            onClick={() => {
                                setShowForm(false);
                                setFormNombre("");
                                setFormErrors({});
                            }}
                        >
                            Cancelar
                        </Button>
                        <Button
                            type="button"
                            size="sm"
                            className="px-3 py-1 text-xs"
                            disabled={createMut.isPending}
                            onClick={submitNew}
                        >
                            {createMut.isPending ? "Creando…" : "Crear y agregar"}
                        </Button>
                    </div>
                </div>
            )}

            <SuccessToast
                open={showError}
                message={errorMessage}
                onClose={() => setShowError(false)}
                variant="error"
            />
        </div>
    );
}
