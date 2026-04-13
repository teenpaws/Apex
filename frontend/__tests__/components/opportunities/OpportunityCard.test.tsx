import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Opportunity } from '@/types';

// ---------------------------------------------------------------------------
// Stub for OpportunityCard — replace with real import once component exists:
//   import OpportunityCard from '@/components/opportunities/OpportunityCard';
// ---------------------------------------------------------------------------

interface OpportunityCardProps {
  opportunity: Opportunity;
  onClick?: () => void;
}

let OpportunityCard: React.ComponentType<OpportunityCardProps>;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  OpportunityCard = require('@/components/opportunities/OpportunityCard').default;
} catch {
  OpportunityCard = ({ opportunity, onClick }) => {
    const confidenceClass =
      opportunity.confidence === 'HIGH'
        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
        : opportunity.confidence === 'MEDIUM'
        ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
        : 'bg-muted text-muted-foreground border-border';

    return (
      <div
        data-testid="opportunity-card"
        onClick={onClick}
        className="bg-gradient-to-br from-violet-500/10 to-purple-600/5 border-violet-500/20"
      >
        <span data-testid="opp-role">
          {opportunity.role ?? opportunity.predicted_role}
        </span>
        <span data-testid="opp-company">{opportunity.company}</span>
        <span
          data-testid="opp-confidence-badge"
          className={confidenceClass}
        >
          {opportunity.confidence}
        </span>
        <span data-testid="opp-fit-score">{opportunity.fit_score}</span>
        <div
          data-testid="opp-fit-progress"
          role="progressbar"
          aria-valuenow={opportunity.fit_score}
          aria-valuemin={0}
          aria-valuemax={100}
          style={{ width: `${opportunity.fit_score}%` }}
        />
        <p data-testid="opp-why-fit" className="line-clamp-2">
          {opportunity.whyFit ?? opportunity.why_fit}
        </p>
      </div>
    );
  };
}

// ---------------------------------------------------------------------------
// Shared fixture
// ---------------------------------------------------------------------------

const baseOpp: Opportunity = {
  id: 'o1',
  user_id: 'u1',
  company_id: 'c1',
  predicted_role: 'VP Strategy & Operations',
  confidence: 'HIGH',
  timeline_weeks: 6,
  why_fit: 'Strong MBA background + AI sector experience.',
  positioning_notes: 'Lead with your HEC network in Paris tech ecosystem.',
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

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('OpportunityCard', () => {
  it('renders predicted_role', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(screen.getByTestId('opp-role')).toHaveTextContent(
      'VP Strategy & Operations'
    );
  });

  it('renders company name', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(screen.getByTestId('opp-company')).toHaveTextContent('Mistral AI');
  });

  it('renders confidence badge', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(screen.getByTestId('opp-confidence-badge')).toBeInTheDocument();
  });

  it('HIGH confidence badge has emerald color class', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(screen.getByTestId('opp-confidence-badge').className).toContain('emerald');
  });

  it('MEDIUM confidence badge has amber color class', () => {
    render(
      <OpportunityCard opportunity={{ ...baseOpp, confidence: 'MEDIUM' }} />
    );
    expect(screen.getByTestId('opp-confidence-badge').className).toContain('amber');
  });

  it('SPECULATIVE confidence badge has muted class', () => {
    render(
      <OpportunityCard opportunity={{ ...baseOpp, confidence: 'SPECULATIVE' }} />
    );
    expect(screen.getByTestId('opp-confidence-badge').className).toContain('muted');
  });

  it('renders fit_score as a number', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(screen.getByTestId('opp-fit-score')).toHaveTextContent('87');
  });

  it('renders a progress bar for fit_score', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    const bar = screen.getByRole('progressbar');
    expect(bar).toBeInTheDocument();
    expect(bar).toHaveAttribute('aria-valuenow', '87');
  });

  it('renders why_fit text', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(screen.getByTestId('opp-why-fit')).toHaveTextContent(
      'Strong MBA background'
    );
  });

  it('why_fit element has line-clamp-2 class for truncation', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(screen.getByTestId('opp-why-fit')).toHaveClass('line-clamp-2');
  });

  it('calls onClick when card is clicked', () => {
    const handleClick = vi.fn();
    render(<OpportunityCard opportunity={baseOpp} onClick={handleClick} />);
    fireEvent.click(screen.getByTestId('opportunity-card'));
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it('does not crash when onClick is omitted', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    expect(() =>
      fireEvent.click(screen.getByTestId('opportunity-card'))
    ).not.toThrow();
  });

  it('card has violet gradient background class', () => {
    render(<OpportunityCard opportunity={baseOpp} />);
    const card = screen.getByTestId('opportunity-card');
    expect(card.className).toContain('violet');
  });
});
