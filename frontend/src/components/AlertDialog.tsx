import { useEffect, useId, useRef } from "react";
import Button from "@/components/Button";

type Props = {
    open: boolean;
    title: string;
    message: string;
    onClose: () => void;
};

export default function AlertDialog({
    open,
    title,
    message,
    onClose,
}: Props) {
    const dialogRef = useRef<HTMLDialogElement>(null);
    const titleId = useId();
    const messageId = useId();

    useEffect(() => {
        const dialog = dialogRef.current;
        if (!open || !dialog) return;
        const opener = document.activeElement instanceof HTMLElement ? document.activeElement : null;
        dialog.showModal();
        dialog.querySelector<HTMLElement>("button")?.focus();
        return () => {
            if (dialog.open) dialog.close();
            if (opener?.isConnected) opener.focus();
        };
    }, [open]);

    if (!open) return null;

    return (
        <dialog
            ref={dialogRef}
            aria-labelledby={titleId}
            aria-describedby={messageId}
            onCancel={(event) => { event.preventDefault(); onClose(); }}
            onClick={(event) => {
                if (event.target !== event.currentTarget) return;
                const rect = event.currentTarget.getBoundingClientRect();
                if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) onClose();
            }}
            className="fixed inset-0 m-auto w-[calc(100%-2rem)] max-w-md rounded-2xl border border-slate-200 bg-white/90 p-6 shadow-lg backdrop:bg-black/30 backdrop:backdrop-blur-sm"
        >
                <h3 id={titleId} className="text-lg font-semibold mb-2">
                    {title}
                </h3>

                <p id={messageId} className="text-sm text-slate-600 mb-5">
                    {message}
                </p>

                <div className="flex justify-end">
                    <Button
                        size="sm"
                        className="px-3 py-1 text-xs"
                        onClick={onClose}
                    >
                        Entendido
                    </Button>
                </div>
        </dialog>
    );
}
