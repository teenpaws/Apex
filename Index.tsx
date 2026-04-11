import { DashboardLayout } from "@/components/DashboardLayout";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { signals, actions, opportunities } from "@/data/mock";
import { ArrowRight, Sparkles, Clock, User } from "lucide-react";
import { Link } from "react-router-dom";
import { PipelineViz } from "@/components/PipelineViz";

const signalTypeColor: Record<string, string> = {
  Funding: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  "Exec Hire": "bg-blue-500/20 text-blue-400 border-blue-500/30",
  Expansion: "bg-violet-500/20 text-violet-400 border-violet-500/30",
  "Job Posting Pattern": "bg-amber-500/20 text-amber-400 border-amber-500/30",
};

const priorityColor: Record<string, string> = {
  High: "bg-red-500/20 text-red-400 border-red-500/30",
  Medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  Low: "bg-muted text-muted-foreground",
};

const confidenceColor: Record<string, string> = {
  High: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  Medium: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  Speculative: "bg-muted text-muted-foreground border-border",
};

export default function Index() {
  const recentSignals = signals.slice(0, 3);
  const priorityActions = actions.filter((a) => a.status !== "Done").slice(0, 3);
  const topOpps = opportunities.filter((o) => o.confidence === "High").slice(0, 3);

  return (
    <DashboardLayout title="Dashboard">
      <div className="space-y-6">
        {/* Pipeline Visualization */}
        <PipelineViz />

        {/* Top Predicted Opportunities — Hero Section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-violet-400" />
              <h2 className="text-base font-semibold text-foreground">Top Predicted Opportunities</h2>
            </div>
            <Link to="/opportunities" className="text-xs text-primary hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {topOpps.map((opp) => (
              <Link key={opp.id} to="/opportunities" className="group">
                <Card className="bg-gradient-to-br from-violet-500/10 to-purple-600/5 border-violet-500/20 h-full transition-all duration-200 group-hover:border-violet-400/40 group-hover:shadow-lg group-hover:shadow-violet-500/10">
                  <CardContent className="p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className={`text-[10px] ${confidenceColor[opp.confidence]}`}>
                        {opp.confidence}
                      </Badge>
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" /> {opp.timeline}
                      </span>
                    </div>
                    <div>
                      <h3 className="font-semibold text-sm text-foreground">{opp.role}</h3>
                      <p className="text-xs text-muted-foreground">{opp.company}</p>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">{opp.whyFit}</p>
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
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent Signals */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Recent Signals</CardTitle>
                <Link to="/signals" className="text-xs text-primary hover:underline flex items-center gap-1">
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {recentSignals.map((signal) => (
                <Link key={signal.id} to="/signals" className="block group">
                  <div className="flex items-start justify-between gap-3 p-3 rounded-lg bg-muted/50 transition-colors group-hover:bg-muted/80">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-medium text-sm text-foreground">{signal.company}</span>
                        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${signalTypeColor[signal.type]}`}>
                          {signal.type}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground truncate">{signal.description}</p>
                      {signal.linkedOpportunityIds.length > 0 && (
                        <p className="text-[10px] text-violet-400 mt-1 flex items-center gap-1">
                          <Sparkles className="h-3 w-3" /> {signal.linkedOpportunityIds.length} opportunity predicted
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">{signal.date}</span>
                  </div>
                </Link>
              ))}
            </CardContent>
          </Card>

          {/* Priority Actions */}
          <Card className="bg-card border-border">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">Priority Actions</CardTitle>
                <Link to="/actions" className="text-xs text-primary hover:underline flex items-center gap-1">
                  View all <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {priorityActions.map((action) => (
                <Link key={action.id} to="/actions" className="block group">
                  <div className="flex items-start justify-between gap-3 p-3 rounded-lg bg-muted/50 transition-colors group-hover:bg-muted/80">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground mb-1">{action.title}</p>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${priorityColor[action.priority]}`}>
                          {action.priority}
                        </Badge>
                        <span className="text-xs text-muted-foreground">{action.company}</span>
                      </div>
                      {action.sourceSignalId && (
                        <p className="text-[10px] text-blue-400 mt-1">
                          Triggered by signal
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">{action.dueDate}</span>
                  </div>
                </Link>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>
    </DashboardLayout>
  );
}
