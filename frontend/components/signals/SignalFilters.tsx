'use client';

import { Input } from '@/components/ui/input';

export interface SignalFilterState {
  types: string[];
  dateRange: '7d' | '30d' | '90d' | 'all';
  company: string;
  minRelevance: number;
}

const ALL_SIGNAL_TYPES = [
  { value: 'FUNDING',             label: 'Funding' },
  { value: 'EXEC_HIRE',           label: 'Exec Hire' },
  { value: 'EXPANSION',           label: 'Expansion' },
  { value: 'JOB_POSTING_PATTERN', label: 'Job Posting Pattern' },
  { value: 'LAYOFF',              label: 'Layoff' },
  { value: 'MA',                  label: 'M&A' },
  { value: 'CONTRACT',            label: 'Contract' },
  { value: 'EARNINGS',            label: 'Earnings' },
] as const;

const DATE_RANGES: { value: SignalFilterState['dateRange']; label: string }[] = [
  { value: '7d',  label: 'Last 7 days' },
  { value: '30d', label: 'Last 30 days' },
  { value: '90d', label: 'Last 90 days' },
  { value: 'all', label: 'All time' },
];

interface SignalFiltersProps {
  filters: SignalFilterState;
  onChange: (filters: SignalFilterState) => void;
}

export function SignalFilters({ filters, onChange }: SignalFiltersProps) {
  function toggleType(type: string) {
    const next = filters.types.includes(type)
      ? filters.types.filter((t) => t !== type)
      : [...filters.types, type];
    onChange({ ...filters, types: next });
  }

  return (
    <div className="rounded-xl border border-border bg-card p-4 space-y-4">
      {/* Signal type checkboxes */}
      <div>
        <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">
          Signal Type
        </p>
        <div className="flex flex-wrap gap-2">
          {ALL_SIGNAL_TYPES.map(({ value, label }) => {
            const checked = filters.types.includes(value);
            return (
              <button
                key={value}
                type="button"
                onClick={() => toggleType(value)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  checked
                    ? 'bg-primary/10 text-primary border-primary/40'
                    : 'border-border text-muted-foreground hover:border-muted-foreground/50 hover:text-foreground'
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Date range */}
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider">
            Date Range
          </label>
          <select
            value={filters.dateRange}
            onChange={(e) =>
              onChange({
                ...filters,
                dateRange: e.target.value as SignalFilterState['dateRange'],
              })
            }
            className="w-full text-sm rounded-md border border-border bg-background px-3 py-1.5 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50"
          >
            {DATE_RANGES.map(({ value, label }) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>

        {/* Company search */}
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider">
            Company
          </label>
          <Input
            placeholder="Search company..."
            value={filters.company}
            onChange={(e) =>
              onChange({ ...filters, company: e.target.value })
            }
            className="h-8 text-sm"
          />
        </div>

        {/* Min relevance slider */}
        <div>
          <label className="text-xs font-medium text-muted-foreground mb-1.5 flex justify-between uppercase tracking-wider">
            <span>Min Relevance</span>
            <span className="normal-case font-semibold text-foreground">
              {Math.round(filters.minRelevance * 100)}%
            </span>
          </label>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={filters.minRelevance}
            onChange={(e) =>
              onChange({ ...filters, minRelevance: parseFloat(e.target.value) })
            }
            className="w-full accent-primary h-1.5 rounded-full"
          />
        </div>
      </div>
    </div>
  );
}
