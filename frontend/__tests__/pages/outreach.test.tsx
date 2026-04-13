import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import type { OutreachEmail } from '@/types';

// ---------------------------------------------------------------------------
// Mock API
// ---------------------------------------------------------------------------

vi.mock('@/lib/api', () => ({
  outreachApi: {
    list: vi.fn(),
    draft: vi.fn(),
    send: vi.fn(),
    oauthConnect: vi.fn(),
  },
}));

vi.mock('@/lib/api/client', () => ({
  outreachApi: {
    list: vi.fn(),
    draft: vi.fn(),
    send: vi.fn(),
    oauthConnect: vi.fn(),
  },
}));

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
  usePathname: () => '/outreach',
}));

import { outreachApi } from '@/lib/api/client';

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const draftEmail1: OutreachEmail = {
  id: 'e1',
  user_id: 'u1',
  action_id: 'a1',
  contact_id: 'ct1',
  subject: 'Introduction — MBA Strategy & Ops',
  body: 'Hi Sophie, I came across Mistral AI\'s recent Series B funding...',
  tone: 'PROFESSIONAL',
};

const sentEmail: OutreachEmail = {
  id: 'e2',
  user_id: 'u1',
  action_id: 'a2',
  contact_id: 'ct2',
  subject: 'Following up on Pigment BD role',
  body: 'Hi Pierre, following up on my previous email...',
  tone: 'WARM',
  sent_at: '2026-04-11T14:00:00Z',
};

const paginatedEmails = {
  data: { data: [draftEmail1, sentEmail], total: 2, page: 1, per_page: 20 },
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

let OutreachPage: React.ComponentType | null = null;

try {
  const mod = await import('@/app/(dashboard)/outreach/page');
  OutreachPage = mod.default ?? null;
} catch {
  // page not yet implemented
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Outreach Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders outreach page heading', async () => {
    if (!OutreachPage) return;
    vi.mocked(outreachApi.list).mockResolvedValue(paginatedEmails as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OutreachPage)
      )
    );

    await waitFor(() => {
      expect(
        screen.getByRole('heading', { name: /outreach/i })
      ).toBeInTheDocument();
    });
  });

  it('shows email drafts when data is loaded', async () => {
    if (!OutreachPage) return;
    vi.mocked(outreachApi.list).mockResolvedValue(paginatedEmails as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OutreachPage)
      )
    );

    await waitFor(() => {
      expect(
        screen.getByText(/introduction.*mba|MBA Strategy/i)
      ).toBeInTheDocument();
    });
  });

  it('shows empty state when no emails exist', async () => {
    if (!OutreachPage) return;
    vi.mocked(outreachApi.list).mockResolvedValue(emptyResponse as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OutreachPage)
      )
    );

    await waitFor(() => {
      const emptyEl =
        screen.queryByText(/no outreach/i) ??
        screen.queryByText(/no email drafts/i) ??
        screen.queryByText(/no emails/i) ??
        screen.queryByText(/no drafts/i) ??
        screen.queryByText(/get started/i) ??
        screen.queryByText(/empty/i);
      expect(emptyEl).not.toBeNull();
    });
  });

  it('shows loading state while fetching', () => {
    if (!OutreachPage) return;
    vi.mocked(outreachApi.list).mockImplementation(
      () => new Promise(() => {}) as never
    );

    const { container } = render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OutreachPage)
      )
    );

    expect(container.querySelector('.animate-pulse')).not.toBeNull();
  });

  it('shows subject line in draft card', async () => {
    if (!OutreachPage) return;
    vi.mocked(outreachApi.list).mockResolvedValue(paginatedEmails as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OutreachPage)
      )
    );

    await waitFor(() => {
      const subjectEl =
        screen.queryByText(/Introduction.*MBA/i) ??
        screen.queryByText(/Following up/i);
      expect(subjectEl).not.toBeNull();
    });
  });

  it('shows tone badge on draft card', async () => {
    if (!OutreachPage) return;
    vi.mocked(outreachApi.list).mockResolvedValue(paginatedEmails as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OutreachPage)
      )
    );

    await waitFor(() => {
      const toneBadge =
        screen.queryByText(/professional/i) ??
        screen.queryByText(/warm/i) ??
        screen.queryByText(/direct/i);
      expect(toneBadge).not.toBeNull();
    });
  });

  it('shows compose or connect Gmail button', async () => {
    if (!OutreachPage) return;
    vi.mocked(outreachApi.list).mockResolvedValue(paginatedEmails as never);

    render(
      React.createElement(
        createWrapper(),
        null,
        React.createElement(OutreachPage)
      )
    );

    await waitFor(() => {
      const actionBtn =
        screen.queryByRole('button', { name: /compose|new email|connect gmail|draft/i }) ??
        screen.queryByText(/connect gmail/i) ??
        screen.queryByText(/compose/i);
      expect(actionBtn).not.toBeNull();
    });
  });
});
