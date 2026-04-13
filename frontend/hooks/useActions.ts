'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { actionsApi } from '@/lib/api/client';
import type { Action, PaginatedResponse, RunStatus } from '@/types';

// ── Normalise raw API response ─────────────────────────────────────────────
function normaliseAction(raw: Action): Action {
  return {
    ...raw,
    // UI-friendly aliases
    dueDate: raw.dueDate ?? formatDueDate(raw.due_date),
    sourceSignalId: raw.sourceSignalId ?? raw.source_signal_id,
    company: raw.company ?? undefined,
  };
}

function formatDueDate(isoDate: string): string {
  try {
    const d = new Date(isoDate);
    return `Due ${d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}`;
  } catch {
    return isoDate;
  }
}

// ── Query keys ─────────────────────────────────────────────────────────────
export const actionKeys = {
  all: ['actions'] as const,
  lists: () => [...actionKeys.all, 'list'] as const,
  list: (params: Record<string, string | number> | undefined) =>
    [...actionKeys.lists(), params] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useActions(params?: Record<string, string | number>) {
  return useQuery({
    queryKey: actionKeys.list(params),
    queryFn: async () => {
      const res = await actionsApi.list(params);
      const body = res.data as PaginatedResponse<Action>;
      return {
        ...body,
        data: body.data.map(normaliseAction),
      };
    },
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useUpdateAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      data,
    }: {
      id: string;
      data: Partial<Pick<Action, 'status' | 'priority' | 'due_date'>>;
    }) => {
      const res = await actionsApi.update(id, data as Record<string, unknown>);
      return normaliseAction(res.data as Action);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: actionKeys.lists() });
    },
  });
}

export function useDraftEmail() {
  return useMutation({
    mutationFn: async (actionId: string) => {
      const res = await actionsApi.draftEmail(actionId);
      return res.data as RunStatus;
    },
  });
}
