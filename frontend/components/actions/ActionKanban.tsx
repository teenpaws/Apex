'use client';

import * as React from 'react';
import { ActionCard } from '@/components/actions/ActionCard';
import type { Action } from '@/types';

// ── Column config ─────────────────────────────────────────────────────────────

interface KanbanColumn {
  status: Action['status'];
  label: string;
  headerClass: string;
  emptyLabel: string;
}

const COLUMNS: KanbanColumn[] = [
  {
    status: 'TODO',
    label: 'Todo',
    headerClass: 'text-blue-400 border-b-blue-500/40',
    emptyLabel: 'No actions to do.',
  },
  {
    status: 'IN_PROGRESS',
    label: 'In Progress',
    headerClass: 'text-violet-400 border-b-violet-500/40',
    emptyLabel: 'Nothing in progress.',
  },
  {
    status: 'DONE',
    label: 'Done',
    headerClass: 'text-emerald-400 border-b-emerald-500/40',
    emptyLabel: 'No completed actions yet.',
  },
  {
    status: 'SNOOZED',
    label: 'Snoozed',
    headerClass: 'text-muted-foreground border-b-border',
    emptyLabel: 'No snoozed actions.',
  },
];

// ── Props ─────────────────────────────────────────────────────────────────────

interface ActionKanbanProps {
  actions: Action[];
  onActionClick: (action: Action) => void;
  onStatusChange: (id: string, status: Action['status']) => void;
  updatingId?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ActionKanban({
  actions,
  onActionClick,
  onStatusChange,
  updatingId,
}: ActionKanbanProps) {
  const byStatus = React.useMemo(() => {
    const map: Record<Action['status'], Action[]> = {
      TODO:        [],
      IN_PROGRESS: [],
      DONE:        [],
      SNOOZED:     [],
    };
    for (const action of actions) {
      map[action.status].push(action);
    }
    return map;
  }, [actions]);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {COLUMNS.map((col) => {
        const colActions = byStatus[col.status];
        return (
          <div key={col.status} className="flex flex-col min-h-[300px]">
            {/* Column header */}
            <div
              className={`flex items-center justify-between pb-2 mb-3 border-b ${col.headerClass}`}
            >
              <span className={`text-xs font-semibold uppercase tracking-wider ${col.headerClass.split(' ')[0]}`}>
                {col.label}
              </span>
              <span className="text-xs text-muted-foreground tabular-nums">
                {colActions.length}
              </span>
            </div>

            {/* Cards */}
            <div className="flex flex-col gap-2 flex-1">
              {colActions.length === 0 ? (
                <p className="text-xs text-muted-foreground/50 text-center pt-6">
                  {col.emptyLabel}
                </p>
              ) : (
                colActions.map((action) => (
                  <ActionCard
                    key={action.id}
                    action={action}
                    onClick={onActionClick}
                    onStatusChange={onStatusChange}
                    isUpdating={updatingId === action.id}
                  />
                ))
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
