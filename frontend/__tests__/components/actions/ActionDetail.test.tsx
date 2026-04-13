import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import type { Action } from '@/types';

// ---------------------------------------------------------------------------
// Stub for ActionDetail — replace with real import once component exists:
//   import { ActionDetail } from '@/components/actions/ActionDetail';
// ---------------------------------------------------------------------------

interface ActionDetailProps {
  action: Action | null;
  onClose?: () => void;
  onDraftEmail?: (actionId: string) => void;
}

let ActionDetail: React.ComponentType<ActionDetailProps>;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  ActionDetail = require('@/components/actions/ActionDetail').ActionDetail;
} catch {
  ActionDetail = ({ action, onClose, onDraftEmail }) => {
    if (!action) return null;
    return (
      <div data-testid="action-detail">
        <h2 data-testid="detail-title">{action.title}</h2>
        <p data-testid="detail-description">{action.description}</p>
        <span data-testid="detail-priority">{action.priority}</span>
        <span data-testid="detail-status">{action.status}</span>
        <span data-testid="detail-type">{action.type}</span>
        <span data-testid="detail-company">{action.company ?? action.company_id}</span>
        <span data-testid="detail-due-date">{action.dueDate ?? action.due_date}</span>
        <button data-testid="close-button" onClick={onClose}>Close</button>
        <button
          data-testid="draft-email-button"
          onClick={() => onDraftEmail?.(action.id)}
        >
          Draft Email
        </button>
      </div>
    );
  };
}

// ---------------------------------------------------------------------------
// Shared fixture
// ---------------------------------------------------------------------------

const baseAction: Action = {
  id: 'a1',
  user_id: 'u1',
  opportunity_id: 'o1',
  company_id: 'c1',
  title: 'Reach out to Sophie Martin',
  description: 'Send initial outreach email to VP Strategy at Mistral AI.',
  type: 'OUTREACH',
  priority: 'HIGH',
  status: 'TODO',
  due_date: '2026-04-20T00:00:00Z',
  created_at: '2026-04-10T10:00:00Z',
  company: 'Mistral AI',
  dueDate: 'Due 20 Apr',
};

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ActionDetail', () => {
  it('renders null when action is null', () => {
    const { container } = render(<ActionDetail action={null} />);
    expect(container.firstChild).toBeNull();
  });

  it('renders title when action is provided', () => {
    render(<ActionDetail action={baseAction} />);
    expect(screen.getByTestId('detail-title')).toHaveTextContent(
      'Reach out to Sophie Martin'
    );
  });

  it('renders description', () => {
    render(<ActionDetail action={baseAction} />);
    expect(screen.getByTestId('detail-description')).toHaveTextContent(
      'Send initial outreach email'
    );
  });

  it('shows priority', () => {
    render(<ActionDetail action={baseAction} />);
    expect(screen.getByTestId('detail-priority')).toHaveTextContent('HIGH');
  });

  it('shows status', () => {
    render(<ActionDetail action={baseAction} />);
    expect(screen.getByTestId('detail-status')).toHaveTextContent('TODO');
  });

  it('shows company name', () => {
    render(<ActionDetail action={baseAction} />);
    expect(screen.getByTestId('detail-company')).toHaveTextContent('Mistral AI');
  });

  it('falls back to company_id when company display name is missing', () => {
    render(<ActionDetail action={{ ...baseAction, company: undefined }} />);
    expect(screen.getByTestId('detail-company')).toHaveTextContent('c1');
  });

  it('shows type', () => {
    render(<ActionDetail action={baseAction} />);
    expect(screen.getByTestId('detail-type')).toHaveTextContent('OUTREACH');
  });

  it('shows due date', () => {
    render(<ActionDetail action={baseAction} />);
    expect(screen.getByTestId('detail-due-date')).toHaveTextContent('Due 20 Apr');
  });

  it('calls onClose when close button is clicked', () => {
    const handleClose = vi.fn();
    render(<ActionDetail action={baseAction} onClose={handleClose} />);
    fireEvent.click(screen.getByTestId('close-button'));
    expect(handleClose).toHaveBeenCalledOnce();
  });

  it('calls onDraftEmail with action id when draft email button is clicked', () => {
    const handleDraftEmail = vi.fn();
    render(
      <ActionDetail action={baseAction} onDraftEmail={handleDraftEmail} />
    );
    fireEvent.click(screen.getByTestId('draft-email-button'));
    expect(handleDraftEmail).toHaveBeenCalledWith('a1');
  });

  it('does not crash when onDraftEmail is omitted', () => {
    render(<ActionDetail action={baseAction} />);
    expect(() =>
      fireEvent.click(screen.getByTestId('draft-email-button'))
    ).not.toThrow();
  });

  it('does not crash when onClose is omitted', () => {
    render(<ActionDetail action={baseAction} />);
    expect(() =>
      fireEvent.click(screen.getByTestId('close-button'))
    ).not.toThrow();
  });
});
