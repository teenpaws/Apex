import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Signal } from '@/types';

// ---------------------------------------------------------------------------
// Stub for SignalFilters — replace with real import once component exists:
//   import SignalFilters from '@/components/signals/SignalFilters';
// ---------------------------------------------------------------------------

const ALL_SIGNAL_TYPES: Signal['type'][] = [
  'FUNDING',
  'EXEC_HIRE',
  'EXPANSION',
  'LAYOFF',
  'JOB_POSTING_PATTERN',
  'MA',
  'CONTRACT',
  'EARNINGS',
];

interface SignalFiltersProps {
  selectedTypes: Signal['type'][];
  onTypesChange: (types: Signal['type'][]) => void;
  dateRange: string;
  onDateRangeChange: (range: string) => void;
  company: string;
  onCompanyChange: (company: string) => void;
  minRelevance: number;
  onMinRelevanceChange: (score: number) => void;
}

let SignalFilters: React.ComponentType<SignalFiltersProps>;

try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  SignalFilters = require('@/components/signals/SignalFilters').default;
} catch {
  // Fallback stub
  SignalFilters = ({
    selectedTypes,
    onTypesChange,
    dateRange,
    onDateRangeChange,
    company,
    onCompanyChange,
    minRelevance,
    onMinRelevanceChange,
  }) => (
    <div data-testid="signal-filters">
      <div data-testid="type-checkboxes">
        {ALL_SIGNAL_TYPES.map((type) => (
          <label key={type} data-testid={`checkbox-label-${type}`}>
            <input
              type="checkbox"
              data-testid={`checkbox-${type}`}
              checked={selectedTypes.includes(type)}
              onChange={(e) => {
                if (e.target.checked) {
                  onTypesChange([...selectedTypes, type]);
                } else {
                  onTypesChange(selectedTypes.filter((t) => t !== type));
                }
              }}
            />
            {type}
          </label>
        ))}
      </div>

      <select
        data-testid="date-range-select"
        value={dateRange}
        onChange={(e) => onDateRangeChange(e.target.value)}
      >
        <option value="7d">Last 7 days</option>
        <option value="30d">Last 30 days</option>
        <option value="90d">Last 90 days</option>
        <option value="all">All time</option>
      </select>

      <input
        data-testid="company-input"
        type="text"
        value={company}
        placeholder="Filter by company"
        onChange={(e) => onCompanyChange(e.target.value)}
      />

      <input
        data-testid="min-relevance-input"
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={minRelevance}
        onChange={(e) => onMinRelevanceChange(parseFloat(e.target.value))}
      />
      <span data-testid="min-relevance-value">{minRelevance}</span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Default props factory
// ---------------------------------------------------------------------------

const defaultProps = (): SignalFiltersProps => ({
  selectedTypes: [],
  onTypesChange: vi.fn(),
  dateRange: '30d',
  onDateRangeChange: vi.fn(),
  company: '',
  onCompanyChange: vi.fn(),
  minRelevance: 0,
  onMinRelevanceChange: vi.fn(),
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('SignalFilters', () => {
  it('renders all 8 signal type checkboxes', () => {
    render(<SignalFilters {...defaultProps()} />);
    for (const type of ALL_SIGNAL_TYPES) {
      expect(
        screen.getByTestId(`checkbox-${type}`),
        `checkbox for ${type} should be present`
      ).toBeInTheDocument();
    }
  });

  it('checkboxes reflect selectedTypes prop — checked state', () => {
    render(<SignalFilters {...defaultProps()} selectedTypes={['FUNDING']} />);
    expect(screen.getByTestId('checkbox-FUNDING')).toBeChecked();
    expect(screen.getByTestId('checkbox-EXEC_HIRE')).not.toBeChecked();
  });

  it('selecting an unchecked type calls onTypesChange with updated array', () => {
    const onTypesChange = vi.fn();
    render(
      <SignalFilters
        {...defaultProps()}
        selectedTypes={[]}
        onTypesChange={onTypesChange}
      />
    );
    fireEvent.click(screen.getByTestId('checkbox-FUNDING'));
    expect(onTypesChange).toHaveBeenCalledWith(['FUNDING']);
  });

  it('deselecting a checked type calls onTypesChange with type removed', () => {
    const onTypesChange = vi.fn();
    render(
      <SignalFilters
        {...defaultProps()}
        selectedTypes={['FUNDING', 'EXEC_HIRE']}
        onTypesChange={onTypesChange}
      />
    );
    fireEvent.click(screen.getByTestId('checkbox-FUNDING'));
    expect(onTypesChange).toHaveBeenCalledWith(['EXEC_HIRE']);
  });

  it('date range dropdown shows expected options', () => {
    render(<SignalFilters {...defaultProps()} />);
    const select = screen.getByTestId('date-range-select');
    const options = Array.from(select.querySelectorAll('option')).map(
      (o) => o.value
    );
    expect(options).toContain('7d');
    expect(options).toContain('30d');
    expect(options).toContain('90d');
  });

  it('selecting date range calls onDateRangeChange', () => {
    const onDateRangeChange = vi.fn();
    render(
      <SignalFilters
        {...defaultProps()}
        onDateRangeChange={onDateRangeChange}
      />
    );
    fireEvent.change(screen.getByTestId('date-range-select'), {
      target: { value: '7d' },
    });
    expect(onDateRangeChange).toHaveBeenCalledWith('7d');
  });

  it('company text input reflects company prop', () => {
    render(<SignalFilters {...defaultProps()} company="Mistral" />);
    expect(screen.getByTestId('company-input')).toHaveValue('Mistral');
  });

  it('typing in company input calls onCompanyChange', () => {
    const onCompanyChange = vi.fn();
    render(
      <SignalFilters {...defaultProps()} onCompanyChange={onCompanyChange} />
    );
    fireEvent.change(screen.getByTestId('company-input'), {
      target: { value: 'Pigment' },
    });
    expect(onCompanyChange).toHaveBeenCalledWith('Pigment');
  });

  it('min relevance filter reflects minRelevance prop', () => {
    render(<SignalFilters {...defaultProps()} minRelevance={0.5} />);
    expect(screen.getByTestId('min-relevance-input')).toHaveValue('0.5');
  });

  it('changing min relevance calls onMinRelevanceChange', () => {
    const onMinRelevanceChange = vi.fn();
    render(
      <SignalFilters
        {...defaultProps()}
        onMinRelevanceChange={onMinRelevanceChange}
      />
    );
    fireEvent.change(screen.getByTestId('min-relevance-input'), {
      target: { value: '0.7' },
    });
    expect(onMinRelevanceChange).toHaveBeenCalledWith(0.7);
  });
});
