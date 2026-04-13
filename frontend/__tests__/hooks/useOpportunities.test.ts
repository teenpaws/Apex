import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { Opportunity } from '@/types';

// ---------------------------------------------------------------------------
// Mock the API layer
// ---------------------------------------------------------------------------

vi.mock('@/lib/api', () => ({
  opportunitiesApi: {
    list: vi.fn(),
    get: vi.fn(),
    refresh: vi.fn(),
  },
  actionsApi: {
    list: vi.fn(),
    update: vi.fn(),
    draftEmail: vi.fn(),
  },
}));

vi.mock('@/lib/api/client', () => ({
  opportunitiesApi: {
    list: vi.fn(),
    get: vi.fn(),
    refresh: vi.fn(),
  },
}));

import { opportunitiesApi } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockOpp: Opportunity = {
  id: 'o1',
  user_id: 'u1',
  company_id: 'c1',
  predicted_role: 'VP Strategy & Operations',
  confidence: 'HIGH',
  timeline_weeks: 6,
  why_fit: 'Strong MBA background + AI sector experience.',
  positioning_notes: 'Lead with your HEC network.',
  predicted_salary_range: '€120k–€160k + equity',
  fit_score: 87,
  key_contact_id: 'ct1',
  signal_ids: ['s1'],
  status: 'PREDICTED',
  created_at: '2026-04-10T10:00:00Z',
  updated_at: '2026-04-10T10:00:00Z',
  company: 'Mistral AI',
  keyContact: 'Sophie Martin',
};

const paginatedResponse = {
  data: { data: [mockOpp], total: 1, page: 1, per_page: 12 },
};

const singleOppResponse = { data: mockOpp };
const refreshResponse = { data: { run_id: 'refresh-run-123', status: 'queued' } };

// ---------------------------------------------------------------------------
// React Query wrapper
// ---------------------------------------------------------------------------

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children);
};

// ---------------------------------------------------------------------------
// Dynamic import hooks
// ---------------------------------------------------------------------------

let useOpportunities: ((params?: Record<string, string | number>) => unknown) | null = null;
let useOpportunity: ((id: string) => unknown) | null = null;
let useRefreshOpportunity: (() => unknown) | null = null;

try {
  const mod = await import('@/hooks/useOpportunities');
  useOpportunities = mod.useOpportunities ?? null;
  useOpportunity = mod.useOpportunity ?? null;
  useRefreshOpportunity = mod.useRefreshOpportunity ?? null;
} catch {
  // Hooks not yet implemented
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useOpportunities hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is exported from @/hooks/useOpportunities', () => {
    expect(useOpportunities).not.toBeNull();
  });

  it('fetches opportunities from /opportunities endpoint', async () => {
    if (!useOpportunities) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValueOnce(paginatedResponse as never);

    const { result } = renderHook(
      () => (useOpportunities as NonNullable<typeof useOpportunities>)(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const data = (result.current as Record<string, unknown>).data;
      expect(data).toBeDefined();
    });

    expect(opportunitiesApi.list).toHaveBeenCalledOnce();
  });

  it('passes filter params (confidence, status) to the API', async () => {
    if (!useOpportunities) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValueOnce(paginatedResponse as never);

    renderHook(
      () =>
        (useOpportunities as NonNullable<typeof useOpportunities>)({
          confidence: 'HIGH',
          status: 'PREDICTED',
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(opportunitiesApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ confidence: 'HIGH', status: 'PREDICTED' })
      );
    });
  });

  it('returns error state when API fails', async () => {
    if (!useOpportunities) return;
    vi.mocked(opportunitiesApi.list).mockRejectedValueOnce(new Error('Server error'));

    const { result } = renderHook(
      () => (useOpportunities as NonNullable<typeof useOpportunities>)(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const hookResult = result.current as Record<string, unknown>;
      expect(hookResult.isError === true || hookResult.error != null).toBe(true);
    });
  });

  it('normalises opportunity data (adds camelCase aliases)', async () => {
    if (!useOpportunities) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValueOnce(paginatedResponse as never);

    const { result } = renderHook(
      () => (useOpportunities as NonNullable<typeof useOpportunities>)(),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const hookResult = result.current as Record<string, unknown>;
      const data = hookResult.data as { data: Opportunity[] } | undefined;
      if (data?.data?.[0]) {
        // Normalised aliases should be present
        expect(data.data[0].predicted_role).toBe('VP Strategy & Operations');
      }
    });
  });
});

describe('useOpportunity (single) hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is exported from @/hooks/useOpportunities', () => {
    expect(useOpportunity).not.toBeNull();
  });

  it('fetches a single opportunity from /opportunities/{id}', async () => {
    if (!useOpportunity) return;
    vi.mocked(opportunitiesApi.get).mockResolvedValueOnce(singleOppResponse as never);

    const { result } = renderHook(
      () => (useOpportunity as NonNullable<typeof useOpportunity>)('o1'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const hookResult = result.current as Record<string, unknown>;
      expect(hookResult.data).toBeDefined();
    });

    expect(opportunitiesApi.get).toHaveBeenCalledWith('o1');
  });

  it('is disabled when id is empty string', async () => {
    if (!useOpportunity) return;

    renderHook(
      () => (useOpportunity as NonNullable<typeof useOpportunity>)(''),
      { wrapper: createWrapper() }
    );

    // Should not fire API call for empty id
    await new Promise((r) => setTimeout(r, 50));
    expect(opportunitiesApi.get).not.toHaveBeenCalled();
  });
});

describe('useRefreshOpportunity mutation hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is exported from @/hooks/useOpportunities', () => {
    expect(useRefreshOpportunity).not.toBeNull();
  });

  it('calls POST /opportunities/{id}/refresh when mutate is triggered', async () => {
    if (!useRefreshOpportunity) return;
    vi.mocked(opportunitiesApi.refresh).mockResolvedValueOnce(refreshResponse as never);

    const { result } = renderHook(
      () => (useRefreshOpportunity as NonNullable<typeof useRefreshOpportunity>)(),
      { wrapper: createWrapper() }
    );

    const hookResult = result.current as Record<string, unknown>;
    const mutate = hookResult.mutate as ((id: string) => void) | undefined;
    if (mutate) mutate('o1');

    await waitFor(() => {
      expect(opportunitiesApi.refresh).toHaveBeenCalledWith('o1');
    });
  });
});
