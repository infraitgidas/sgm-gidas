import { type ReactNode, useEffect, useId, useRef, useState } from "react";
import Button from "@/components/Button";
import { getErrorMessage } from "@/lib/httpError";

type Props = {
  open: boolean;
  title: string;
  message?: string;
  items?: string[];
  children?: ReactNode;
  confirmText?: string;
  cancelText?: string;
  confirmDisabled?: boolean;
  loading?: boolean;
  loadingText?: string;
  onCancel: () => void;
  onConfirm: () => unknown;
};

export default function ConfirmDialog({
  open,
  title,
  message,
  items = [],
  children,
  confirmText = "Aceptar",
  cancelText = "Cancelar",
  confirmDisabled = false,
  loading = false,
  loadingText = "Procesando...",
  onCancel,
  onConfirm,
}: Props) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const inFlight = useRef(false);
  const dialogRef = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const messageId = useId();
  const busy = loading || pending;
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!open || !dialog) return;
    const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    dialog.showModal();
    const firstControl = dialog.querySelector<HTMLElement>("input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])");
    firstControl?.focus();
    return () => {
      if (dialog.open) dialog.close();
      if (opener?.isConnected) opener.focus();
    };
  }, [open]);
  useEffect(() => {
    if (open) setError("");
  }, [open]);
  const cancel = () => {
    if (inFlight.current || loading) return;
    setError("");
    onCancel();
  };
  const confirm = async () => {
    if (inFlight.current || loading || confirmDisabled) return;
    inFlight.current = true;
    setError("");
    try {
      const result = onConfirm();
      if (result && typeof (result as PromiseLike<unknown>).then === "function") {
        setPending(true);
        await result;
      }
    } catch (cause) {
      setError(getErrorMessage(cause, "Lo sentimos, no pudimos completar la operación. Intente nuevamente."));
    } finally {
      inFlight.current = false;
      setPending(false);
    }
  };
  if (!open) return null;

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={titleId}
      aria-describedby={message ? messageId : undefined}
      onCancel={(event) => { event.preventDefault(); cancel(); }}
      onClick={(event) => {
        if (event.target !== event.currentTarget) return;
        const rect = event.currentTarget.getBoundingClientRect();
        if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) cancel();
      }}
      className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-lg backdrop:bg-black/30 backdrop:backdrop-blur-sm"
    >
        <h3 id={titleId} className="mb-2 text-lg font-semibold">{title}</h3>

        {message && (
          <p id={messageId} className="mb-3 text-sm text-slate-600">
            {message}
          </p>
        )}

        {items.length > 0 && (
          <ul className="mb-4 max-h-40 overflow-y-auto rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700">
            {items.map((name) => (
              <li key={name} className="py-0.5">
                • {name}
              </li>
            ))}
          </ul>
        )}

        {children && <fieldset disabled={busy} className="mb-4">{children}</fieldset>}
        {error && <p role="alert" className="mb-4 text-sm text-rose-600">{error}</p>}

        <div className="flex justify-between">
          <Button
            variant="secondary"
            size="sm"
            className="px-3 py-1 text-xs"
            onClick={cancel}
            disabled={busy}
          >
            {cancelText}
          </Button>

          <Button
            size="sm"
            className="px-3 py-1 text-xs"
            onClick={confirm}
            disabled={confirmDisabled}
            loading={busy}
            loadingText={loadingText}
          >
            {confirmText}
          </Button>
        </div>
    </dialog>
  );
}
