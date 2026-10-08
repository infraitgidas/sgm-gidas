import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    getAdoptantes,
    getAdoptanteById,
    getHistorialAdoptanteById,
    createAdoptante,
    updateAdoptante,
    deleteAdoptante,
    type Adoptante,
    type AdoptantePayload,
    type HistorialAdoptanteItem,
} from "@/modules/transferencia/services/adoptantesServices";

// ─── Queries ─────────────────────────────────────────────────

export function useAdoptantes() {
    const { data = [], isLoading, isError, refetch } = useQuery<Adoptante[]>({
        queryKey: ["adoptantes"],
        queryFn: getAdoptantes,
        staleTime: 60_000,
    });

    return { list: data, isLoading, isError, refetch };
}

export function useAdoptante(id: number | undefined) {
    return useQuery<Adoptante | null>({
        queryKey: ["adoptantes", id],
        queryFn: () => getAdoptanteById(id!),
        enabled: !!id,
    });
}

export function useAdoptanteHistorial(id: number | undefined) {
    return useQuery<HistorialAdoptanteItem[]>({
        queryKey: ["adoptantes", id, "historial"],
        queryFn: () => getHistorialAdoptanteById(id!),
        enabled: id !== undefined && id > 0,
        refetchOnMount: "always",
    });
}

// ─── Mutations ───────────────────────────────────────────────

export function useCreateAdoptante() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (data: AdoptantePayload) => createAdoptante(data),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["adoptantes"] }),
    });
}

export function useUpdateAdoptante() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: number; data: Partial<AdoptantePayload> }) =>
            updateAdoptante(id, data),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["adoptantes"] }),
    });
}

export function useDeleteAdoptante() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (id: number) => deleteAdoptante(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["adoptantes"] }),
    });
}
