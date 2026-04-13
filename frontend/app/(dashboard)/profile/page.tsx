'use client';

import { useState, useEffect, KeyboardEvent } from 'react';
import { User, Sparkles, Save, X, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import {
  Progress,
  ProgressTrack,
  ProgressIndicator,
  ProgressLabel,
  ProgressValue,
} from '@/components/ui/progress';
import { SkeletonCard } from '@/components/shared/SkeletonCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { useProfile, useUpdateProfile } from '@/hooks/useProfile';
import { profileApi } from '@/lib/api/client';
import type { CareerProfile } from '@/types';

// ── Tag input component ───────────────────────────────────────────────────────

interface TagInputProps {
  label: string;
  tags: string[];
  placeholder?: string;
  onChange: (tags: string[]) => void;
}

function TagInput({ label, tags, placeholder = 'Type and press Enter…', onChange }: TagInputProps) {
  const [draft, setDraft] = useState('');

  function addTag() {
    const trimmed = draft.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
    }
    setDraft('');
  }

  function handleKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter') {
      e.preventDefault();
      addTag();
    }
    if (e.key === 'Backspace' && !draft && tags.length > 0) {
      onChange(tags.slice(0, -1));
    }
  }

  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
        {label}
      </label>
      <div className="min-h-10 rounded-lg border border-border bg-background px-3 py-2 flex flex-wrap gap-1.5 cursor-text focus-within:ring-2 focus-within:ring-ring/50 focus-within:border-ring transition-colors">
        {tags.map((tag) => (
          <span
            key={tag}
            className="inline-flex items-center gap-1 rounded-md bg-violet-500/20 text-violet-400 border border-violet-500/30 px-2 py-0.5 text-xs font-medium"
          >
            {tag}
            <button
              type="button"
              onClick={() => onChange(tags.filter((t) => t !== tag))}
              className="hover:text-violet-300 transition-colors"
              aria-label={`Remove ${tag}`}
            >
              <X className="h-3 w-3" />
            </button>
          </span>
        ))}
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={handleKey}
          onBlur={addTag}
          placeholder={tags.length === 0 ? placeholder : ''}
          className="flex-1 min-w-24 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none"
        />
      </div>
    </div>
  );
}

// ── Completeness calc ─────────────────────────────────────────────────────────

function calcCompleteness(profile: Partial<CareerProfile>): number {
  const checks = [
    Boolean(profile.current_role?.trim()),
    (profile.target_roles?.length ?? 0) > 0,
    (profile.industries?.length ?? 0) > 0,
    Boolean(profile.aspirations_text?.trim()),
  ];
  return Math.round((checks.filter(Boolean).length / checks.length) * 100);
}

// ── Main page ─────────────────────────────────────────────────────────────────

type SaveStatus = 'idle' | 'saving' | 'success' | 'error';

