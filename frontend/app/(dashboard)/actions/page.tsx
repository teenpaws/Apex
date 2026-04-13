'use client';

import * as React from 'react';
import { ListTodo, LayoutGrid, List, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { SkeletonCard } from '@/components/shared/SkeletonCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { ActionKanban } from '@/components/actions/ActionKanban';
import { ActionCard } from '@/components/actions/ActionCard';
import { ActionDetail } from '@/components/actions/ActionDetail';
import { useActions, useUpdateAction, useDraftEmail } from '@/hooks/useActions';
import { cn } from '@/lib/utils';
import type { Action } from '@/types';

// ── Filter state ─────────────────────────────────────────────────────────────

type PriorityFilter = Action['priority'] | 'ALL';
type TypeFilter = Action['type'] | 'ALL';

interface FilterState {
  priority: PriorityFilter;
  type: TypeFilter;
}

const DEFAULT_FILTERS: FilterState = { priority: 'ALL', type: 'ALL' };

// ── Filter chips ──────────────────────────────────────────────────────────────

const PRIORITY_OPTIONS: PriorityFilter[] = ['ALL', 'HIGH', 'MEDIUM', 'LOW'];
const TYPE_OPTIONS: TypeFilter[] = ['ALL', 'OUTREACH', 'FOLLOW_UP', 'RESEARCH', 'CALL'];

const PRIORITY_CLASSES: Partial<Record<PriorityFilter, string>> = {
  HIGH:   'bg-red-500/20 text-red-400 border-red-500/30 hover:bg-red-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30 hover:bg-amber-500/30',
  LOW:    'bg-muted text-muted-foreground border-border hover:bg-muted/60',
};

const TYPE_LABEL: Record<string, string> = {
  ALL:        'All Types',
  OUTREACH:   'Outreach',
  FOLLOW_UP:  'Follow-up',
  RESEARCH:   'Research',
  CALL:       'Call',
};

function chipClass(active: boolean, customActive?: string): string {
  if (active) {
    return customActive
      ? `border text-xs px-2.5 py-1 rounded-full font-medium transition-colors ${customActive}`
      : 'border border-primary/60 bg-primary/10 text-primary text-xs px-2.5 py-1 rounded-full font-medium';
  }
  return 'border border-border text-muted-foreground text-xs px-2.5 py-1 rounded-full font-medium hover:border-border/80 hover:text-foreground transition-colors';
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ActionsPage() {
  const [view, setView] = React.useState<'kanban' | 'list'>('kanban');
  const [filters, setFilters] = React.useState<FilterState>(DEFAULT_FILTERS);
  const [selectedAction, setSelectedAction] = React.useState<Action | null>(null);
  const [draftRunId, setDraftRunId] = React.useState<string | null>(null);
  const [updatingId, setUpdatingId] = React.useState<string | undefined>(undefined);

  const actionsQuery = useActions({ per_page: 100 });
  const updateAction = useUpdateAction();
  const draftEmail = useDraftEmail();

  // Client-side filtering
  const filteredActions = React.useMemo(() => {
    const items = actionsQuery.data?.data ?? [];
    return items.filter((a) => {
      if (filters.priority !== 'ALL' && a.priority !== filters.priority) return false;
      if (filters.type !== 'ALL' && a.type !== filters.type) return false;
      return true;
    });
  }, [actionsQuery.data, filters]);

  // Status change handler
  const handleStatusChange = React.useCallback(
    (id: string, status: Action['status']) => {
      setUpdatingId(id);
      updateAction.mutate(
        { id, data: { status } },
        {
          onSettled: () => setUpdatingId(undefined),
          onSuccess: (updated) => {
            // Keep detail panel in sync
            setSelectedAction((prev) => (prev?.id === id ? updated : prev));
          },
        }
      );
    },
    [updateAction]
  );

  // Draft email handler
  const handleDraftEmail = React.useCallback(
    (actionId: string) => {
      setDraftRunId(null);
      draftEmail.mutate(actionId, {
        onSuccess: (run) => {
          setDraftRunId(run.run_id);
        },
      });
    },
    [draftEmail]
  );

  const hasActiveFilters =
    filters.priority !== 'ALL' || filters.type !== 'ALL';

  return (
    <div className="space-y-5">
      {/* ── Page header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <ListTodo className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold text-foreground">Actions</h1>
          {!actionsQuery.isLoading && (
            <span className="text-xs text-muted-foreground ml-1">
              ({filteredActions.length}
              {actionsQuery.data && actionsQuery.data.total !== filteredActions.length
                ? ` of ${actionsQuery.data.total}`
                : ''}
              )
            </span>
          )}
        </div>

        {/* View toggle */}
        <div className="flex items-center gap-1 rounded-lg border border-border p-0.5 bg-muted/30">
          <button
            type="button"
            onClick={() => setView('kanban')}
            className={cn(
              'flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md transition-colors',
              view === 'kanban'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <LayoutGrid className="h-3.5 w-3.5" />
            Board
          </button>
          <button
            type="button"
            onClick={() => setView('list')}
            className={cn(
              'flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-md transition-colors',
              view === 'list'
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <List className="h-3.5 w-3.5" />
            List
          </button>
        </div>
      </div>

      {/* ── Draft email toast ────────────────────────────────────────── */}
      {draftRunId && (
        <div className="flex items-center justify-between text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">
          <span>Email draft queued — run ID: {draftRunId}. Check Outreach shortly.</span>
          <button
            type="button"
            onClick={() => setDraftRunId(null)}
            className="text-emerald-400/60 hover:text-emerald-400 ml-3 shrink-0"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
      {draftEmail.isError && (
        <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          Failed to queue email draft. Please try again.
        </div>
      )}

      {/* ── Filters ──────────────────────────────────────────────────── */}
      <div className="space-y-2">
        {/* Priority chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground font-medium w-14 shrink-0">Priority</span>
          {PRIORITY_OPTIONS.map((p) => (
            <button
              key={p}
              type="button"
              onClick={() => setFilters((f) => ({ ...f, priority: p }))}
              className={
                p === 'ALL'
                  ? chipClass(filters.priority === 'ALL')
                  : chipClass(
                      filters.priority === p,
                      filters.priority === p ? PRIORITY_CLASSES[p] : undefined
                    )
              }
            >
              {p === 'ALL' ? 'All Priorities' : p}
            </button>
          ))}
        </div>

        {/* Type chips */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-muted-foreground font-medium w-14 shrink-0">Type</span>
          {TYPE_OPTIONS.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilters((f) => ({ ...f, type: t }))}
              className={chipClass(filters.type === t)}
            >
              {TYPE_LABEL[t]}
            </button>
          ))}
        </div>

        {/* Clear filters */}
        {hasActiveFilters && (
          <div className="pt-0.5">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setFilters(DEFAULT_FILTERS)}
              className="text-xs h-7 px-2 text-muted-foreground"
            >
              Clear filters
            </Button>
          </div>
        )}
      </div>

      {/* ── Main content ─────────────────────────────────────────────── */}
      {actionsQuery.isLoading ? (
        <div
          className={
            view === 'kanban'
              ? 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4'
              : 'space-y-3'
          }
        >
          {Array.from({ length: view === 'kanban' ? 8 : 5 }).map((_, i) => (
            <SkeletonCard key={i} lines={3} />
          ))}
        </div>
      ) : actionsQuery.isError ? (
        <ErrorState
          error={actionsQuery.error as Error}
          onRetry={() => actionsQuery.refetch()}
        />
      ) : filteredActions.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-card p-12 text-center">
          <ListTodo className="h-8 w-8 text-muted-foreground/40" />
          <p className="text-sm font-medium text-foreground">
            {hasActiveFilters ? 'No actions match your filters' : 'No actions yet'}
          </p>
          <p className="text-xs text-muted-foreground">
            {hasActiveFilters
              ? 'Try adjusting the filters.'
              : 'Actions are generated automatically when opportunities are predicted.'}
          </p>
          {hasActiveFilters && (
            <Button variant="ghost" size="sm" onClick={() => setFilters(DEFAULT_FILTERS)}>
              Clear filters
            </Button>
          )}
        </div>
      ) : view === 'kanban' ? (
        <ActionKanban
          actions={filteredActions}
          onActionClick={setSelectedAction}
          onStatusChange={handleStatusChange}
          updatingId={updatingId}
        />
      ) : (
        /* List view */
        <div className="space-y-2">
          {filteredActions.map((action) => (
            <ActionCard
              key={action.id}
              action={action}
              onClick={setSelectedAction}
              onStatusChange={handleStatusChange}
              isUpdating={updatingId === action.id}
            />
          ))}
        </div>
      )}

      {/* ── Detail panel ─────────────────────────────────────────────── */}
      <ActionDetail
        action={selectedAction}
        onClose={() => setSelectedAction(null)}
        onStatusChange={handleStatusChange}
        onDraftEmail={handleDraftEmail}
        isDrafting={draftEmail.isPending}
      />
    </div>
  );
}
