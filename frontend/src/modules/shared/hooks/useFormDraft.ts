import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useBlocker } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  deleteFormDraft,
  getFormDraft,
  putFormDraft,
  type FormDraft,
} from "@/modules/shared/services/formDraftService";

type Params<T> = {
  userId: number | undefined;
  module: string;
  recordId?: string | number;
  value: T;
  ready?: boolean;
  autosave?: boolean;
  hasContent: (value: T) => boolean;
  onRestore: (value: T) => void;
};

function fingerprint(value: string) {
  let hash = 2166136261;
  for (let index = 0; index < value.length; index += 1) {
    hash = Math.imul(hash ^ value.charCodeAt(index), 16777619);
  }
  return (hash >>> 0).toString(16);
}

export function useFormDraft<T>({ userId, module, recordId, value, ready = true, autosave = false, hasContent, onRestore }: Params<T>) {
  const queryClient = useQueryClient();
  const [availableDraft, setAvailableDraft] = useState<FormDraft<T> | null>(null);
  const [sourceChanged, setSourceChanged] = useState(false);
  const [canSave, setCanSave] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [manualBlocked, setManualBlocked] = useState(false);
  const baseline = useRef("");
  const baseFingerprint = useRef("");
  const valueRef = useRef(value);
  const hasContentRef = useRef(hasContent);
  const restoreRef = useRef(onRestore);
  const canSaveRef = useRef(false);
  const disabledRef = useRef(false);
  const queue = useRef<Promise<unknown>>(Promise.resolve());
  const pendingLeave = useRef<(() => void) | null>(null);
  const initializedKey = useRef<string | null>(null);
  const readyInitializedKey = useRef<string | null>(null);
  const key = useMemo(() => userId ? `${userId}:${module}:${recordId ?? "new"}` : null, [userId, module, recordId]);
  const serializedValue = JSON.stringify(value);
  valueRef.current = value;
  hasContentRef.current = hasContent;
  restoreRef.current = onRestore;

  useEffect(() => {
    let active = true;
    if (initializedKey.current !== key) {
      initializedKey.current = key;
      setAvailableDraft(null);
      setSourceChanged(false);
      setCanSave(false);
      canSaveRef.current = false;
      disabledRef.current = false;
      baseline.current = JSON.stringify(valueRef.current);
      readyInitializedKey.current = null;
    }
    if (!key || !ready) return;
    const timer = window.setTimeout(() => {
      if (!active) return;
      if (readyInitializedKey.current !== key) {
        readyInitializedKey.current = key;
        baseline.current = JSON.stringify(valueRef.current);
        baseFingerprint.current = fingerprint(baseline.current);
      }
      void getFormDraft<T>(module, recordId).then((draft) => {
      if (!active) return;
      setAvailableDraft(draft);
      setSourceChanged(Boolean(recordId && draft?.base_fingerprint && draft.base_fingerprint !== baseFingerprint.current));
      setCanSave(!draft);
      canSaveRef.current = !draft;
      }).catch(() => {
      if (active) {
        setSaveStatus("error");
        window.setTimeout(() => { if (active) setLoadAttempt((attempt) => attempt + 1); }, 3000);
      }
      });
    }, 0);
    return () => { active = false; window.clearTimeout(timer); };
  }, [key, ready, module, recordId, loadAttempt]);

  const saveNow = useCallback(async (force = false) => {
    if (!userId || !ready || !canSaveRef.current || disabledRef.current) return false;
    const currentValue = valueRef.current;
    if (!hasContentRef.current(currentValue)) return false;
    if (!force && JSON.stringify(currentValue) === baseline.current) return true;
    setSaveStatus("saving");
    const operation = queue.current.catch(() => undefined).then(() =>
      putFormDraft(module, recordId, currentValue, baseFingerprint.current)
    );
    queue.current = operation;
    try {
      const summary = await operation;
      baseline.current = JSON.stringify(currentValue);
      setSaveStatus("saved");
      queryClient.setQueryData<Array<typeof summary>>(["form-drafts", userId], (previous) => [
        summary,
        ...(previous ?? []).filter((draft) => draft.module !== summary.module || draft.record_key !== summary.record_key),
      ]);
      void queryClient.invalidateQueries({ queryKey: ["form-drafts"] });
      return true;
    } catch {
      setSaveStatus("error");
      return false;
    }
  }, [module, queryClient, ready, recordId, userId]);

  useEffect(() => {
    if (!ready || disabledRef.current || serializedValue === baseline.current) return;
    if (!canSave || !autosave) return;
    const timer = window.setTimeout(() => { void saveNow(); }, 900);
    return () => window.clearTimeout(timer);
  }, [autosave, canSave, ready, saveNow, serializedValue]);

  const hasUnsavedChanges = useCallback(() =>
    ready && readyInitializedKey.current === key &&
    JSON.stringify(valueRef.current) !== baseline.current && !disabledRef.current,
  [key, ready]);

  const blocker = useBlocker(hasUnsavedChanges);

  const requestLeave = useCallback((action: () => void) => {
    if (hasUnsavedChanges()) {
      pendingLeave.current = action;
      setManualBlocked(true);
      return;
    }
    action();
  }, [hasUnsavedChanges]);

  const resetLeave = useCallback(() => {
    pendingLeave.current = null;
    setManualBlocked(false);
    if (blocker.state === "blocked") blocker.reset();
  }, [blocker]);

  const restoreDraft = useCallback(() => {
    if (!availableDraft) return;
    restoreRef.current(availableDraft.data);
    baseline.current = JSON.stringify(availableDraft.data);
    setAvailableDraft(null);
    setCanSave(true);
    canSaveRef.current = true;
    setSaveStatus("saved");
  }, [availableDraft]);

  const discardDraft = useCallback(async () => {
    disabledRef.current = true;
    const operation = queue.current.catch(() => undefined).then(() => deleteFormDraft(module, recordId));
    queue.current = operation;
    try {
      await operation;
      setAvailableDraft(null);
      setCanSave(true);
      canSaveRef.current = true;
      disabledRef.current = false;
      baseline.current = JSON.stringify(valueRef.current);
      queryClient.setQueryData<Array<{ module: string; record_key: string }>>(["form-drafts", userId], (previous) =>
        previous?.filter((draft) => draft.module !== module || draft.record_key !== String(recordId ?? "new"))
      );
      void queryClient.invalidateQueries({ queryKey: ["form-drafts"] });
    } catch {
      disabledRef.current = false;
      setSaveStatus("error");
      throw new Error("No pudimos descartar el borrador. Intente nuevamente.");
    }
  }, [module, queryClient, recordId, userId]);

  const clearDraft = useCallback(() => {
    disabledRef.current = true;
    setAvailableDraft(null);
    setCanSave(false);
    queue.current = queue.current.catch(() => undefined).then(() => deleteFormDraft(module, recordId));
    void queue.current.then(() => {
      queryClient.setQueryData<Array<{ module: string; record_key: string }>>(["form-drafts", userId], (previous) =>
        previous?.filter((draft) => draft.module !== module || draft.record_key !== String(recordId ?? "new"))
      );
      return queryClient.invalidateQueries({ queryKey: ["form-drafts"] });
    }).catch(() => setSaveStatus("error"));
  }, [module, queryClient, recordId, userId]);

  const keepAndLeave = useCallback(async () => {
    const saved = saveStatus === "saved" && serializedValue === baseline.current ? true : await saveNow(true);
    if (saved && manualBlocked) {
      disabledRef.current = true;
      setManualBlocked(false);
      const action = pendingLeave.current;
      pendingLeave.current = null;
      action?.();
    } else if (saved && blocker.state === "blocked") {
      disabledRef.current = true;
      blocker.proceed();
    }
    return saved;
  }, [blocker, manualBlocked, saveNow, saveStatus, serializedValue]);

  const discardAndLeave = useCallback(async () => {
    disabledRef.current = true;
    try {
      await queue.current.catch(() => undefined);
      await deleteFormDraft(module, recordId);
      queryClient.setQueryData<Array<{ module: string; record_key: string }>>(["form-drafts", userId], (previous) =>
        previous?.filter((draft) => draft.module !== module || draft.record_key !== String(recordId ?? "new"))
      );
      void queryClient.invalidateQueries({ queryKey: ["form-drafts"] });
      if (manualBlocked) {
        setManualBlocked(false);
        const action = pendingLeave.current;
        pendingLeave.current = null;
        action?.();
      } else if (blocker.state === "blocked") blocker.proceed();
      return true;
    } catch {
      disabledRef.current = false;
      setSaveStatus("error");
      return false;
    }
  }, [blocker, manualBlocked, module, queryClient, recordId, userId]);

  const leaveBlocker = manualBlocked ? { state: "blocked", reset: resetLeave } : blocker;
  return { availableDraft, sourceChanged, restoreDraft, discardDraft, clearDraft, saveStatus, blocker: leaveBlocker, requestLeave, keepAndLeave, discardAndLeave };
}
