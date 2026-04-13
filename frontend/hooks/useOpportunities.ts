'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { opportunitiesApi, actionsApi } from '@/lib/api/client';
import type { Opportunity, PaginatedResponse, RunStatus } from '@/types';

// ── Normalise raw API response ─────────────────────────────────────────────
// Adds camelCase UI-aliases so components can use opp.role, opp.whyFit, etc.
// without embedding mapping logic in JSX.
function normaliseOpportunity(raw: Opportunity): Opportunity {
  return {
    ...raw,
    // UI-friendly aliases (dashboard reads these)
    role: raw.role ?? raw.predicted_role,
    timeline:
      raw.timeline ??
      (raw.timeline_weeks != null ? `${raw.timeline_weeks}w` : undefined),
    whyFit: raw.whyFit ?? raw.why_fit,
    predictedSalary: raw.predictedSalary ?? raw.predicted_salary_range,
    // company & keyContact come from join in API; keep if present
    company: raw.company ?? undefined,
    keyContact: raw.keyContact ?? undefined,
  };
}

// ── Query keys ─────────────────────────────────────────────────────────────
export const opportunityKeys = {
  all: ['opportunities'] as const,
  lists: () => [...opportunityKeys.all, 'list'] as const,
  list: (params: Record<string, string | number> | undefined) =>
    [...opportunityKeys.lists(), params] as const,
  detail: (id: string) => [...opportunityKeys.all, 'detail', id] as const,
};

// ── Hooks ──────────────────────────────────────────────────────────────────

export function useOpportunities(params?: Record<string, string | number>) {
  return useQuery({
    queryKey: opportunityKeys.list(params),
    queryFn: async () => {
      const res = await opportunitiesApi.list(params);
      const body = res.data as PaginatedResponse<Opportunity>;
      return {
        ...body,
        data: body.data.map(normaliseOpportunity),
      };
    },
    refetchInterval: 5 * 60 * 1000,
  });
}

export function useOpportunity(id: string) {
  return useQuery({
    queryKey: opportunityKeys.detail(id),
    queryFn: async () => {
      const res = await opportunitiesApi.get(id);
      return normaliseOpportunity(res.data as Opportunity);
    },
    enabled: Boolean(id),
  });
}

export function useRefreshOpportunity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const res = await opportunitiesApi.refresh(id);
      return res.data as RunStatus;
    },
    onSuccess: (_data, id) => {
      queryClient.invalidateQueries({ queryKey: opportunityKeys.detail(id) });
      queryClient.invalidateQueries({ queryKey: opportunityKeys.lists() });
    },
  });
}

// ── Create action from opportunity ─────────────────────────────────────────
export interface CreateActionPayload {
  opportunity_id: string;
  type?: 'OUTREACH' | 'FOLLOW_UP' | 'RESEARCH' | 'CALL';
  title?: string;
}

export function useCreateAction() {
  return useMutation({
    mutationFn: async (payload: CreateActionPayload) => {
      const res = await actionsApi.draftEmail(payload.opportunity_id);
      return res.data as RunStatus;
    },
  });
}
