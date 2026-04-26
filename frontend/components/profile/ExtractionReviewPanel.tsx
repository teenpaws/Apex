"use client";

import { useState } from "react";
import { documentsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, Loader2 } from "lucide-react";
import type { StagedProfile } from "@/types";

export type { StagedProfile };

interface Props {
  staged: StagedProfile;
  onApproved: () => void;
}

export function ExtractionReviewPanel({ staged, onApproved }: Props) {
  const [approving, setApproving] = useState(false);
  const [approved, setApproved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleApprove = async () => {
    setApproving(true);
    setError(null);
    try {
      await documentsApi.approve();
      setApproved(true);
      onApproved();
    } catch {
      setError("Approval failed. Please try again.");
    } finally {
      setApproving(false);
    }
  };

  if (approved) {
    return (
      <div className="flex items-center gap-2 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
        <CheckCircle2 className="h-4 w-4 text-emerald-400" />
        <p className="text-sm text-emerald-400">
          Profile updated. Existing opportunities will be re-scored in the
          background.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4 p-4 rounded-lg bg-violet-500/5 border border-violet-500/20">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-foreground">
          Extracted profile — review before applying
        </h3>
        <Button
          size="sm"
          onClick={handleApprove}
          disabled={approving}
          className="bg-violet-600 hover:bg-violet-700 text-white"
        >
          {approving ? (
            <>
              <Loader2 className="mr-2 h-3 w-3 animate-spin" /> Applying…
            </>
          ) : (
            "Apply to profile"
          )}
        </Button>
      </div>

      {error && <p className="text-xs text-red-400">{error}</p>}

      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span className="text-muted-foreground text-xs">Experience</span>
          <p className="font-medium">{staged.years_of_experience} years</p>
        </div>
        <div>
          <span className="text-muted-foreground text-xs">Seniority</span>
          <div className="mt-1">
            <Badge
              variant="outline"
              className="bg-violet-500/20 text-violet-400 border-violet-500/30 text-xs"
            >
              {staged.seniority_band}
            </Badge>
          </div>
        </div>
      </div>

      {staged.work_history && staged.work_history.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Work history</p>
          <ul className="space-y-1">
            {staged.work_history.slice(0, 3).map((w, i) => (
              <li key={i} className="text-sm">
                <span className="font-medium">{w.title}</span>
                <span className="text-muted-foreground"> · {w.company}</span>
                {w.start_year && (
                  <span className="text-muted-foreground">
                    {" "}
                    ({w.start_year}–{w.end_year ?? "present"})
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {staged.key_achievements && staged.key_achievements.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Key achievements</p>
          <ul className="space-y-1">
            {staged.key_achievements.slice(0, 3).map((a, i) => (
              <li key={i} className="text-sm">
                {a.achievement}
                {a.impact && (
                  <span className="text-muted-foreground"> — {a.impact}</span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {staged.inferred_skills && staged.inferred_skills.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-2">Inferred skills</p>
          <div className="flex flex-wrap gap-1">
            {staged.inferred_skills.map((s, i) => (
              <Badge key={i} variant="outline" className="text-xs">
                {s}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