export default function ProfilePage() {
  const profileQuery = useProfile();
  const updateMutation = useUpdateProfile();

  // Form state — mirrors CareerProfile editable fields
  const [currentRole, setCurrentRole] = useState('');
  const [targetRoles, setTargetRoles] = useState<string[]>([]);
  const [industries, setIndustries] = useState<string[]>([]);
  const [aspirationsText, setAspirationsText] = useState('');
  const [saveStatus, setSaveStatus] = useState<SaveStatus>('idle');
  const [analyzeRunId, setAnalyzeRunId] = useState<string | null>(null);

  // Sync form when profile loads
  useEffect(() => {
    if (profileQuery.data) {
      const p = profileQuery.data;
      setCurrentRole(p.current_role ?? '');
      setTargetRoles(p.target_roles ?? []);
      setIndustries(p.industries ?? []);
      setAspirationsText(p.aspirations_text ?? '');
    }
  }, [profileQuery.data]);

  const completeness = calcCompleteness({
    current_role: currentRole,
    target_roles: targetRoles,
    industries,
    aspirations_text: aspirationsText,
  });

  async function handleSave() {
    setSaveStatus('saving');
    try {
      await updateMutation.mutateAsync({
        current_role: currentRole,
        target_roles: targetRoles,
        industries,
        aspirations_text: aspirationsText,
      });
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 2500);
    } catch {
      setSaveStatus('error');
      setTimeout(() => setSaveStatus('idle'), 3000);
    }
  }

  async function handleAnalyze() {
    try {
      const res = await profileApi.analyze();
      setAnalyzeRunId((res.data as { run_id: string }).run_id);
      setTimeout(() => setAnalyzeRunId(null), 8000);
    } catch {
      // silently fail — no backend yet
    }
  }

  if (profileQuery.isLoading) {
    return (
      <div className="space-y-4 max-w-2xl">
        <SkeletonCard lines={4} />
        <SkeletonCard lines={3} />
      </div>
    );
  }

  if (profileQuery.isError) {
    return (
      <ErrorState
        error={profileQuery.error as Error}
        onRetry={() => profileQuery.refetch()}
      />
    );
  }

  const completenessColor =
    completeness >= 75
      ? 'bg-emerald-500'
      : completeness >= 40
      ? 'bg-amber-500'
      : 'bg-red-500';

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <User className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold text-foreground">Career Profile</h1>
        </div>
        {profileQuery.data?.updated_at && (
          <p className="text-xs text-muted-foreground">
            Last updated:{' '}
            {new Date(profileQuery.data.updated_at).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              year: 'numeric',
            })}
          </p>
        )}
      </div>

      {/* Completeness */}
      <Card className="p-5 bg-card border-border">
        <div className="flex items-center justify-between mb-3">
          <span className="text-sm font-medium text-foreground">Profile completeness</span>
          <span
            className={`text-sm font-bold ${
              completeness >= 75
                ? 'text-emerald-400'
                : completeness >= 40
                ? 'text-amber-400'
                : 'text-red-400'
            }`}
          >
            {completeness}%
          </span>
        </div>
        <Progress value={completeness}>
          <ProgressLabel className="sr-only">Profile completeness</ProgressLabel>
          <ProgressValue className="sr-only">{() => `${completeness}%`}</ProgressValue>
          <ProgressTrack className="h-2">
            <ProgressIndicator className={completenessColor} />
          </ProgressTrack>
        </Progress>
        {completeness < 100 && (
          <p className="text-xs text-muted-foreground mt-2">
            {completeness < 40
              ? 'Complete your profile to unlock better opportunity predictions.'
              : completeness < 75
              ? 'Almost there — add more details for sharper AI recommendations.'
              : 'Great profile! Keep it updated for the best predictions.'}
          </p>
        )}
      </Card>

      {/* Form */}
      <Card className="p-6 bg-card border-border space-y-5">
        {/* Current role */}
        <div className="space-y-1.5">
          <label
            htmlFor="current-role"
            className="text-xs font-medium text-muted-foreground uppercase tracking-wide"
          >
            Current role
          </label>
          <Input
            id="current-role"
            value={currentRole}
            onChange={(e) => setCurrentRole(e.target.value)}
            placeholder="e.g. Senior Product Manager at Contentsquare"
            className="bg-background"
          />
        </div>

        {/* Target roles */}
        <TagInput
          label="Target roles"
          tags={targetRoles}
          placeholder="e.g. Head of Product — press Enter to add"
          onChange={setTargetRoles}
        />

        {/* Industries */}
        <TagInput
          label="Target industries"
          tags={industries}
          placeholder="e.g. Fintech, SaaS — press Enter to add"
          onChange={setIndustries}
        />

        {/* Aspirations */}
        <div className="space-y-1.5">
          <label
            htmlFor="aspirations"
            className="text-xs font-medium text-muted-foreground uppercase tracking-wide"
          >
            Career aspirations
          </label>
          <textarea
            id="aspirations"
            rows={4}
            value={aspirationsText}
            onChange={(e) => setAspirationsText(e.target.value)}
            placeholder="Describe where you want to take your career — role, impact, company stage, culture…"
            className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring transition-colors resize-none"
          />
          <p className="text-xs text-muted-foreground">
            The AI uses this to predict which opportunities fit your aspirations, not just your skills.
          </p>
        </div>
      </Card>

      {/* Feedback banners */}
      {saveStatus === 'success' && (
        <div className="flex items-center gap-2 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-500/30 rounded-lg px-3 py-2">
          <CheckCircle className="h-4 w-4 shrink-0" />
          Profile saved successfully.
        </div>
      )}
      {saveStatus === 'error' && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-3 py-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          Failed to save — please try again.
        </div>
      )}
      {analyzeRunId && (
        <div className="flex items-center gap-2 text-xs text-blue-400 bg-blue-500/10 border border-blue-500/30 rounded-lg px-3 py-2">
          <Sparkles className="h-4 w-4 shrink-0 animate-pulse" />
          Analysis queued — run ID: <span className="font-mono">{analyzeRunId}</span>. Results will update shortly.
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-3">
        <Button
          onClick={handleSave}
          disabled={saveStatus === 'saving'}
          className="flex items-center gap-2"
        >
          <Save className="h-4 w-4" />
          {saveStatus === 'saving' ? 'Saving…' : 'Save Profile'}
        </Button>
        <Button
          variant="outline"
          onClick={handleAnalyze}
          className="flex items-center gap-2"
        >
          <Sparkles className="h-4 w-4" />
          Analyze Profile
        </Button>
      </div>
    </div>
  );
}
