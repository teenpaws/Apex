'use client';

import * as React from 'react';
import { Mail, RefreshCw, Search, Phone, Calendar, Building2 } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Action } from '@/types';

// ── Colour maps ───────────────────────────────────────────────────────────────

const PRIORITY_CLASSES: Record<Action['priority'], string> = {
  HIGH:   'bg-red-500/20 text-red-400 border-red-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  LOW:    'bg-muted text-muted-foreground border-border',
};

const STATUS_CLASSES: Record<Action['status'], string> = {
  TODO:        'bg-blue-500/20 text-blue-400 border-blue-500/30',
  IN_PROGRESS: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  DONE:        'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  SNOOZED:     'bg-muted text-muted-foreground border-border',
};

const STATUS_LABEL: Record<Action['status'], string> = {
  TODO:        'Todo',
  IN_PROGRESS: 'In Progress',
  DONE:        'Done',
  SNOOZED:     'Snoozed',
};

const TYPE_ICON: Record<Action['type'], React.ReactNode> = {
  OUTREACH:   <Mail className="h-3.5 w-3.5" />,
  FOLLOW_UP:  <RefreshCw className="h-3.5 w-3.5" />,
  RESEARCH:   <Search className="h-3.5 w-3.5" />,
  CALL:       <Phone className="h-3.5 w-3.5" />,
};

const TYPE_COLOR: Record<Action['type'], string> = {
  OUTREACH:   'text-blue-400',
  FOLLOW_UP:  'text-violet-400',
  RESEARCH:   'text-amber-400',
  CALL:       'text-emerald-400',
};

// ── Status transition map ─────────────────────────────────────────────────────

const NEXT_STATUSES: Record<Action['status'], Action['status'][]> = {
  TODO:        ['IN_PROGRESS', 'SNOOZED'],
  IN_PROGRESS: ['DONE', 'TODO', 'SNOOZED'],
  DONE:        ['TODO'],
  SNOOZED:     ['TODO', 'IN_PROGRESS'],
};

// ── Props ─────────────────────────────────────────────────────────────────────

interface ActionCardProps {
  action: Action;
  onClick: (action: Action) => void;
  onStatusChange: (id: string, status: Action['status']) => void;
  isUpdating?: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ActionCard({
  action,
  onClick,
  onStatusChange,
  isUpdating = false,
}: ActionCardProps) {
  const displayDue = action.dueDate ?? action.due_date;
  const displayCompany = action.company ?? action.company_id;
  const isDue = React.useMemo(() => {
    try {
      return new Date(action.due_date) < new Date();
    } catch {
      return false;
    }
  }, [action.due_date]);

  const nextStatus = NEXT_STATUSES[action.status][0];

  return (
    <div
      className={cn(
        'rounded-xl border bg-card transition-all duration-150',
        'hover:border-primary/30 hover:shadow-sm',
        action.status === 'DONE' ? 'opacity-60 border-border' : 'border-border',
        isUpdating && 'opacity-50 pointer-events-none'
      )}
    >
      {/* Clickable body */}
      <button
        type="button"
        onClick={() => onClick(action)}
        className="w-full text-left p-4 space-y-2.5"
      >
        {/* Top row: type icon + title */}
        <div className="flex items-start gap-2.5">
          <span className={cn('mt-0.5 shrink-0', TYPE_COLOR[action.type])}>
            {TYPE_ICON[action.type]}
          </span>
          <p
            className={cn(
              'text-sm font-medium text-foreground leading-snug line-clamp-2',
              action.status === 'DONE' && 'line-through text-muted-foreground'
            )}
          >
            {action.title}
          </p>
        </div>

        {/* Badges row */}
        <div className="flex items-center gap-1.5 flex-wrap pl-6">
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 ${PRIORITY_CLASSES[action.priority]}`}
          >
            {action.priority}
          </Badge>
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 ${STATUS_CLASSES[action.status]}`}
          >
            {STATUS_LABEL[action.status]}
          </Badge>
        </div>

        {/* Footer: company + due date */}
        <div className="flex items-center justify-between gap-2 pl-6">
          {displayCompany && (
            <span className="flex items-center gap-1 text-[11px] text-muted-foreground truncate">
              <Building2 className="h-3 w-3 shrink-0" />
              {displayCompany}
            </span>
          )}
          {displayDue && (
            <span
              className={cn(
                'flex items-center gap-1 text-[11px] whitespace-nowrap shrink-0',
                isDue && action.status !== 'DONE'
                  ? 'text-red-400'
                  : 'text-muted-foreground'
              )}
            >
              <Calendar className="h-3 w-3" />
              {displayDue}
            </span>
          )}
        </div>
      </button>

      {/* Quick-move button */}
      {action.status !== 'DONE' && (
        <div className="border-t border-border/60 px-4 py-2 flex justify-end">
          <button
            type="button"
            onClick={() => onStatusChange(action.id, nextStatus)}
            disabled={isUpdating}
            className={cn(
              'text-[11px] font-medium px-2.5 py-1 rounded-md border transition-colors',
              'hover:bg-muted/40',
              STATUS_CLASSES[nextStatus]
            )}
          >
            → {STATUS_LABEL[nextStatus]}
          </button>
        </div>
      )}
    </div>
  );
}
