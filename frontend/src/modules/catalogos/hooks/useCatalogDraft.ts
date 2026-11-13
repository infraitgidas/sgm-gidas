import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getFormDraft, putFormDraft, deleteFormDraft, type FormDraft } from "@/modules/shared/services/formDraftService";

export type CatalogDraft = {
  endpoint: string;
  mode: "create" | "edit";
  editId: number | null;
  name: string;
  description: string;
  fkId: number | "";
};

export function useCatalogDraft(userId: number | undefined, enabled: boolean) {
  const queryClient = useQueryClient();
  const [available, setAvailable] = useState<FormDraft<CatalogDraft> | null>(null);
  const [value, setValue] = useState<CatalogDraft | null>(null);
  const [ready, setReady] = useState(false);
  const [status, setStatus] = useState("");
  const [attempt, setAttempt] = useState(0);
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const generation = useRef(0);
  const serialized = JSON.stringify(value);

  useEffect(() => {
    if (!userId || !enabled) return;
    let active = true;
    setReady(false);
    void getFormDraft<CatalogDraft>("catalogos").then(draft => {
      if (!active) return;
      setAvailable(draft);
      setReady(!draft);
      setStatus("");
    }).catch(() => { if (active) setStatus("No pudimos recuperar el borrador. Intente nuevamente."); });
    return () => { active = false; generation.current++; };
  }, [userId, enabled, attempt]);

  useEffect(() => {
    if (!ready || !enabled || !value?.name.trim()) return;
    const version = generation.current;
    const timer = window.setTimeout(() => {
      setStatus("Guardando borrador...");
      queue.current = queue.current.catch(() => undefined).then(async () => {
        if (version !== generation.current) return;
        await putFormDraft("catalogos", undefined, value, "");
        if (version === generation.current) setStatus("Borrador guardado.");
        void queryClient.invalidateQueries({ queryKey: ["form-drafts", userId] });
      }).catch(() => { if (version === generation.current) setStatus("No pudimos guardar el borrador. Intente nuevamente."); });
    }, 500);
    return () => window.clearTimeout(timer);
  }, [serialized, ready, enabled, userId, queryClient]);

  const clear = useCallback(async () => {
    generation.current++;
    await queue.current.catch(() => undefined);
    try { await deleteFormDraft("catalogos"); }
    catch (error) {
      setStatus("No pudimos eliminar el borrador. Intente nuevamente antes de salir.");
      throw error;
    }
    setAvailable(null);
    setValue(null);
    setReady(true);
    setStatus("");
    void queryClient.invalidateQueries({ queryKey: ["form-drafts", userId] });
  }, [queryClient, userId]);

  return { available, status, ready, setValue, clear,
    retry: () => setAttempt(value => value + 1),
    restore: () => { setAvailable(null); setReady(true); },
  };
}
