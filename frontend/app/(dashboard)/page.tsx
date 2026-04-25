'use client';

import Link from 'next/link';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ArrowRight, Sparkles, Clock, User, Play } from 'lucide-react';
import { PipelineViz } from '@/components/shared/PipelineViz';
import { PipelineProgressBar } from '@/components/shared/PipelineProgressBar';
import { SkeletonCard } from '@/components/shared/SkeletonCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { useSignals } from '@/hooks/useSignals';
import { useOpportunities } from '@/hooks/useOpportunities';
import { useActions } from '@/hooks/useActions';
import { useDashboardStats } from '@/hooks/useDashboardStats';
import { usePipelineRun } from '@/hooks/usePipelineRun';

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

const priorityColor: Record<string, string> = {
  HIGH:   'bg-red-500/20 text-red-400 border-red-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  LOW:    'bg-muted text-muted-foreground',
};

const confidenceColor: Record<string, string> = {
  HIGH:        'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  MEDIUM:      'bg-amber-500/20 text-amber-400 border-amber-500/30',
  SPECULATIVE: 'bg-muted text-muted-foreground border-border',
};

export default function DashboardPage() {
  const signalsQuery = useSignals({ per_page: 3 });
  const oppsQuery = useOpportunities({ confidence: 'HIGH', per_page: 3 });
  const actionsQuery = useActions({ status: 'TODO,IN_PROGRESS', per_page: 3 });
  const statsQuery = useDashboardStats();
  const { runId, isRunning, error: pipelineError, startPipeline, handleComplete, handleError } = usePipelineRun();

  const recentSignals = signalsQuery.data?.data ?? [];
  const topOpps = oppsQuery.data?.data ?? [];
  const priorityActions = actionsQuery.data?.data ?? [];

  return (
    <div className="space-y-6">
      {/* Pipeline control */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Market Intelligence Pipeline</h2>
          <p className="text-sm text-muted-foreground">Ingest signals, classify, predict opportunities, and generate actions.</p>
        </div>
        <Button
          onClick={startPipeline}
          disabled={isRunning}
          className="gap-2 bg-violet-600 hover:bg-violet-700"
        >
          {isRunning ? 'Running...' : <><Play className="h-4 w-4" />Run Pipeline</>}
        </Button>
      </div>
      {runId && (
        <PipelineProgressBar
          runId={runId}
          onComplete={() => { handleComplete(); signalsQuery.refetch(); oppsQuery.refetch(); actionsQuery.refetch(); }}
          onError={handleError}
        />
      )}
      {pipelineError && <p className="text-sm text-red-400">{pipelineError}</p>}

      {/* Pipeline Visualization */}
      <PipelineViz stats={statsQuery.data} />

      {/* Top Predicted Opportunities */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-violet-400" />
            <h2 className="text-base font-semibold text-foreground">Top Predicted Opportunities</h2>
          </div>
          <Link
            href="/opportunities"
            className="text-xs text-primary hover:underline flex items-center gap-1"
          >
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {oppsQuery.isLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[1, 2, 3].map((i) => <SkeletonCard key={i} lines={4} />)}
          </div>
        ) : oppsQuery.isError ? (
          <ErrorState
            error={oppsQuery.error as Error}
            onRetry={() => oppsQuery.refetch()}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {topOpps.map((opp) => (
              <Link key={opp.id} href="/opportunities" className="group">
                <Card className="bg-gradient-to-br from-violet-500/10 to-purple-600/5 border-violet-500/20 h-full transition-all duration-200 group-hover:border-violet-400/40 group-hover:shadow-lg group-hover:shadow-violet-500/10">
                  <CardContent className="p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <Badge
                        variant="outline"
                        className={`text-[10px] ${confidenceColor[opp.confidence]}`}
                      >
                        {opp.confidence}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" /> {opp.timeline ?? `${opp.timeline_weeks}w`}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm text-foreground">
                        {opp.role ?? opp.predicted_role}
                      </h3>
                      <p className="text-xs text-muted-foreground">{opp.company}</p>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {opp.whyFit ?? opp.why_fit}
                    </p>
                    <div className="flex items-center gap-1 text-xs text-primary">
                      <User className="h-3 w-3" /> {opp.keyContact}
                    </div>
                    {opp.predictedSalary && (
                      <p className="text-xs font-medium text-emerald-400">{opp.predictedSalary}</p>
                    )}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Signals */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Recent Signals</CardTitle>
              <Link
                href="/signals"
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {signalsQuery.isLoading ? (
              [1, 2, 3].map((i) => <SkeletonCard key={i} lines={2} />)
            ) : signalsQuery.isError ? (
              <ErrorState
                error={signalsQuery.error as Error}
                onRetry={() => signalsQuery.refetch()}
              />
            ) : (
              recentSignals.map((signal) => (
                <Link key={signal.id} href="/signals" className="block group">
                  <div className="flex items-start justify-between gap-3 p-3 rounded-lg bg-muted/50 transition-colors group-hover:bg-muted/80">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm text-foreground">{signal.company}</span>
                        <Badge
                          variant="outline"
                          className={`text-[10px] px-1.5 py-0 ${signalTypeColor[signal.type]}`}
                        >
                          {signalTypeLabel[signal.type] ?? signal.type}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{signal.description}</p>
                      {(signal.linkedOpportunityIds?.length ?? 0) > 0 && (
                        <p className="text-[10px] text-violet-400 mt-1 flex items-center gap-1">
                          <Sparkles className="h-3 w-3" />{' '}
                          {signal.linkedOpportunityIds!.length} opportunity predicted
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                      {signal.date}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>

        {/* Priority Actions */}
        <Card className="bg-card border-border">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Priority Actions</CardTitle>
              <Link
                href="/actions"
                className="text-xs text-primary hover:underline flex items-center gap-1"
              >
                View all <ArrowRight className="h-3 w-3" />
              </Link>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {actionsQuery.isLoading ? (
              [1, 2, 3].map((i) => <SkeletonCard key={i} lines={2} />)
            ) : actionsQuery.isError ? (
              <ErrorState
                error={actionsQuery.error as Error}
                onRetry={() => actionsQuery.refetch()}
              />
            ) : (
              priorityActions.map((action) => (
                <Link key={action.id} href="/actions" className="block group">
                  <div className="flex items-start justify-between gap-3 p-3 rounded-lg bg-muted/50 transition-colors group-hover:bg-muted/80">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground mb-1">{action.title}</p>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className={`text-[10px] px-1.5 py-0 ${priorityColor[action.priority]}`}
                        >
                          {action.priority}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{action.company}</span>
                      </div>
                      {action.sourceSignalId && (
                        <p className="text-[10px] text-blue-400 mt-1">Triggered by signal</p>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                      {action.dueDate}
                    </span>
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
