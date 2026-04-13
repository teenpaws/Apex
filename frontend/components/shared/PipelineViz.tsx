'use client';

import { ArrowRight } from 'lucide-react';
import type { DashboardStats } from '@/types';

const stages = [
  { key: 'signals',       label: 'Signals',       color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  { key: 'opportunities', label: 'Opportunities', color: 'bg-violet-500/20 text-violet-400 border-violet-500/30' },
  { key: 'actions',       label: 'Actions',       color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  { key: 'outreach',      label: 'Outreach',      color: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' },
] as const;

const EMPTY_STAGES: DashboardStats['pipeline_stages'] = {
  signals: 0,
  opportunities: 0,
  actions: 0,
  outreach: 0,
};

interface PipelineVizProps {
  stats?: DashboardStats | null;
}

export function PipelineViz({ stats }: PipelineVizProps) {
  const pipeline_stages = stats?.pipeline_stages ?? EMPTY_STAGES;

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <p className="text-xs text-muted-foreground mb-4 font-medium uppercase tracking-wider">
        Pipeline Overview
      </p>
      <div className="flex items-center gap-2">
        {stages.map((stage, idx) => (
          <div key={stage.key} className="flex items-center gap-2 flex-1">
            <div
              className={`flex-1 rounded-lg border px-4 py-3 text-center ${stage.color}`}
            >
              <p className="text-lg font-bold">
                {pipeline_stages[stage.key]}
              </p>
              <p className="text-[10px] mt-0.5 opacity-80">{stage.label}</p>
            </div>
            {idx < stages.length - 1 && (
              <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
