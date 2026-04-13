'use client';

import Link from 'next/link';
import { ExternalLink, Sparkles } from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useIngestSignals } from '@/hooks/useSignals';
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

interface SignalDetailPanelProps {
  signal: Signal | null;
  onClose: () => void;
}

export function SignalDetailPanel({ signal, onClose }: SignalDetailPanelProps) {
  const ingest = useIngestSignals();

  const relevanceScore = signal?.relevance_score ?? 0;
  const relevancePct = Math.round(relevanceScore * 100);
  const relevanceColor =
    relevanceScore >= 0.7
      ? 'text-emerald-400'
      : relevanceScore >= 0.4
      ? 'text-amber-400'
      : 'text-red-400';
  const relevanceBg =
    relevanceScore >= 0.7
      ? 'bg-emerald-500/10 border-emerald-500/30'
      : relevanceScore >= 0.4
      ? 'bg-amber-500/10 border-amber-500/30'
      : 'bg-red-500/10 border-red-500/30';

  const linkedCount = signal?.linkedOpportunityIds?.length ?? 0;

  return (
    <Sheet open={signal !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
        {signal && (
          <>
            <SheetHeader className="pb-4 border-b border-border">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <Badge
                  variant="outline"
                  className={`text-xs ${signalTypeColor[signal.type] ?? 'bg-muted text-muted-foreground'}`}
                >
                  {signalTypeLabel[signal.type] ?? signal.type}
                </Badge>
                <span className="text-xs text-muted-foreground">
                  {signal.date ?? signal.signal_date}
                </span>
              </div>
              <SheetTitle className="text-base leading-snug">{signal.title}</SheetTitle>
              <SheetDescription className="text-sm">
                {signal.company ?? signal.company_id} · {signal.source}
              </SheetDescription>
            </SheetHeader>

            <div className="p-4 space-y-5">
              {/* Description */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
                  Description
                </p>
                <p className="text-sm text-foreground leading-relaxed">
                  {signal.description}
                </p>
              </div>

              {/* Relevance score */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
                  Relevance Score
                </p>
                <div
                  className={`inline-flex items-center gap-2 rounded-lg border px-3 py-2 ${relevanceBg}`}
                >
                  <span className={`text-2xl font-bold tabular-nums ${relevanceColor}`}>
                    {relevancePct}%
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {relevanceScore >= 0.7
                      ? 'High relevance'
                      : relevanceScore >= 0.4
                      ? 'Medium relevance'
                      : 'Low relevance'}
                  </span>
                </div>
              </div>

              {/* Linked opportunities */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
                  Linked Opportunities
                </p>
                {linkedCount > 0 ? (
                  <Link
                    href="/opportunities"
                    className="flex items-center gap-2 text-sm text-violet-400 hover:text-violet-300 transition-colors"
                  >
                    <Sparkles className="h-4 w-4" />
                    {linkedCount} {linkedCount === 1 ? 'opportunity' : 'opportunities'} predicted
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </Link>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    No opportunities linked yet.
                  </p>
                )}
              </div>

              {/* Source info */}
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
                  Source
                </p>
                <p className="text-sm text-foreground">{signal.source}</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Ingested {signal.processed_at
                    ? new Date(signal.processed_at).toLocaleString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                      })
                    : 'Unknown'}
                </p>
              </div>

              {/* Ingest Now */}
              <div className="pt-2 border-t border-border">
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={() => ingest.mutate()}
                  disabled={ingest.isPending}
                >
                  {ingest.isPending ? 'Ingesting…' : 'Ingest Now'}
                </Button>
                {ingest.isSuccess && (
                  <p className="text-xs text-emerald-400 mt-2 text-center">
                    Ingestion queued — run ID: {ingest.data?.run_id}
                  </p>
                )}
                {ingest.isError && (
                  <p className="text-xs text-red-400 mt-2 text-center">
                    Ingestion failed. Please try again.
                  </p>
                )}
              </div>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
