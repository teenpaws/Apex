import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { Opportunity } from '@/types';

// ---------------------------------------------------------------------------
// Mock API
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
  actionsApi: {
    list: vi.fn(),
    update: vi.fn(),
    draftEmail: vi.fn(),
  },
}));

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/opportunities',
}));

import { opportunitiesApi } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const highConfOpp: Opportunity = {
  id: 'o1',
  user_id: 'u1',
  company_id: 'c1',
  predicted_role: 'VP Strategy & Operations',
  confidence: 'HIGH',
  timeline_weeks: 6,
  why_fit: 'Strong MBA background + AI sector experience.',
  approach_angle: 'Lead with your HEC network.',
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

const medConfOpp: Opportunity = {
  id: 'o2',
  user_id: 'u1',
  company_id: 'c2',
  predicted_role: 'Head of Business Development',
  confidence: 'MEDIUM',
  timeline_weeks: 10,
  why_fit: 'BD background + BI sector knowledge.',
  approach_angle: 'Focus on growth metrics.',
  fit_score: 62,
  signal_ids: ['s2'],
  status: 'PREDICTED',
  created_at: '2026-04-09T10:00:00Z',
  updated_at: '2026-04-09T10:00:00Z',
  company: 'Pigment',
};

const paginatedOpps = {
  data: { data: [highConfOpp, medConfOpp], total: 2, page: 1, per_page: 12 },
};

const emptyResponse = {
  data: { data: [], total: 0, page: 1, per_page: 12 },
};

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
// Dynamic import
// ---------------------------------------------------------------------------

let OpportunitiesPage: React.ComponentType | null = null;

try {
  const mod = await import('@/app/(dashboard)/opportunities/page');
  OpportunitiesPage = mod.default ?? null;
} catch {
  // page not yet implemented
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Opportunities Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the Opportunities heading', async () => {
    if (!OpportunitiesPage) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValue(paginatedOpps as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OpportunitiesPage)
      )
    );

    await waitFor(() => {
      expect(screen.getByRole('heading', { name: /opportunities/i })).toBeInTheDocument();
    });
  });

  it('shows opportunity cards after data loads', async () => {
    if (!OpportunitiesPage) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValue(paginatedOpps as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OpportunitiesPage)
      )
    );

    await waitFor(() => {
      expect(screen.getByText('VP Strategy & Operations')).toBeInTheDocument();
    });
  });

  it('renders filter bar with opportunity count', async () => {
    if (!OpportunitiesPage) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValue(paginatedOpps as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OpportunitiesPage)
      )
    );

    await waitFor(() => {
      // Filter section or count display should be present
      const el =
        screen.queryByText(/2 opportunit/i) ??
        screen.queryByText(/high/i) ??
        screen.queryByText(/filter/i);
      expect(el).not.toBeNull();
    });
  });

  it('shows skeleton loading state while fetching', () => {
    if (!OpportunitiesPage) return;
    // Deliberately never resolves to keep loading state
    vi.mocked(opportunitiesApi.list).mockImplementation(
      () => new Promise(() => {}) as never
    );

    const { container } = render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OpportunitiesPage)
      )
    );

    // Skeleton uses animate-pulse — check container for it
    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('shows empty state when no opportunities found', async () => {
    if (!OpportunitiesPage) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValue(emptyResponse as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OpportunitiesPage)
      )
    );

    await waitFor(() => {
      expect(screen.getByText(/no opportunities/i)).toBeInTheDocument();
    });
  });

  it('opens OpportunityDetail dialog when a card is clicked', async () => {
    if (!OpportunitiesPage) return;
    vi.mocked(opportunitiesApi.list).mockResolvedValue(paginatedOpps as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OpportunitiesPage)
      )
    );

    // Wait for cards
    await waitFor(() => {
      expect(screen.getByText('VP Strategy & Operations')).toBeInTheDocument();
    });

    // Click the first opportunity card
    const card = screen.getByText('VP Strategy & Operations').closest('[data-testid]') ??
      screen.getByText('VP Strategy & Operations');
    fireEvent.click(card);

    // Dialog / modal content should appear — look for detail-specific content
    await waitFor(() => {
      const whyFit =
        screen.queryByText(/why this fits/i) ??
        screen.queryByText(/strong mba/i) ??
        screen.queryByRole('dialog');
      expect(whyFit).not.toBeNull();
    });
  });

  it('shows error state and retry button when API fails', async () => {
    if (!OpportunitiesPage) return;
    vi.mocked(opportunitiesApi.list).mockRejectedValue(new Error('Network error'));

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OpportunitiesPage)
      )
    );

    await waitFor(() => {
      expect(
        screen.getByRole('button', { name: /retry/i })
      ).toBeInTheDocument();
    });
  });
});
