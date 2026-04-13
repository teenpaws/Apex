'use client';

import * as React from 'react';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Progress,
  ProgressTrack,
  ProgressIndicator,
} from '@/components/ui/progress';
import {
  Clock,
  DollarSign,
  Lightbulb,
  RefreshCw,
  Zap,
  Radio,
  ExternalLink,
} from 'lucide-react';
import Link from 'next/link';
import type { Opportunity } from '@/types';

// ── Colour maps ──────────────────────────────────────────────────────────────

const CONFIDENCE_CLASSES: Record<Opportunity['confidence'], string> = {
  HIGH: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  SPECULATIVE: 'bg-muted text-muted-foreground border-border',
};

const STATUS_CLASSES: Record<Opportunity['status'], string> = {
  PREDICTED: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  APPROACHED: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
  INTERVIEWING: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  CLOSED: 'bg-muted text-muted-foreground border-border',
};

function fitScoreColor(score: number): string {
  if (score >= 70) return 'text-emerald-400';
  if (score >= 50) return 'text-amber-400';
  return 'text-red-400';
}

function fitScoreIndicatorClass(score: number): string {
  if (score >= 70) return 'bg-emerald-500';
  if (score >= 50) return 'bg-amber-500';
  return 'bg-red-500';
}

function fitScoreLabel(score: number): string {
  if (score >= 70) return 'Strong fit';
  if (score >= 50) return 'Moderate fit';
  return 'Weak fit';
}

// ── Component ────────────────────────────────────────────────────────────────

interface OpportunityDetailProps {
  opportunity: Opportunity | null;
  onClose: () => void;
  onRefresh: (id: string) => void;
  isRefreshing?: boolean;
  onCreateAction?: (opportunityId: string) => void;
  isCreatingAction?: boolean;
}

export function OpportunityDetail({
  opportunity: opp,
  onClose,
  onRefresh,
  isRefreshing = false,
  onCreateAction,
  isCreatingAction = false,
}: OpportunityDetailProps) {
  if (!opp) {
    return null;
  }

  const displayRole = opp.role ?? opp.predicted_role;
  const displayCompany = opp.company ?? opp.company_id;
  const displayTimeline = opp.timeline ?? (opp.timeline_weeks != null ? `${opp.timeline_weeks}w` : null);
  const displayWhyFit = opp.whyFit ?? opp.why_fit;
  const displaySalary = opp.predictedSalary ?? opp.predicted_salary_range;
  const signalCount = opp.signal_ids?.length ?? 0;

  return (
    <Dialog open={true} onOpenChange={(open) => !open && onClose()}>
      <DialogContent
        className="sm:max-w-2xl max-h-[90vh] overflow-y-auto"
        showCloseButton
      >
        {/* ── Header ────────────────────────────────────────────────── */}
        <DialogHeader>
          <div className="flex flex-wrap items-start gap-2 pr-8">
            <Badge
              variant="outline"
              className={`text-[10px] ${CONFIDENCE_CLASSES[opp.confidence]}`}
            >
              {opp.confidence}
            </Badge>
            <Badge
              variant="outline"
              className={`text-[10px] ${STATUS_CLASSES[opp.status]}`}
            >
              {opp.status}
            </Badge>
          </div>
          <DialogTitle className="text-lg font-semibold leading-snug">
            {displayRole}
          </DialogTitle>
          {displayCompany && (
            <DialogDescription className="text-sm text-muted-foreground">
              {displayCompany}
            </DialogDescription>
          )}
        </DialogHeader>

        {/* ── Body ──────────────────────────────────────────────────── */}
        <div className="space-y-5 mt-1">
          {/* Fit Score */}
          <section className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                Career Fit Score
              </span>
              <span className="text-xs text-muted-foreground">
                {fitScoreLabel(opp.fit_score)}
              </span>
            </div>
            <div className="flex items-end gap-3">
              <span
                className={`text-4xl font-bold tabular-nums ${fitScoreColor(opp.fit_score)}`}
              >
                {Math.round(opp.fit_score)}
              </span>
              <span className="text-xl text-muted-foreground mb-1">/100</span>
            </div>
            <Progress value={opp.fit_score} className="gap-0">
              <ProgressTrack className="h-2">
                <ProgressIndicator
                  className={fitScoreIndicatorClass(opp.fit_score)}
                />
              </ProgressTrack>
            </Progress>
          </section>

          {/* Why This Fits */}
          {displayWhyFit && (
            <section className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wide">
                  Why This Fits You
                </h4>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {displayWhyFit}
              </p>
            </section>
          )}

          {/* Positioning Notes */}
          {opp.positioning_notes && (
            <section className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Zap className="h-3.5 w-3.5 text-violet-400" />
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wide">
                  Positioning Notes
                </h4>
              </div>
              <p className="text-sm text-muted-foreground leading-relaxed">
                {opp.positioning_notes}
              </p>
            </section>
          )}

          {/* Timeline + Salary row */}
          <div className="grid grid-cols-2 gap-4">
            {displayTimeline && (
              <section className="rounded-lg border border-border bg-muted/30 p-3 space-y-1">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <Clock className="h-3.5 w-3.5" />
                  <span className="text-[10px] uppercase tracking-wide font-medium">
                    Timeline
                  </span>
                </div>
                <p className="text-sm font-semibold text-foreground">
                  {displayTimeline} out
                </p>
              </section>
            )}

            {displaySalary && (
              <section className="rounded-lg border border-border bg-muted/30 p-3 space-y-1">
                <div className="flex items-center gap-1.5 text-muted-foreground">
                  <DollarSign className="h-3.5 w-3.5" />
                  <span className="text-[10px] uppercase tracking-wide font-medium">
                    Predicted Salary
                  </span>
                </div>
                <p className="text-sm font-semibold text-emerald-400">
                  {displaySalary}
                </p>
              </section>
            )}
          </div>

          {/* Source signals */}
          {signalCount > 0 && (
            <section className="space-y-1.5">
              <div className="flex items-center gap-1.5">
                <Radio className="h-3.5 w-3.5 text-blue-400" />
                <h4 className="text-xs font-semibold text-foreground uppercase tracking-wide">
                  Source Signals
                </h4>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  Based on{' '}
                  <span className="text-foreground font-medium">
                    {signalCount}
                  </span>{' '}
                  {signalCount === 1 ? 'signal' : 'signals'}
                </span>
                <Link
                  href="/signals"
                  className="inline-flex items-center gap-0.5 text-xs text-primary hover:underline"
                >
                  View signals
                  <ExternalLink className="h-3 w-3" />
                </Link>
              </div>
            </section>
          )}
        </div>

        {/* ── Footer / Action buttons ────────────────────────────────── */}
        <DialogFooter className="mt-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => onRefresh(opp.id)}
            disabled={isRefreshing}
            className="gap-1.5"
          >
            <RefreshCw
              className={['h-3.5 w-3.5', isRefreshing ? 'animate-spin' : ''].join(' ')}
            />
            {isRefreshing ? 'Refreshing…' : 'Refresh Analysis'}
          </Button>

          {onCreateAction && (
            <Button
              size="sm"
              onClick={() => onCreateAction(opp.id)}
              disabled={isCreatingAction}
              className="gap-1.5"
            >
              <Zap className="h-3.5 w-3.5" />
              {isCreatingAction ? 'Creating…' : 'Create Action'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
