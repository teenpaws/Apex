'use client';

import { useState, useMemo } from 'react';
import { Radio, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SkeletonCard } from '@/components/shared/SkeletonCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { SignalCard } from '@/components/signals/SignalCard';
import { SignalFilters } from '@/components/signals/SignalFilters';
import type { SignalFilterState } from '@/components/signals/SignalFilters';
import { SignalDetailPanel } from '@/components/signals/SignalDetailPanel';
import { useSignals, useIngestSignals } from '@/hooks/useSignals';
import type { Signal } from '@/types';

const DEFAULT_FILTERS: SignalFilterState = {
  types: [],
  dateRange: 'all',
  company: '',
  minRelevance: 0,
};

function dateRangeCutoff(range: SignalFilterState['dateRange']): number {
  const now = Date.now();
  if (range === '7d')  return now - 7  * 86_400_000;
  if (range === '30d') return now - 30 * 86_400_000;
  if (range === '90d') return now - 90 * 86_400_000;
  return 0; // 'all'
}

export default function SignalsPage() {
  const [filters, setFilters] = useState<SignalFilterState>(DEFAULT_FILTERS);
  const [selectedSignal, setSelectedSignal] = useState<Signal | null>(null);

  // Fetch all signals (backend pagination: large per_page to allow client filtering)
  const signalsQuery = useSignals({ per_page: 100 });
  const ingest = useIngestSignals();

  // Client-side filter (complementary to backend filtering)
  const filteredSignals = useMemo(() => {
    const items = signalsQuery.data?.data ?? [];
    const cutoff = dateRangeCutoff(filters.dateRange);

    return items.filter((s) => {
      if (filters.types.length > 0 && !filters.types.includes(s.type)) return false;
      if (cutoff > 0 && new Date(s.signal_date).getTime() < cutoff) return false;
      if (
        filters.company &&
        !(s.company ?? s.company_id)
          .toLowerCase()
          .includes(filters.company.toLowerCase())
      )
        return false;
      if (s.relevance_score < filters.minRelevance) return false;
      return true;
    });
  }, [signalsQuery.data, filters]);

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Radio className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold text-foreground">Signals</h1>
          {!signalsQuery.isLoading && (
            <span className="text-xs text-muted-foreground ml-1">
              ({filteredSignals.length} of {signalsQuery.data?.total ?? 0})
            </span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => ingest.mutate()}
          disabled={ingest.isPending}
          className="flex items-center gap-2"
        >
          <RefreshCw
            className={`h-3.5 w-3.5 ${ingest.isPending ? 'animate-spin' : ''}`}
          />
          {ingest.isPending ? 'Ingesting…' : 'Ingest Now'}
        </Button>
      </div>

      {ingest.isSuccess && (
        <div className="text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">
          Ingestion queued — run ID: {ingest.data?.run_id}. Signals will appear shortly.
        </div>
      )}

      {/* Filters */}
      <SignalFilters filters={filters} onChange={setFilters} />

      {/* Signal list */}
      {signalsQuery.isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <SkeletonCard key={i} lines={3} />
          ))}
        </div>
      ) : signalsQuery.isError ? (
        <ErrorState
          error={signalsQuery.error as Error}
          onRetry={() => signalsQuery.refetch()}
        />
      ) : filteredSignals.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-card p-12 text-center">
          <Radio className="h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm font-medium text-foreground">No signals match your filters</p>
          <p className="text-xs text-muted-foreground">
            Try adjusting the filters or ingest new signals.
          </p>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setFilters(DEFAULT_FILTERS)}
          >
            Clear filters
          </Button>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredSignals.map((signal) => (
            <SignalCard
              key={signal.id}
              signal={signal}
              onClick={setSelectedSignal}
              isSelected={selectedSignal?.id === signal.id}
            />
          ))}
        </div>
      )}

      {/* Detail panel (slide-over) */}
      <SignalDetailPanel
        signal={selectedSignal}
        onClose={() => setSelectedSignal(null)}
      />
    </div>
  );
}
