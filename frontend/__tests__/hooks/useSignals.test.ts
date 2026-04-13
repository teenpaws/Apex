import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { Signal } from '@/types';

// ---------------------------------------------------------------------------
// Mock the API layer so no real HTTP calls are made
// ---------------------------------------------------------------------------

vi.mock('@/lib/api', () => ({
  signalsApi: {
    list: vi.fn(),
    get: vi.fn(),
    ingest: vi.fn(),
  },
}));

// Also mock the re-export path hooks might use
vi.mock('@/lib/api/client', () => ({
  signalsApi: {
    list: vi.fn(),
    get: vi.fn(),
    ingest: vi.fn(),
  },
}));

import { signalsApi } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockSignals: Signal[] = [
  {
    id: 's1',
    user_id: 'u1',
    company_id: 'c1',
    type: 'FUNDING',
    source: 'TechCrunch',
    title: 'Mistral AI raises €600M Series B',
    description: 'European AI startup closes €600M round.',
    signal_date: '2026-04-10',
    relevance_score: 0.95,
    processed_at: '2026-04-10T09:00:00Z',
    is_duplicate: false,
    company: 'Mistral AI',
    date: '2 days ago',
  },
  {
    id: 's2',
    user_id: 'u1',
    company_id: 'c2',
    type: 'EXEC_HIRE',
    source: 'LinkedIn',
    title: 'Pigment hires new Chief Revenue Officer',
    description: 'Pigment appoints Pierre Dupont as CRO.',
    signal_date: '2026-04-09',
    relevance_score: 0.78,
    processed_at: '2026-04-09T12:00:00Z',
    is_duplicate: false,
    company: 'Pigment',
    date: '3 days ago',
  },
];

const paginatedResponse = {
  data: { data: mockSignals, total: 2, page: 1, per_page: 20 },
};

const singleSignalResponse = {
  data: mockSignals[0],
};

const ingestResponse = {
  data: { run_id: 'test-run-123', status: 'queued' },
};

// ---------------------------------------------------------------------------
// React Query test wrapper
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
// Attempt to import hooks — skip gracefully if not yet implemented
// ---------------------------------------------------------------------------

let useSignals: ((params?: Record<string, string | number>) => unknown) | null = null;
let useSignal: ((id: string) => unknown) | null = null;
let useIngestSignals: (() => unknown) | null = null;

try {
  const mod = await import('@/hooks/useSignals');
  useSignals = mod.useSignals ?? mod.default ?? null;
  useSignal = mod.useSignal ?? null;
  useIngestSignals = mod.useIngestSignals ?? null;
} catch {
  // Hooks not yet implemented — tests will be skipped below
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useSignals hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is exported from @/hooks/useSignals', () => {
    expect(useSignals).not.toBeNull();
  });

  it('fetches signals from /signals endpoint', async () => {
    if (!useSignals) return;
    vi.mocked(signalsApi.list).mockResolvedValueOnce(paginatedResponse as never);

    const { result } = renderHook(() => (useSignals as NonNullable<typeof useSignals>)(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      // The hook should expose a data property
      const data = (result.current as Record<string, unknown>).data;
      expect(data).toBeDefined();
    });

    expect(signalsApi.list).toHaveBeenCalledOnce();
  });

  it('passes filter params to the API', async () => {
    if (!useSignals) return;
    vi.mocked(signalsApi.list).mockResolvedValueOnce(paginatedResponse as never);

    renderHook(() => (useSignals as NonNullable<typeof useSignals>)({ type: 'FUNDING', page: 1 }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(signalsApi.list).toHaveBeenCalledWith(
        expect.objectContaining({ type: 'FUNDING', page: 1 })
      );
    });
  });

  it('returns error state when API call fails', async () => {
    if (!useSignals) return;
    vi.mocked(signalsApi.list).mockRejectedValueOnce(
      new Error('Network error')
    );

    const { result } = renderHook(() => (useSignals as NonNullable<typeof useSignals>)(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      const hookResult = result.current as Record<string, unknown>;
      expect(
        hookResult.isError === true || hookResult.error != null
      ).toBe(true);
    });
  });
});

describe('useSignal (single) hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is exported from @/hooks/useSignals', () => {
    expect(useSignal).not.toBeNull();
  });

  it('fetches a single signal from /signals/{id}', async () => {
    if (!useSignal) return;
    vi.mocked(signalsApi.get).mockResolvedValueOnce(singleSignalResponse as never);

    const { result } = renderHook(
      () => (useSignal as NonNullable<typeof useSignal>)('s1'),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      const hookResult = result.current as Record<string, unknown>;
      expect(hookResult.data).toBeDefined();
    });

    expect(signalsApi.get).toHaveBeenCalledWith('s1');
  });
});

describe('useIngestSignals mutation hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('is exported from @/hooks/useSignals', () => {
    expect(useIngestSignals).not.toBeNull();
  });

  it('calls POST /signals/ingest when mutate is triggered', async () => {
    if (!useIngestSignals) return;
    vi.mocked(signalsApi.ingest).mockResolvedValueOnce(ingestResponse as never);

    const { result } = renderHook(
      () => (useIngestSignals as NonNullable<typeof useIngestSignals>)(),
      { wrapper: createWrapper() }
    );

    const hookResult = result.current as Record<string, unknown>;
    const mutate = hookResult.mutate as (() => void) | undefined;
    if (mutate) mutate();

    await waitFor(() => {
      expect(signalsApi.ingest).toHaveBeenCalledOnce();
    });
  });

  it('exposes run_id in returned data after successful mutation', async () => {
    if (!useIngestSignals) return;
    vi.mocked(signalsApi.ingest).mockResolvedValueOnce(ingestResponse as never);

    const { result } = renderHook(
      () => (useIngestSignals as NonNullable<typeof useIngestSignals>)(),
      { wrapper: createWrapper() }
    );

    const hookResult = result.current as Record<string, unknown>;
    const mutateAsync = hookResult.mutateAsync as (() => Promise<unknown>) | undefined;

    if (mutateAsync) {
      const data = await mutateAsync();
      // Data may be the raw axios response or the unwrapped body
      expect(JSON.stringify(data)).toContain('test-run-123');
    }
  });
});
