'use client';

import * as React from 'react';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import {
  Progress,
  ProgressTrack,
  ProgressIndicator,
} from '@/components/ui/progress';
import { Clock, User } from 'lucide-react';
import type { Opportunity } from '@/types';

// ── Design-system colour maps ────────────────────────────────────────────────

const CONFIDENCE_CLASSES: Record<Opportunity['confidence'], string> = {
  HIGH: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  SPECULATIVE: 'bg-muted text-muted-foreground border-border',
};

// Fit score colour: green ≥70, amber 50-69, red <50
function fitScoreIndicatorClass(score: number): string {
  if (score >= 70) return 'bg-emerald-500';
  if (score >= 50) return 'bg-amber-500';
  return 'bg-red-500';
}

// ── Component ────────────────────────────────────────────────────────────────

interface OpportunityCardProps {
  opportunity: Opportunity;
  onClick: (opp: Opportunity) => void;
}

export function OpportunityCard({ opportunity: opp, onClick }: OpportunityCardProps) {
  const displayRole = opp.role ?? opp.predicted_role;
  const displayTimeline = opp.timeline ?? (opp.timeline_weeks != null ? `${opp.timeline_weeks}w` : null);
  const displayWhyFit = opp.whyFit ?? opp.why_fit;
  const displayCompany = opp.company ?? opp.company_id;
  const displayContact = opp.keyContact;

  return (
    <Card
      role="button"
      tabIndex={0}
      onClick={() => onClick(opp)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick(opp);
        }
      }}
      className={[
        'bg-gradient-to-br from-violet-500/10 to-purple-600/5 border-violet-500/20',
        'cursor-pointer transition-all duration-200',
        'hover:border-violet-400/40 hover:shadow-lg hover:shadow-violet-500/10',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-400/60',
      ].join(' ')}
    >
      <CardContent className="p-5 space-y-3">
        {/* Top row: confidence badge + timeline */}
        <div className="flex items-center justify-between">
          <Badge
            variant="outline"
            className={`text-[10px] ${CONFIDENCE_CLASSES[opp.confidence]}`}
          >
            {opp.confidence}
          </Badge>
          {displayTimeline && (
            <span className="text-[10px] text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {displayTimeline}
            </span>
          )}
        </div>

        {/* Role + company */}
        <div>
          <h3 className="font-semibold text-sm text-foreground leading-snug">
            {displayRole}
          </h3>
          {displayCompany && (
            <p className="text-xs text-muted-foreground mt-0.5">{displayCompany}</p>
          )}
        </div>

        {/* Fit score */}
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <span className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Fit Score
            </span>
            <span
              className={[
                'text-xs font-semibold tabular-nums',
                opp.fit_score >= 70
                  ? 'text-emerald-400'
                  : opp.fit_score >= 50
                  ? 'text-amber-400'
                  : 'text-red-400',
              ].join(' ')}
            >
              {Math.round(opp.fit_score)}
            </span>
          </div>
          <Progress value={opp.fit_score} className="gap-0">
            <ProgressTrack className="h-1.5">
              <ProgressIndicator
                className={fitScoreIndicatorClass(opp.fit_score)}
              />
            </ProgressTrack>
          </Progress>
        </div>

        {/* Why fit — 2-line clamp */}
        {displayWhyFit && (
          <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
            {displayWhyFit}
          </p>
        )}

        {/* Key contact */}
        {displayContact && (
          <div className="flex items-center gap-1 text-xs text-primary">
            <User className="h-3 w-3 shrink-0" />
            <span className="truncate">{displayContact}</span>
          </div>
        )}

        {/* Predicted salary */}
        {(opp.predictedSalary ?? opp.predicted_salary_range) && (
          <p className="text-xs font-medium text-emerald-400">
            {opp.predictedSalary ?? opp.predicted_salary_range}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
