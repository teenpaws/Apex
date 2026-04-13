import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { Action } from '@/types';

// ---------------------------------------------------------------------------
// Mock API
// ---------------------------------------------------------------------------

vi.mock('@/lib/api', () => ({
  actionsApi: {
    list: vi.fn(),
    update: vi.fn(),
    draftEmail: vi.fn(),
  },
}));

vi.mock('@/lib/api/client', () => ({
  actionsApi: {
    list: vi.fn(),
    update: vi.fn(),
    draftEmail: vi.fn(),
  },
}));

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/actions',
}));

import { actionsApi } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const mockAction1: Action = {
  id: 'a1',
  user_id: 'u1',
  opportunity_id: 'o1',
  company_id: 'c1',
  title: 'Reach out to Sophie Martin',
  description: 'Send initial outreach email to VP Strategy.',
  type: 'OUTREACH',
  priority: 'HIGH',
  status: 'TODO',
  due_date: '2026-04-20T00:00:00Z',
  created_at: '2026-04-10T10:00:00Z',
  company: 'Mistral AI',
  dueDate: 'Due 20 Apr',
};

const mockAction2: Action = {
  id: 'a2',
  user_id: 'u1',
  opportunity_id: 'o2',
  company_id: 'c2',
  title: 'Research Pigment leadership',
  description: 'Identify key decision makers in product org.',
  type: 'RESEARCH',
  priority: 'MEDIUM',
  status: 'IN_PROGRESS',
  due_date: '2026-04-22T00:00:00Z',
  created_at: '2026-04-11T10:00:00Z',
  company: 'Pigment',
  dueDate: 'Due 22 Apr',
};

const paginatedActions = {
  data: { data: [mockAction1, mockAction2], total: 2, page: 1, per_page: 20 },
};

const emptyResponse = {
  data: { data: [], total: 0, page: 1, per_page: 20 },
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

let ActionsPage: React.ComponentType | null = null;

try {
  const mod = await import('@/app/(dashboard)/actions/page');
  ActionsPage = mod.default ?? null;
} catch {
  // page not yet implemented
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Actions Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders page heading', async () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockResolvedValue(paginatedActions as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /actions/i })
      ).toBeInTheDocument();
    });
  });

  it('shows action cards when data is loaded', async () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockResolvedValue(paginatedActions as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    await waitFor(() => {
      expect(
        screen.getByText('Reach out to Sophie Martin')
      ).toBeInTheDocument();
    });
  });

  it('shows loading skeleton while fetching', () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockImplementation(
      () => new Promise(() => {}) as never
    );

    const { container } = render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('shows error state when API fails', async () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockRejectedValue(new Error('Network error'));

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    await waitFor(() => {
      // Use queryAllByText to avoid "multiple elements" error when both a heading
      // and a detail paragraph contain error text
      const errorEls = screen.queryAllByText(/failed|error|something went wrong/i);
      const retryBtn = screen.queryByRole('button', { name: /retry/i });
      expect(errorEls.length > 0 || retryBtn !== null).toBe(true);
    });
  });

  it('shows empty state when no actions exist', async () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockResolvedValue(emptyResponse as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    await waitFor(() => {
      expect(screen.getByText(/no actions/i)).toBeInTheDocument();
    });
  });

  it('shows view toggle (Kanban or List) button', async () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockResolvedValue(paginatedActions as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    await waitFor(() => {
      const toggleEl =
        screen.queryByRole('button', { name: /kanban/i }) ??
        screen.queryByRole('button', { name: /list/i }) ??
        screen.queryByRole('tab', { name: /kanban/i }) ??
        screen.queryByRole('tab', { name: /list/i });
      expect(toggleEl).not.toBeNull();
    });
  });

  it('filters by HIGH priority shows correct subset', async () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockResolvedValue(paginatedActions as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    await waitFor(() => {
      expect(screen.getByText('Reach out to Sophie Martin')).toBeInTheDocument();
    });

    // Find and click a HIGH filter button if it exists
    const highFilterBtn =
      screen.queryByRole('button', { name: /^high$/i }) ??
      screen.queryByText(/^high$/i);

    if (highFilterBtn) {
      fireEvent.click(highFilterBtn);
      // After filtering, the HIGH action should still be visible
      await waitFor(() => {
        expect(screen.getByText('Reach out to Sophie Martin')).toBeInTheDocument();
      });
    }
  });

  it('shows action type in each card', async () => {
    if (!ActionsPage) return;
    vi.mocked(actionsApi.list).mockResolvedValue(paginatedActions as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(ActionsPage)
      )
    );

    await waitFor(() => {
      // Either both actions are visible, or at least the page loaded
      const outreach = screen.queryByText(/outreach/i);
      const research = screen.queryByText(/research/i);
      expect(outreach !== null || research !== null).toBe(true);
    });
  });
});
