import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './client';

export const queryKeys = {
  health: ['health'] as const,
  metrics: ['metrics'] as const,
  samples: ['samples'] as const,
  history: ['history'] as const,
  historyItem: (id: string) => ['history', id] as const,
};

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: api.health,
    refetchInterval: 10_000,
    retry: 1,
  });
}

export function useMetrics() {
  return useQuery({ queryKey: queryKeys.metrics, queryFn: api.metrics, staleTime: 5 * 60_000 });
}

export function useSamples() {
  return useQuery({ queryKey: queryKeys.samples, queryFn: api.samples, staleTime: Infinity });
}

export function useHistory(enabled = true) {
  return useQuery({ queryKey: queryKeys.history, queryFn: api.history, enabled });
}

export function useHistoryItem(id: string | undefined) {
  return useQuery({
    queryKey: queryKeys.historyItem(id ?? ''),
    queryFn: () => api.historyItem(id!),
    enabled: Boolean(id),
    retry: false,
  });
}

export function useDeleteHistoryItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.deleteHistoryItem,
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.history }),
  });
}

export function useClearHistory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.clearHistory,
    onSuccess: () => qc.invalidateQueries({ queryKey: queryKeys.history }),
  });
}
