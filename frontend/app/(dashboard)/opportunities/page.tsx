'use client';

import * as React from 'react';
import { useState, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { Sparkles, AlertCircle, Inbox, RefreshCw } from 'lucide-react';
import {
  useOpportunities,
  useRefreshOpportunity,
  useCreateAction,
} from '@/hooks/useOpportunities';
import { OpportunityFilters, DEFAULT_FILTERS } from '@/components/opportunities/OpportunityFilters';
import type { OpportunityFilterState } from '@/components/opportunities/OpportunityFilters';
import { OpportunityCard } from '@/components/opportunities/OpportunityCard';
import { OpportunityDetail } from '@/components/opportunities/OpportunityDetail';
import type { Opportunity } from '@/types';
import { useRouter } from 'next/navigation';

// ── Skeleton card ─────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-violet-500/20 bg-gradient-to-br from-violet-500/10 to-purple-600/5 p-5 space-y-3 animate-pulse">
      <div className="flex items-center justify-between">
        <div className="h-4 w-14 rounded-full bg-muted" />
        <div className="h-3 w-10 rounded bg-muted" />
      </div>
      <div className="space-y-1.5">
        <div className="h-4 w-3/4 rounded bg-muted" />
        <div className="h-3 w-1/2 rounded bg-muted" />
      </div>
      <div className="space-y-1">
        <div className="h-2 w-full rounded-full bg-muted" />
        <div className="flex justify-between">
          <div className="h-2 w-16 rounded bg-muted" />
          <div className="h-2 w-8 rounded bg-muted" />
        </div>
      </div>
      <div className="h-8 w-full rounded bg-muted" />
    </div>
  );
}

// ── Filter state → API params ─────────────────────────────────────────────────

function filtersToParams(
  filters: OpportunityFilterState,
  page: number
): Record<string, string | number> {
  const params: Record<string, string | number> = {
    page,
    per_page: 12,
    sort: filters.sort,
    sort_dir: filters.sort_dir,
  };
  if (filters.confidence.length > 0) {
    params['confidence'] = filters.confidence.join(',');
  }
  if (filters.status.length > 0) {
    params['status'] = filters.status.join(',');
  }
  if (filters.timeline_max_weeks !== null) {
    params['timeline_max_weeks'] = filters.timeline_max_weeks;
  }
  return params;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function OpportunitiesPage() {
  const router = useRouter();
  const [filters, setFilters] = useState<OpportunityFilterState>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [selectedOpp, setSelectedOpp] = useState<Opportunity | null>(null);
  // Accumulate items across pages for "load more"
  const [allOpportunities, setAllOpportunities] = useState<Opportunity[]>([]);
  const [totalLoaded, setTotalLoaded] = useState(0);

  const params = filtersToParams(filters, page);

  const {
    data: pagedData,
    isLoading,
    isError,
    refetch,
  } = useOpportunities(params);

  const refreshMutation = useRefreshOpportunity();
  const createActionMutation = useCreateAction();

  // Merge newly fetched page into accumulated list
  React.useEffect(() => {
    if (!pagedData) return;
    if (page === 1) {
      setAllOpportunities(pagedData.data);
      setTotalLoaded(pagedData.data.length);
    } else {
      setAllOpportunities((prev) => {
        const existingIds = new Set(prev.map((o) => o.id));
        const newItems = pagedData.data.filter((o) => !existingIds.has(o.id));
        return [...prev, ...newItems];
      });
      setTotalLoaded((prev) => prev + pagedData.data.length);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pagedData]);

  // Reset to page 1 when filters change
  const handleFiltersChange = useCallback((f: OpportunityFilterState) => {
    setFilters(f);
    setPage(1);
    setAllOpportunities([]);
    setTotalLoaded(0);
  }, []);

  const totalFromApi = pagedData?.total ?? 0;
  const hasMore = totalLoaded < totalFromApi;
  const displayCount = pagedData?.total ?? allOpportunities.length;

  function handleCardClick(opp: Opportunity) {
    setSelectedOpp(opp);
  }

  function handleDetailClose() {
    setSelectedOpp(null);
  }

  function handleRefresh(id: string) {
    refreshMutation.mutate(id, {
      onSuccess: () => {
        // After refresh is queued, re-fetch the list
        setPage(1);
        setAllOpportunities([]);
        setTotalLoaded(0);
        refetch();
      },
    });
  }

  function handleCreateAction(opportunityId: string) {
    createActionMutation.mutate(
      { opportunity_id: opportunityId },
      {
        onSuccess: () => {
          setSelectedOpp(null);
          router.push('/actions');
        },
      }
    );
  }

  function handleLoadMore() {
    setPage((p) => p + 1);
  }

  // ── Render states ──────────────────────────────────────────────────────────

  const showSkeleton = isLoading && page === 1;
  const showError = isError && allOpportunities.length === 0;
  const showEmpty =
    !isLoading && !isError && allOpportunities.length === 0 && page === 1;

  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div className="flex items-center gap-2">
        <Sparkles className="h-5 w-5 text-violet-400" />
        <h1 className="text-xl font-semibold text-foreground">Opportunities</h1>
        <span className="text-sm text-muted-foreground">
          — AI-predicted hiring needs
        </span>
      </div>

      {/* Filters */}
      <OpportunityFilters
        filters={filters}
        onChange={handleFiltersChange}
        total={displayCount}
      />

      {/* ── Skeleton loading ───────────────────────────────────────── */}
      {showSkeleton && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      )}

      {/* ── Error state ────────────────────────────────────────────── */}
      {showError && (
        <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
          <AlertCircle className="h-10 w-10 text-red-400" />
          <div>
            <p className="text-base font-medium text-foreground">
              Failed to load opportunities
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Check your connection and try again.
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="gap-1.5"
          >
            <RefreshCw className="h-4 w-4" />
            Retry
          </Button>
        </div>
      )}

      {/* ── Empty state ────────────────────────────────────────────── */}
      {showEmpty && (
        <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
          <Inbox className="h-10 w-10 text-muted-foreground" />
          <div>
            <p className="text-base font-medium text-foreground">
              No opportunities found
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Signals are being processed — check back soon, or adjust your
              filters.
            </p>
          </div>
          {(filters.confidence.length > 0 ||
            filters.status.length > 0 ||
            filters.timeline_max_weeks !== null) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => handleFiltersChange(DEFAULT_FILTERS)}
            >
              Clear filters
            </Button>
          )}
        </div>
      )}

      {/* ── Opportunity grid ───────────────────────────────────────── */}
      {allOpportunities.length > 0 && (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {allOpportunities.map((opp) => (
              <OpportunityCard key={opp.id} opportunity={opp} onClick={handleCardClick} />
            ))}
          </div>

          {/* Load more */}
          {hasMore && (
            <div className="flex justify-center pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleLoadMore}
                disabled={isLoading}
                className="gap-1.5"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    Loading…
                  </>
                ) : (
                  `Load more (${totalFromApi - totalLoaded} remaining)`
                )}
              </Button>
            </div>
          )}
        </>
      )}

      {/* ── Opportunity detail dialog ──────────────────────────────── */}
      <OpportunityDetail
        opportunity={selectedOpp}
        onClose={handleDetailClose}
        onRefresh={handleRefresh}
        isRefreshing={refreshMutation.isPending}
        onCreateAction={handleCreateAction}
        isCreatingAction={createActionMutation.isPending}
      />
    </div>
  );
}
