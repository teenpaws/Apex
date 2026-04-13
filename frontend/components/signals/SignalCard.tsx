'use client';

import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import type { Signal } from '@/types';

const signalTypeColor: Record<string, string> = {
  FUNDING:             'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  EXEC_HIRE:           'bg-blue-500/20 text-blue-400 border-blue-500/30',
  EXPANSION:           'bg-violet-500/20 text-violet-400 border-violet-500/30',
  JOB_POSTING_PATTERN: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  LAYOFF:              'bg-red-500/20 text-red-400 border-red-500/30',
  MA:                  'bg-pink-500/20 text-pink-400 border-pink-500/30',
  CONTRACT:            'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
  EARNINGS:            'bg-orange-500/20 text-orange-400 border-orange-500/30',
};

const signalTypeLabel: Record<string, string> = {
  FUNDING:             'Funding',
  EXEC_HIRE:           'Exec Hire',
  EXPANSION:           'Expansion',
  JOB_POSTING_PATTERN: 'Job Posting Pattern',
  LAYOFF:              'Layoff',
  MA:                  'M&A',
  CONTRACT:            'Contract',
  EARNINGS:            'Earnings',
};

interface SignalCardProps {
  signal: Signal;
  onClick: (signal: Signal) => void;
  isSelected?: boolean;
}

export function SignalCard({ signal, onClick, isSelected = false }: SignalCardProps) {
  const relevancePct = Math.round(signal.relevance_score * 100);
  const relevanceColor =
    signal.relevance_score >= 0.7
      ? 'text-emerald-400'
      : signal.relevance_score >= 0.4
      ? 'text-amber-400'
      : 'text-red-400';

  return (
    <button
      type="button"
      onClick={() => onClick(signal)}
      className={cn(
        'w-full text-left p-4 rounded-xl border bg-card transition-all duration-150',
        'hover:border-primary/40 hover:shadow-sm hover:bg-muted/30',
        isSelected
          ? 'border-primary/60 bg-primary/5 shadow-sm shadow-primary/10'
          : 'border-border'
      )}
    >
      <div className="flex items-start justify-between gap-3">
        {/* Left: company + badge + title + description */}
        <div className="flex-1 min-w-0 space-y-1.5">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-sm text-foreground truncate">
              {signal.company ?? signal.company_id}
            </span>
            <Badge
              variant="outline"
              className={`text-[10px] px-1.5 py-0 ${signalTypeColor[signal.type] ?? 'bg-muted text-muted-foreground'}`}
            >
              {signalTypeLabel[signal.type] ?? signal.type}
            </Badge>
          </div>
          <p className="text-sm font-medium text-foreground line-clamp-1">
            {signal.title}
          </p>
          <p className="text-xs text-muted-foreground line-clamp-2">
            {signal.description}
          </p>
        </div>

        {/* Right: date + relevance */}
        <div className="flex-shrink-0 flex flex-col items-end gap-1.5">
          <span className="text-[10px] text-muted-foreground whitespace-nowrap">
            {signal.date ?? signal.signal_date}
          </span>
          <span className={`text-xs font-medium tabular-nums ${relevanceColor}`}>
            {relevancePct}%
          </span>
        </div>
      </div>
    </button>
  );
}
