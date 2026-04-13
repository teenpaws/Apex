'use client';

import { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingUp, Zap, CheckSquare, DollarSign, Activity } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { SkeletonCard } from '@/components/shared/SkeletonCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { analyticsApi, agentsApi } from '@/lib/api/client';
import type { DashboardStats, AgentRun } from '@/types';

// ── Mock fallback data ─────────────────────────────────────────────────────────

const MOCK_SIGNAL_VELOCITY = Array.from({ length: 30 }, (_, i) => {
  const d = new Date();
  d.setDate(d.getDate() - (29 - i));
  return {
    date: d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
    FUNDING: Math.floor(Math.random() * 4),
    EXEC_HIRE: Math.floor(Math.random() * 5),
    EXPANSION: Math.floor(Math.random() * 3),
    JOB_POSTING_PATTERN: Math.floor(Math.random() * 6),
  };
});

const MOCK_COMPANY_SIGNALS = [
  { company: 'Stripe', signals: 14 },
  { company: 'Mistral AI', signals: 11 },
  { company: 'Revolut', signals: 9 },
  { company: 'N26', signals: 8 },
  { company: 'Klarna', signals: 7 },
  { company: 'Alan', signals: 6 },
  { company: 'Doctolib', signals: 5 },
  { company: 'Contentsquare', signals: 4 },
  { company: 'Back Market', signals: 3 },
  { company: 'PayFit', signals: 2 },
];

// ── Hooks ──────────────────────────────────────────────────────────────────────

function useDashboardStats() {
  return useQuery({
    queryKey: ['analytics', 'dashboard'],
    queryFn: async () => {
      const res = await analyticsApi.dashboard();
      return res.data as DashboardStats;
    },
  });
}

function useAgentRuns() {
  return useQuery({
    queryKey: ['agents', 'runs'],
    queryFn: async () => {
      const res = await agentsApi.runs();
      return res.data as AgentRun[];
    },
  });
}

// ── Stat card ──────────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  accent?: string;
}

function StatCard({ label, value, icon, accent = 'text-primary' }: StatCardProps) {
  return (
    <Card className="p-5 flex items-center gap-4 bg-card border-border">
      <div className={`rounded-lg bg-muted p-2.5 ${accent}`}>{icon}</div>
      <div>
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold text-foreground">{value}</p>
      </div>
    </Card>
  );
}

// ── Pipeline funnel ────────────────────────────────────────────────────────────

