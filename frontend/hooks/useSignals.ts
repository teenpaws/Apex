'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { signalsApi } from '@/lib/api/client';
import type { Signal, PaginatedResponse, RunStatus } from '@/types';

// ── Normalise raw API response ─────────────────────────────────────────────
// The API returns pure snake_case. We enrich the object with the camelCase
// aliases the Dashboard and other components read from `@/lib/mock` so the
// pages need zero data-mapping logic of their own.
function normaliseSignal(raw: Signal): Signal {
  return {
    ...raw,
    // UI-friendly aliases
    company: raw.company ?? undefined,
    date: raw.date ?? formatRelativeDate(raw.signal_date),
    linkedOpportunityIds: raw.linkedOpportunityIds ?? [],
  };
}

function formatRelativeDate(isoDate: string): string {
  try {
    const diff = Date.now() - new Date(isoDate).getTime();
    const hours = Math.floor(diff / 3_600_000);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days === 1) return '1d ago';
    if (days < 7) return `${days}d ago`;
    return new Date(isoDate).toLocaleDateString('en-GB', {
      day: 'numeric',
      month: 'short',
    });
  } catch {
    return isoDate;
  }
}

// ── Query keys ─────────────────────────────────────────────────────────────
export const signalKeys = {
  all: ['signals'] as const,
  lists: () => [...signalKeys.all, 'list'] as const,
  list: (params: Record<string, string | number> | undefined) =>
    [...signalKeys.lists(), params] as const,
  detail: (id: string) => [...signalKeys.all, 'detail', id] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useSignals(params?: Record<string, string | number>) {
  return useQuery({
    queryKey: signalKeys.list(params),
    queryFn: async () => {
      const res = await signalsApi.list(params);
      const body = res.data as PaginatedResponse<Signal>;
      return {
        ...body,
        data: body.data.map(normaliseSignal),
      };
    },
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useSignal(id: string) {
  return useQuery({
    queryKey: signalKeys.detail(id),
    queryFn: async () => {
      const res = await signalsApi.get(id);
      return normaliseSignal(res.data as Signal);
    },
    enabled: Boolean(id),
  });
}

export function useIngestSignals() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const res = await signalsApi.ingest();
      return res.data as RunStatus;
    },
    onSuccess: () => {
      // Invalidate all signal lists so they re-fetch after ingestion
      queryClient.invalidateQueries({ queryKey: signalKeys.lists() });
    },
  });
}
