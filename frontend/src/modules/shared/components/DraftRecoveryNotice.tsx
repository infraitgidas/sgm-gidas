import { FileClock } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import Button from "@/components/Button";

type Props = {
  savedAt: string;
  onRestore: () => void;
  onDiscard: () => Promise<void>;
  sourceChanged?: boolean;
};

export default function DraftRecoveryNotice({ savedAt, onRestore, onDiscard, sourceChanged = false }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [error, setError] = useState("");
  const savedLabel = new Intl.DateTimeFormat("es-AR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(savedAt));

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    const requireDecision = (event: Event) => event.preventDefault();
    dialog.addEventListener("cancel", requireDecision);
    if (!dialog.open) dialog.showModal();

    return () => {
      dialog.removeEventListener("cancel", requireDecision);
      if (dialog.open) dialog.close();
    };
  }, []);

  return (
    <dialog
      ref={dialogRef}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="draft-recovery-title"
      aria-describedby="draft-recovery-description"
      className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-lg rounded-2xl border border-sky-200 bg-sky-50 p-5 text-sky-950 shadow-xl backdrop:bg-slate-950/50"
    >
      <div className="flex items-start gap-3">
        <FileClock className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h2 id="draft-recovery-title" className="font-semibold">
            Encontramos un borrador sin guardar
          </h2>
          <p id="draft-recovery-description" className="mt-1 text-sm text-sky-800">
            Guardado en el servidor el {savedLabel}. Para continuar, elija si desea
            recuperarlo o descartarlo.
          </p>
          {sourceChanged && <p role="alert" className="mt-2 text-sm font-medium text-amber-800">El registro cambió desde que guardó este borrador. Revise los datos antes de guardar.</p>}
          <div className="mt-4 flex flex-wrap gap-2">
            <Button type="button" size="sm" onClick={onRestore}>Recuperar borrador</Button>
            <Button type="button" size="sm" variant="secondary" onClick={() => void onDiscard().catch((cause) => setError(cause instanceof Error ? cause.message : "No pudimos descartar el borrador. Intente nuevamente."))}>Descartar</Button>
          </div>
          {error && <p role="alert" className="mt-3 text-sm text-rose-700">{error}</p>}
        </div>
      </div>
    </dialog>
  );
}