function PipelineFunnel({ stages }: { stages: DashboardStats['pipeline_stages'] }) {
  const steps = [
    { label: 'Signals', value: stages.signals, color: 'bg-violet-500' },
    { label: 'Opportunities', value: stages.opportunities, color: 'bg-blue-500' },
    { label: 'Actions', value: stages.actions, color: 'bg-amber-500' },
    { label: 'Outreach', value: stages.outreach, color: 'bg-emerald-500' },
  ];
  const max = steps[0].value || 1;

  return (
    <div className="space-y-3">
      {steps.map((step, i) => {
        const pct = Math.round((step.value / max) * 100);
        const convPct =
          i > 0 && steps[i - 1].value > 0
            ? Math.round((step.value / steps[i - 1].value) * 100)
            : null;
        return (
          <div key={step.label} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground font-medium">{step.label}</span>
              <span className="text-foreground font-semibold">
                {step.value}
                {convPct !== null && (
                  <span className="ml-2 text-muted-foreground font-normal">
                    ({convPct}% of prev)
                  </span>
                )}
              </span>
            </div>
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div
                className={`h-full rounded-full ${step.color} transition-all duration-500`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── Agent cost table ───────────────────────────────────────────────────────────

interface AgentCostRow {
  agent_name: string;
  calls: number;
  total_tokens: number;
  cost_usd: number;
}

function buildCostRows(runs: AgentRun[]): AgentCostRow[] {
  const map = new Map<string, AgentCostRow>();
  for (const run of runs) {
    const existing = map.get(run.agent_name);
    if (existing) {
      existing.calls += 1;
      existing.total_tokens += run.tokens_in + run.tokens_out;
      existing.cost_usd += run.cost_usd;
    } else {
      map.set(run.agent_name, {
        agent_name: run.agent_name,
        calls: 1,
        total_tokens: run.tokens_in + run.tokens_out,
        cost_usd: run.cost_usd,
      });
    }
  }
  return Array.from(map.values()).sort((a, b) => b.cost_usd - a.cost_usd);
}

// ── Chart tooltip style ────────────────────────────────────────────────────────

const CHART_TOOLTIP_STYLE = {
  contentStyle: {
    backgroundColor: 'hsl(var(--card))',
    border: '1px solid hsl(var(--border))',
    borderRadius: '8px',
    fontSize: '12px',
    color: 'hsl(var(--foreground))',
  },
  labelStyle: { color: 'hsl(var(--muted-foreground))' },
};

const AXIS_TICK_STYLE = { fill: 'hsl(var(--muted-foreground))', fontSize: 11 };

// ── Main page ──────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const statsQuery = useDashboardStats();
  const runsQuery = useAgentRuns();

  const stats = statsQuery.data;
  const runs: AgentRun[] = runsQuery.data ?? [];
  const costRows = useMemo(() => buildCostRows(runs), [runs]);

  const totalCostThisMonth = useMemo(() => {
    const cutoff = new Date();
    cutoff.setDate(1);
    cutoff.setHours(0, 0, 0, 0);
    return runs
      .filter((r) => new Date(r.created_at) >= cutoff)
      .reduce((sum, r) => sum + r.cost_usd, 0);
  }, [runs]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Activity className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold text-foreground">Analytics</h1>
      </div>

      {/* Stat cards row */}
      {statsQuery.isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <SkeletonCard key={i} lines={1} />)}
        </div>
      ) : statsQuery.isError ? (
        <ErrorState error={statsQuery.error as Error} onRetry={() => statsQuery.refetch()} />
      ) : stats ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Signals this week"
            value={stats.signals_this_week}
            icon={<Zap className="h-4 w-4" />}
            accent="text-violet-400"
          />
          <StatCard
            label="New opportunities"
            value={stats.new_opportunities}
            icon={<TrendingUp className="h-4 w-4" />}
            accent="text-emerald-400"
          />
          <StatCard
            label="Actions completed"
            value={stats.actions_completed}
            icon={<CheckSquare className="h-4 w-4" />}
            accent="text-blue-400"
          />
          <StatCard
            label="Agent cost this month"
            value={`$${totalCostThisMonth.toFixed(4)}`}
            icon={<DollarSign className="h-4 w-4" />}
            accent="text-amber-400"
          />
        </div>
      ) : null}

      {/* Charts row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Signal velocity */}
        <Card className="p-5 bg-card border-border">
          <h2 className="text-sm font-semibold text-foreground mb-4">
            Signal Velocity (last 30 days)
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={MOCK_SIGNAL_VELOCITY}>
              <defs>
                <linearGradient id="gradFunding" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradExec" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradExpansion" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradJob" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="date"
                tick={AXIS_TICK_STYLE}
                tickLine={false}
                interval={6}
              />
              <YAxis tick={AXIS_TICK_STYLE} tickLine={false} axisLine={false} />
              <Tooltip {...CHART_TOOLTIP_STYLE} />
              <Area
                type="monotone"
                dataKey="FUNDING"
                stackId="1"
                stroke="#10b981"
                fill="url(#gradFunding)"
                name="Funding"
              />
              <Area
                type="monotone"
                dataKey="EXEC_HIRE"
                stackId="1"
                stroke="#3b82f6"
                fill="url(#gradExec)"
                name="Exec Hire"
              />
              <Area
                type="monotone"
                dataKey="EXPANSION"
                stackId="1"
                stroke="#8b5cf6"
                fill="url(#gradExpansion)"
                name="Expansion"
              />
              <Area
                type="monotone"
                dataKey="JOB_POSTING_PATTERN"
                stackId="1"
                stroke="#f59e0b"
                fill="url(#gradJob)"
                name="Job Postings"
              />
            </AreaChart>
          </ResponsiveContainer>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Sample data — live data available once signal ingestion runs
          </p>
        </Card>

        {/* Company distribution */}
        <Card className="p-5 bg-card border-border">
          <h2 className="text-sm font-semibold text-foreground mb-4">
            Top Companies by Signal Count
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart
              data={MOCK_COMPANY_SIGNALS}
              layout="vertical"
              margin={{ left: 8, right: 8 }}
            >
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(var(--border))"
                horizontal={false}
              />
              <XAxis
                type="number"
                tick={AXIS_TICK_STYLE}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                type="category"
                dataKey="company"
                tick={AXIS_TICK_STYLE}
                tickLine={false}
                axisLine={false}
                width={90}
              />
              <Tooltip {...CHART_TOOLTIP_STYLE} />
              <Bar dataKey="signals" fill="#8b5cf6" radius={[0, 4, 4, 0]} name="Signals" />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-muted-foreground mt-2 text-center">
            Sample data — updates after real signal ingestion
          </p>
        </Card>
      </div>

      {/* Pipeline funnel */}
      {stats && (
        <Card className="p-5 bg-card border-border">
          <h2 className="text-sm font-semibold text-foreground mb-4">
            Conversion Pipeline
          </h2>
          <PipelineFunnel stages={stats.pipeline_stages} />
        </Card>
      )}

      {/* Agent cost table */}
      <Card className="p-5 bg-card border-border">
        <h2 className="text-sm font-semibold text-foreground mb-4">
          Agent Cost Breakdown
        </h2>
        {runsQuery.isLoading ? (
          <SkeletonCard lines={4} />
        ) : costRows.length === 0 ? (
          <div className="text-center py-8">
            <DollarSign className="h-8 w-8 text-muted-foreground/40 mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">No agent runs recorded yet.</p>
            <p className="text-xs text-muted-foreground mt-1">
              Costs appear here once AI agents have been invoked.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left pb-2 text-xs font-medium text-muted-foreground">
                    Agent
                  </th>
                  <th className="text-right pb-2 text-xs font-medium text-muted-foreground">
                    Calls
                  </th>
                  <th className="text-right pb-2 text-xs font-medium text-muted-foreground">
                    Total Tokens
                  </th>
                  <th className="text-right pb-2 text-xs font-medium text-muted-foreground">
                    Cost (USD)
                  </th>
                </tr>
              </thead>
              <tbody>
                {costRows.map((row) => (
                  <tr
                    key={row.agent_name}
                    className="border-b border-border/50 hover:bg-muted/30 transition-colors"
                  >
                    <td className="py-2.5 font-mono text-xs text-foreground">
                      {row.agent_name}
                    </td>
                    <td className="py-2.5 text-right text-muted-foreground">
                      {row.calls}
                    </td>
                    <td className="py-2.5 text-right text-muted-foreground">
                      {row.total_tokens.toLocaleString()}
                    </td>
                    <td className="py-2.5 text-right font-semibold text-amber-400">
                      ${row.cost_usd.toFixed(5)}
                    </td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={3} className="pt-2.5 text-xs text-muted-foreground">
                    Total
                  </td>
                  <td className="pt-2.5 text-right text-sm font-bold text-amber-400">
                    ${costRows.reduce((s, r) => s + r.cost_usd, 0).toFixed(5)}
                  </td>
                </tr>
              </tfoot>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
