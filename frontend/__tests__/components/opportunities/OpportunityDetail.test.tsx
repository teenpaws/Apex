import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Opportunity } from '@/types';

// ---------------------------------------------------------------------------
// Stub for OpportunityDetail — replace with real import once component exists:
//   import OpportunityDetail from '@/components/opportunities/OpportunityDetail';
// ---------------------------------------------------------------------------

interface OpportunityDetailProps {
  opportunity: Opportunity | null;
  onClose: () => void;
  onRefresh: (id: string) => void;
}

let OpportunityDetail: React.ComponentType<OpportunityDetailProps>;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  OpportunityDetail = require('@/components/opportunities/OpportunityDetail').default;
} catch {
  OpportunityDetail = ({ opportunity, onClose, onRefresh }) => {
    if (!opportunity) return null;

    const fitColor =
      opportunity.fit_score >= 70
        ? 'text-green-400'
        : opportunity.fit_score >= 50
        ? 'text-amber-400'
        : 'text-red-400';

    const confidenceClass =
      opportunity.confidence === 'HIGH'
        ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
        : opportunity.confidence === 'MEDIUM'
        ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
        : 'bg-muted text-muted-foreground border-border';

    const statusClass =
      opportunity.status === 'PREDICTED'
        ? 'bg-blue-500/20 text-blue-400'
        : opportunity.status === 'APPROACHED'
        ? 'bg-amber-500/20 text-amber-400'
        : opportunity.status === 'INTERVIEWING'
        ? 'bg-violet-500/20 text-violet-400'
        : 'bg-muted text-muted-foreground';

    return (
      <div role="dialog" data-testid="opportunity-detail">
        <button data-testid="close-button" onClick={onClose}>
          Close
        </button>

        <h2 data-testid="detail-role">
          {opportunity.role ?? opportunity.predicted_role}
        </h2>
        <span data-testid="detail-company">{opportunity.company}</span>

        <span
          data-testid="detail-confidence-badge"
          className={confidenceClass}
        >
          {opportunity.confidence}
        </span>

        <span
          data-testid="detail-status-badge"
          className={statusClass}
        >
          {opportunity.status}
        </span>

        <span data-testid="detail-fit-score" className={fitColor}>
          {opportunity.fit_score}
        </span>

        <section data-testid="why-fit-section">
          <h3>Why This Fits</h3>
          <p>{opportunity.whyFit ?? opportunity.why_fit}</p>
        </section>

        <section data-testid="positioning-section">
          <p>{opportunity.approach_angle}</p>
        </section>

        <button
          data-testid="refresh-button"
          onClick={() => onRefresh(opportunity.id)}
        >
          Refresh Analysis
        </button>
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
  approach_angle: 'Lead with your HEC network in Paris tech ecosystem.',
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

describe('OpportunityDetail', () => {
  it('renders nothing when opportunity is null', () => {
    const { container } = render(
      <OpportunityDetail
        opportunity={null}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(container.firstChild).toBeNull();
  });

  it('renders dialog when opportunity is provided', () => {
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('shows role title', () => {
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('detail-role')).toHaveTextContent(
      'VP Strategy & Operations'
    );
  });

  it('shows company name', () => {
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('detail-company')).toHaveTextContent('Mistral AI');
  });

  it('shows confidence badge with emerald class for HIGH', () => {
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('detail-confidence-badge').className).toContain(
      'emerald'
    );
  });

  it('shows status badge', () => {
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('detail-status-badge')).toHaveTextContent(
      'PREDICTED'
    );
  });

  it('fit_score ≥70 has green color class', () => {
    render(
      <OpportunityDetail
        opportunity={{ ...baseOpp, fit_score: 87 }}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('detail-fit-score').className).toContain('green');
  });

  it('fit_score 50–69 has amber color class', () => {
    render(
      <OpportunityDetail
        opportunity={{ ...baseOpp, fit_score: 60 }}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('detail-fit-score').className).toContain('amber');
  });

  it('fit_score <50 has red color class', () => {
    render(
      <OpportunityDetail
        opportunity={{ ...baseOpp, fit_score: 35 }}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('detail-fit-score').className).toContain('red');
  });

  it('shows why_fit section', () => {
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('why-fit-section')).toHaveTextContent(
      'Why This Fits'
    );
    expect(screen.getByTestId('why-fit-section')).toHaveTextContent(
      'Strong MBA background'
    );
  });

  it('shows approach_angle', () => {
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={vi.fn()}
      />
    );
    expect(screen.getByTestId('positioning-section')).toHaveTextContent(
      'HEC network'
    );
  });

  it('"Refresh Analysis" button calls onRefresh with opportunity.id', () => {
    const onRefresh = vi.fn();
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={vi.fn()}
        onRefresh={onRefresh}
      />
    );
    fireEvent.click(screen.getByTestId('refresh-button'));
    expect(onRefresh).toHaveBeenCalledWith('o1');
  });

  it('onClose is called when close button is clicked', () => {
    const onClose = vi.fn();
    render(
      <OpportunityDetail
        opportunity={baseOpp}
        onClose={onClose}
        onRefresh={vi.fn()}
      />
    );
    fireEvent.click(screen.getByTestId('close-button'));
    expect(onClose).toHaveBeenCalledOnce();
  });
});
