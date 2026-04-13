'use client';

import * as React from 'react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { SlidersHorizontal, X } from 'lucide-react';

export interface OpportunityFilterState {
  confidence: ('HIGH' | 'MEDIUM' | 'SPECULATIVE')[];
  status: ('PREDICTED' | 'APPROACHED' | 'INTERVIEWING' | 'CLOSED')[];
  timeline_max_weeks: number | null;
  sort: 'fit_score' | 'timeline_weeks' | 'confidence' | 'created_at';
  sort_dir: 'asc' | 'desc';
}

export const DEFAULT_FILTERS: OpportunityFilterState = {
  confidence: [],
  status: [],
  timeline_max_weeks: null,
  sort: 'fit_score',
  sort_dir: 'desc',
};

interface OpportunityFiltersProps {
  filters: OpportunityFilterState;
  onChange: (f: OpportunityFilterState) => void;
  total: number;
}

const CONFIDENCE_OPTIONS: ('HIGH' | 'MEDIUM' | 'SPECULATIVE')[] = [
  'HIGH',
  'MEDIUM',
  'SPECULATIVE',
];

const STATUS_OPTIONS: ('PREDICTED' | 'APPROACHED' | 'INTERVIEWING' | 'CLOSED')[] =
  ['PREDICTED', 'APPROACHED', 'INTERVIEWING', 'CLOSED'];

const CONFIDENCE_CHIP_CLASSES: Record<string, string> = {
  HIGH: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30 hover:bg-amber-500/30',
  SPECULATIVE: 'bg-muted text-muted-foreground border-border hover:bg-muted/80',
};

const CONFIDENCE_ACTIVE_CLASSES: Record<string, string> = {
  HIGH: 'ring-2 ring-emerald-400/60',
  MEDIUM: 'ring-2 ring-amber-400/60',
  SPECULATIVE: 'ring-2 ring-muted-foreground/40',
};

const TIMELINE_OPTIONS: { label: string; value: number | null }[] = [
  { label: 'Any timeline', value: null },
  { label: '< 4 weeks', value: 4 },
  { label: '< 8 weeks', value: 8 },
  { label: '< 12 weeks', value: 12 },
];

const SORT_OPTIONS: { label: string; value: OpportunityFilterState['sort'] }[] = [
  { label: 'Fit Score', value: 'fit_score' },
  { label: 'Timeline', value: 'timeline_weeks' },
  { label: 'Confidence', value: 'confidence' },
  { label: 'Date Added', value: 'created_at' },
];

function toggleArrayItem<T>(arr: T[], item: T): T[] {
  return arr.includes(item) ? arr.filter((x) => x !== item) : [...arr, item];
}

export function OpportunityFilters({
  filters,
  onChange,
  total,
}: OpportunityFiltersProps) {
  const hasActiveFilters =
    filters.confidence.length > 0 ||
    filters.status.length > 0 ||
    filters.timeline_max_weeks !== null;

  function handleConfidenceToggle(c: 'HIGH' | 'MEDIUM' | 'SPECULATIVE') {
    onChange({ ...filters, confidence: toggleArrayItem(filters.confidence, c) });
  }

  function handleStatusToggle(s: 'PREDICTED' | 'APPROACHED' | 'INTERVIEWING' | 'CLOSED') {
    onChange({ ...filters, status: toggleArrayItem(filters.status, s) });
  }

  function handleTimelineChange(val: string) {
    const parsed = val === 'null' ? null : Number(val);
    onChange({ ...filters, timeline_max_weeks: parsed });
  }

  function handleSortChange(val: string) {
    onChange({
      ...filters,
      sort: val as OpportunityFilterState['sort'],
    });
  }

  function handleSortDirToggle() {
    onChange({ ...filters, sort_dir: filters.sort_dir === 'desc' ? 'asc' : 'desc' });
  }

  function handleClearAll() {
    onChange(DEFAULT_FILTERS);
  }

  return (
    <div className="space-y-3">
      {/* Header row */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground">
            {total} {total === 1 ? 'opportunity' : 'opportunities'}
          </span>
        </div>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            className="h-7 gap-1 text-xs text-muted-foreground"
          >
            <X className="h-3 w-3" />
            Clear filters
          </Button>
        )}
      </div>

      {/* Filter controls */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Confidence chips */}
        <div className="flex items-center gap-1">
          {CONFIDENCE_OPTIONS.map((c) => {
            const active = filters.confidence.includes(c);
            return (
              <button
                key={c}
                type="button"
                onClick={() => handleConfidenceToggle(c)}
                className={[
                  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all',
                  CONFIDENCE_CHIP_CLASSES[c],
                  active ? CONFIDENCE_ACTIVE_CLASSES[c] : '',
                ]
                  .filter(Boolean)
                  .join(' ')}
              >
                {c}
              </button>
            );
          })}
        </div>

        {/* Separator */}
        <div className="h-5 w-px bg-border" />

        {/* Status multi-select (native toggle chips) */}
        <div className="flex items-center gap-1 flex-wrap">
          {STATUS_OPTIONS.map((s) => {
            const active = filters.status.includes(s);
            return (
              <button
                key={s}
                type="button"
                onClick={() => handleStatusToggle(s)}
                className={[
                  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all',
                  active
                    ? 'bg-primary/20 text-primary border-primary/30 ring-2 ring-primary/30'
                    : 'bg-muted text-muted-foreground border-border hover:bg-muted/80',
                ]
                  .join(' ')}
              >
                {s === 'JOB_POSTING_PATTERN' ? 'Job Pattern' : s.charAt(0) + s.slice(1).toLowerCase()}
              </button>
            );
          })}
        </div>

        {/* Separator */}
        <div className="h-5 w-px bg-border" />

        {/* Timeline dropdown */}
        <Select
          value={filters.timeline_max_weeks === null ? 'null' : String(filters.timeline_max_weeks)}
          onValueChange={handleTimelineChange}
        >
          <SelectTrigger size="sm" className="w-36 h-7 text-xs">
            <SelectValue placeholder="Any timeline" />
          </SelectTrigger>
          <SelectContent>
            {TIMELINE_OPTIONS.map((opt) => (
              <SelectItem key={String(opt.value)} value={String(opt.value)}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Sort dropdown */}
        <Select value={filters.sort} onValueChange={handleSortChange}>
          <SelectTrigger size="sm" className="w-36 h-7 text-xs">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            {SORT_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Sort direction toggle */}
        <button
          type="button"
          onClick={handleSortDirToggle}
          className="inline-flex items-center rounded-lg border border-input bg-transparent px-2 py-1 text-xs text-muted-foreground hover:bg-muted transition-colors h-7"
          title={filters.sort_dir === 'desc' ? 'Descending — click to ascending' : 'Ascending — click to descending'}
        >
          {filters.sort_dir === 'desc' ? '↓ Desc' : '↑ Asc'}
        </button>
      </div>
    </div>
  );
}
