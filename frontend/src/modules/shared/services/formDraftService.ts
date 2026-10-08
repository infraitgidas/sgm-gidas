import { http } from "@/lib/http";

export type FormDraftSummary = {
  module: string;
  record_key: string;
  label: string;
  display_name?: string;
  path: string;
  saved_at: string;
  expires_at: string;
};

export type FormDraft<T> = FormDraftSummary & { data: T; base_fingerprint?: string };

type StoredDraft<T> = { __draft_meta: { schema: 1; base_fingerprint: string }; fields: T };

type Envelope<T> = { data: T };

function endpoint(module: string, recordId?: string | number) {
  const recordKey = recordId == null ? "new" : String(recordId);
  return `/borradores/${encodeURIComponent(module)}/${encodeURIComponent(recordKey)}`;
}

export async function listFormDrafts(): Promise<FormDraftSummary[]> {
  const result = await http<Envelope<FormDraftSummary[]>>("/borradores");
  return result.data;
}

export async function getFormDraft<T>(module: string, recordId?: string | number): Promise<FormDraft<T> | null> {
  const result = await http<Envelope<FormDraft<StoredDraft<T> | T>> | null>(endpoint(module, recordId), { allowNotFound: true });
  const draft = result?.data;
  if (!draft) return null;
  const stored = draft.data as StoredDraft<T>;
  if (stored && typeof stored === "object" && stored.__draft_meta?.schema === 1) {
    return { ...draft, data: stored.fields, base_fingerprint: stored.__draft_meta.base_fingerprint };
  }
  return draft as FormDraft<T>;
}

export async function putFormDraft<T>(module: string, recordId: string | number | undefined, data: T, baseFingerprint: string): Promise<FormDraftSummary> {
  const result = await http<Envelope<FormDraftSummary>>(endpoint(module, recordId), {
    method: "PUT",
    body: JSON.stringify({ data: { __draft_meta: { schema: 1, base_fingerprint: baseFingerprint }, fields: data } satisfies StoredDraft<T> }),
  });
  return result.data;
}

export async function deleteFormDraft(module: string, recordId?: string | number): Promise<void> {
  await http(endpoint(module, recordId), { method: "DELETE" });
}
