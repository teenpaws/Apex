'use client';

import { useEffect, useState } from 'react';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Loader2, CheckCircle2, XCircle, Clock } from 'lucide-react';

type Stage = 'QUEUED' | 'INGEST' | 'CLASSIFY' | 'PREDICT' | 'FIT_SCORE' | 'ACTIONS' | 'DONE';

interface PipelineStatus {
  run_id: string;
  status: string;
  stage: Stage;
  completed: number;
  total: number;
  progress: number;
  eta_seconds: number | null;
  error_message: string | null;
}

const STAGE_LABELS: Record<Stage, string> = {
  QUEUED:    'Queued',
  INGEST:    'Ingesting Signals',
  CLASSIFY:  'Classifying',
  PREDICT:   'Predicting Opportunities',
  FIT_SCORE: 'Scoring Fit',
  ACTIONS:   'Generating Actions',
  DONE:      'Complete',
};

const STAGE_ORDER: Stage[] = ['INGEST', 'CLASSIFY', 'PREDICT', 'FIT_SCORE', 'ACTIONS', 'DONE'];

interface PipelineProgressBarProps {
  runId: string;
  onComplete?: () => void;
  onError?: (msg: string) => void;
}

export function PipelineProgressBar({ runId, onComplete, onError }: PipelineProgressBarProps) {
  const [status, setStatus] = useState<PipelineStatus | null>(null);
  const [polling, setPolling] = useState(true);

  useEffect(() => {
    if (!polling) return;
    const poll = async () => {
      try {
        const res = await fetch(`/api/v1/agents/run-status/${runId}`, { credentials: 'include' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: PipelineStatus = await res.json();
        setStatus(data);
        if (data.status === 'SUCCESS' || data.stage === 'DONE') {
          setPolling(false);
          onComplete?.();
        } else if (data.status === 'FAILED') {
          setPolling(false);
          onError?.(data.error_message ?? 'Pipeline failed');
        }
      } catch { /* keep polling on network errors */ }
    };
    poll();
    const interval = setInterval(poll, 2000);
    return () => clearInterval(interval);
  }, [runId, polling, onComplete, onError]);

  if (!status) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Starting pipeline...
      </div>
    );
  }

  const isDone = status.stage === 'DONE' || status.status === 'SUCCESS';
  const isFailed = status.status === 'FAILED';

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isFailed ? (
            <XCircle className="h-4 w-4 text-red-400" />
          ) : isDone ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          ) : (
            <Loader2 className="h-4 w-4 animate-spin text-violet-400" />
          )}
          <span className="text-sm font-medium">
            {isFailed ? 'Pipeline Failed' : isDone ? 'Pipeline Complete' : (STAGE_LABELS[status.stage] ?? status.stage)}
          </span>
        </div>
        {status.eta_seconds != null && !isDone && !isFailed && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            ~{Math.ceil(status.eta_seconds / 60)}m remaining
          </div>
        )}
      </div>
      <Progress value={status.progress} className="h-2" />
      <div className="flex flex-wrap gap-1.5">
        {STAGE_ORDER.map((stage) => {
          const currentIdx = STAGE_ORDER.indexOf(status.stage as Stage);
          const stageIdx = STAGE_ORDER.indexOf(stage);
          const isComplete = stageIdx < currentIdx || isDone;
          const isCurrent = stage === status.stage && !isDone;
          return (
            <Badge key={stage} variant="outline" className={
              isComplete ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs'
              : isCurrent ? 'border-violet-500/30 bg-violet-500/10 text-violet-400 text-xs'
              : 'text-xs text-muted-foreground'
            }>
              {isComplete && '✓ '}{STAGE_LABELS[stage]}
              {isCurrent && status.total > 0 && ` ${status.completed}/${status.total}`}
            </Badge>
          );
        })}
      </div>
      {isFailed && status.error_message && (
        <p className="text-xs text-red-400">{status.error_message}</p>
      )}
    </div>
  );
}
