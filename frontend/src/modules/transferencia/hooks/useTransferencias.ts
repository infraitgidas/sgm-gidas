import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
    getTransferencias,
    getTransferenciaById,
    createTransferencia,
    updateTransferencia,
    deleteTransferencia,
    addAdoptantesToTransferencia,
    removeAdoptantesFromTransferencia,
    type Transferencia,
    type TransferenciaPayload,
} from "@/modules/transferencia/services/transferenciasServices";
import { getTiposContrato, type TipoContratoItem } from "@/modules/transferencia/services/tiposContratoService";

// ─── Queries ─────────────────────────────────────────────────

export function useTransferencias(activos: "true" | "false" | "all" = "true") {
  const { data = [], isLoading, isFetching, isError, refetch } = useQuery<Transferencia[]>({
    queryKey: ["transferencias", activos],
    queryFn: () => getTransferencias(activos),
    staleTime: 60_000,
  });

  return { list: data, isLoading, isFetching, isError, refetch };
}

export function useTransferencia(id: number | undefined) {
    return useQuery<Transferencia | null>({
        queryKey: ["transferencias", id],
        queryFn: () => getTransferenciaById(id!),
        enabled: !!id,
    });
}

export function useTiposContrato() {
    const { data = [], isLoading, isError, refetch } = useQuery<TipoContratoItem[]>({
        queryKey: ["tipos-contrato"],
        queryFn: getTiposContrato,
        staleTime: 5 * 60_000,
    });

    return { tipos: data, isLoading, isError, refetch };
}

// ─── Mutations ───────────────────────────────────────────────

export function useCreateTransferencia() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (data: TransferenciaPayload) => createTransferencia(data),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["transferencias"] }),
    });
}

export function useUpdateTransferencia() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({ id, data }: { id: number; data: Partial<TransferenciaPayload> }) =>
            updateTransferencia(id, data),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["transferencias"] }),
    });
}

export function useDeleteTransferencia() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: (id: number) => deleteTransferencia(id),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["transferencias"] }),
    });
}

export function useAddAdoptantes() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            transferenciaId,
            adoptantesIds,
        }: {
            transferenciaId: number;
            adoptantesIds: number[];
        }) => addAdoptantesToTransferencia(transferenciaId, adoptantesIds),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["transferencias"] }),
    });
}

export function useRemoveAdoptantes() {
    const qc = useQueryClient();
    return useMutation({
        mutationFn: ({
            transferenciaId,
            adoptantesIds,
        }: {
            transferenciaId: number;
            adoptantesIds: number[];
        }) => removeAdoptantesFromTransferencia(transferenciaId, adoptantesIds),
        onSuccess: () => qc.invalidateQueries({ queryKey: ["transferencias"] }),
    });
}
