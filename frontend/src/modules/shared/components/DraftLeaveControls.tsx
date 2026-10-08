import { useState } from "react";
import Button from "@/components/Button";
import ConfirmDialog from "@/components/ConfirmDialog";

type Props = {
  blocker: { state: string; reset?: () => void };
  saveStatus: "idle" | "saving" | "saved" | "error";
  keepAndLeave: () => Promise<boolean>;
  discardAndLeave: () => Promise<boolean>;
};

export default function DraftLeaveControls({ blocker, saveStatus, keepAndLeave, discardAndLeave }: Props) {
  const [discarding, setDiscarding] = useState(false);
  const [discardError, setDiscardError] = useState(false);

  const discard = async () => {
    setDiscarding(true);
    try {
      setDiscardError(!await discardAndLeave());
    } finally {
      setDiscarding(false);
    }
  };

  return (
    <>
      <ConfirmDialog
        open={blocker.state === "blocked"}
        title="¿Qué desea hacer con este borrador?"
        message="Puede guardarlo para continuar más tarde o descartarlo antes de volver."
        confirmText="Guardar borrador y volver"
        cancelText="Seguir editando"
        loading={discarding}
        onCancel={() => blocker.reset?.()}
        onConfirm={async () => {
          if (!await keepAndLeave()) throw new Error("No pudimos guardar el borrador. Intente nuevamente.");
        }}
      >
        <Button type="button" variant="secondary" size="sm" onClick={() => void discard()}>
          Descartar y volver
        </Button>
        {discardError && <p role="alert" className="mt-2 text-sm text-rose-700">No pudimos descartar el borrador. Intente nuevamente.</p>}
      </ConfirmDialog>
      {saveStatus !== "idle" && (
        <p role="status" className="mt-2 text-sm text-slate-600">
          {saveStatus === "saving" ? "Guardando borrador..." :
            saveStatus === "saved" ? "Borrador guardado." :
              "No pudimos guardar el borrador. Intente nuevamente."}
        </p>
      )}
    </>
  );
}
