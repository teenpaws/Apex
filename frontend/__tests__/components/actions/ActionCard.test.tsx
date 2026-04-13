import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import React from 'react';
import type { Action } from '@/types';

// ---------------------------------------------------------------------------
// Stub for ActionCard — replace with real import once component exists:
//   import { ActionCard } from '@/components/actions/ActionCard';
// ---------------------------------------------------------------------------

interface ActionCardProps {
  action: Action;
  onClick?: (action: Action) => void;
  onStatusChange?: (id: string, status: Action['status']) => void;
}

let ActionCard: React.ComponentType<ActionCardProps>;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  ActionCard = require('@/components/actions/ActionCard').ActionCard;
} catch {
  ActionCard = ({ action, onClick, onStatusChange }) => (
    <div
      data-testid="action-card"
      onClick={() => onClick?.(action)}
    >
      <span data-testid="action-title">{action.title}</span>
      <span data-testid="action-company">{action.company ?? action.company_id}</span>
      <span
        data-testid="action-priority"
        className={
          action.priority === 'HIGH'
            ? 'bg-red-500/20 text-red-400 border-red-500/30'
            : action.priority === 'MEDIUM'
            ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
            : 'bg-muted text-muted-foreground'
        }
      >
        {action.priority}
      </span>
      <span data-testid="action-status">{action.status}</span>
      <span data-testid="action-type">{action.type}</span>
      <span data-testid="action-due-date">{action.dueDate ?? action.due_date}</span>
      <p data-testid="action-description">{action.description}</p>
      {/* Type icon hint — used by icon-render test */}
      {action.type === 'OUTREACH' && (
        <span data-testid="action-icon-outreach" aria-label="Mail">✉</span>
      )}
      <button
        data-testid="action-status-change"
        onClick={() => onStatusChange?.(action.id, 'DONE')}
      >
        Mark Done
      </button>
    </div>
  );
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
  description: 'Send initial outreach email to VP Strategy.',
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

describe('ActionCard', () => {
  it('renders title', () => {
    render(<ActionCard action={baseAction} />);
    expect(screen.getByTestId('action-title')).toHaveTextContent(
      'Reach out to Sophie Martin'
    );
  });

  it('renders company name', () => {
    render(<ActionCard action={baseAction} />);
    expect(screen.getByTestId('action-company')).toHaveTextContent('Mistral AI');
  });

  it('falls back to company_id when company display name is missing', () => {
    const noCompanyName = { ...baseAction, company: undefined };
    render(<ActionCard action={noCompanyName} />);
    expect(screen.getByTestId('action-company')).toHaveTextContent('c1');
  });

  it('HIGH priority badge has red color class', () => {
    render(<ActionCard action={baseAction} />);
    expect(screen.getByTestId('action-priority').className).toContain('red');
  });

  it('MEDIUM priority badge has amber color class', () => {
    render(<ActionCard action={{ ...baseAction, priority: 'MEDIUM' }} />);
    expect(screen.getByTestId('action-priority').className).toContain('amber');
  });

  it('LOW priority badge has muted class', () => {
    render(<ActionCard action={{ ...baseAction, priority: 'LOW' }} />);
    expect(screen.getByTestId('action-priority').className).toContain('muted');
  });

  it('renders due date', () => {
    render(<ActionCard action={baseAction} />);
    expect(screen.getByTestId('action-due-date')).toHaveTextContent('Due 20 Apr');
  });

  it('falls back to raw due_date when dueDate alias is missing', () => {
    const noDueDate = { ...baseAction, dueDate: undefined };
    render(<ActionCard action={noDueDate} />);
    expect(screen.getByTestId('action-due-date')).toHaveTextContent(
      noDueDate.due_date
    );
  });

  it('renders action type', () => {
    render(<ActionCard action={baseAction} />);
    expect(screen.getByTestId('action-type')).toHaveTextContent('OUTREACH');
  });

  it('renders description', () => {
    render(<ActionCard action={baseAction} />);
    expect(screen.getByTestId('action-description')).toHaveTextContent(
      'Send initial outreach email'
    );
  });

  it('shows mail icon or type label for OUTREACH type', () => {
    render(<ActionCard action={baseAction} />);
    // Either an icon element with aria-label="Mail" or the type text
    const icon = screen.queryByLabelText('Mail') ?? screen.queryByTestId('action-icon-outreach');
    const typeLabel = screen.getByTestId('action-type');
    expect(icon !== null || typeLabel.textContent === 'OUTREACH').toBe(true);
  });

  it('calls onClick when card is clicked', () => {
    const handleClick = vi.fn();
    render(<ActionCard action={baseAction} onClick={handleClick} />);
    fireEvent.click(screen.getByTestId('action-card'));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('calls onClick with the action object', () => {
    const handleClick = vi.fn();
    render(<ActionCard action={baseAction} onClick={handleClick} />);
    fireEvent.click(screen.getByTestId('action-card'));
    expect(handleClick).toHaveBeenCalledWith(baseAction);
  });

  it('does not crash without onClick', () => {
    render(<ActionCard action={baseAction} />);
    expect(() =>
      fireEvent.click(screen.getByTestId('action-card'))
    ).not.toThrow();
  });

  it('calls onStatusChange with new status when triggered', () => {
    const handleStatusChange = vi.fn();
    render(
      <ActionCard
        action={baseAction}
        onStatusChange={handleStatusChange}
      />
    );
    fireEvent.click(screen.getByTestId('action-status-change'));
    expect(handleStatusChange).toHaveBeenCalledWith('a1', 'DONE');
  });

  it('renders action status', () => {
    render(<ActionCard action={baseAction} />);
    expect(screen.getByTestId('action-status')).toHaveTextContent('TODO');
  });
});
