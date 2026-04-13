'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Mail,
  Plus,
  Send,
  Clock,
  CheckCheck,
  MessageSquare,
  Eye,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { SkeletonCard } from '@/components/shared/SkeletonCard';
import { ErrorState } from '@/components/shared/ErrorState';
import { outreachApi } from '@/lib/api/client';
import type { OutreachEmail } from '@/types';

// ── Hooks ─────────────────────────────────────────────────────────────────────

function useOutreach(tab: string) {
  return useQuery({
    queryKey: ['outreach', tab],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (tab === 'pending') params.status = 'draft';
      if (tab === 'sent') params.status = 'sent';
      if (tab === 'replied') params.status = 'replied';
      const res = await outreachApi.list(params);
      // Backend may return {data:[]} or OutreachEmail[] directly
      const raw = res.data;
      if (Array.isArray(raw)) return raw as OutreachEmail[];
      if (raw && Array.isArray((raw as { data: OutreachEmail[] }).data))
        return (raw as { data: OutreachEmail[] }).data;
      return [] as OutreachEmail[];
    },
  });
}

function useSendEmail() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => outreachApi.send(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outreach'] });
    },
  });
}

// ── Tone badge ────────────────────────────────────────────────────────────────

const TONE_STYLES: Record<OutreachEmail['tone'], string> = {
  PROFESSIONAL: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  WARM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  DIRECT: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
};

const TONE_LABELS: Record<OutreachEmail['tone'], string> = {
  PROFESSIONAL: 'Professional',
  WARM: 'Warm',
  DIRECT: 'Direct',
};

// ── Status display ────────────────────────────────────────────────────────────

function EmailStatus({ email }: { email: OutreachEmail }) {
  if (email.reply_detected_at) {
    return (
      <span className="flex items-center gap-1 text-xs text-emerald-400">
        <MessageSquare className="h-3 w-3" />
        Replied
      </span>
    );
  }
  if (email.opened_at) {
    return (
      <span className="flex items-center gap-1 text-xs text-blue-400">
        <Eye className="h-3 w-3" />
        Opened
      </span>
    );
  }
  if (email.sent_at) {
    return (
      <span className="flex items-center gap-1 text-xs text-violet-400">
        <CheckCheck className="h-3 w-3" />
        Sent
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-xs text-muted-foreground">
      <Clock className="h-3 w-3" />
      Draft
    </span>
  );
}

// ── Email card ────────────────────────────────────────────────────────────────

interface EmailCardProps {
  email: OutreachEmail;
  onSend: (id: string) => void;
  sending: boolean;
}

function EmailCard({ email, onSend, sending }: EmailCardProps) {
  const [expanded, setExpanded] = useState(false);

  // Format date
  function fmtDate(iso?: string) {
    if (!iso) return null;
    return new Date(iso).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  const contactDisplay =
    email.contact_id.length > 20
      ? `…${email.contact_id.slice(-12)}`
      : email.contact_id;

  return (
    <Card className="p-5 bg-card border-border space-y-3 hover:border-border/80 transition-colors">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-xs text-muted-foreground">To:</span>
            <span className="text-xs font-mono text-foreground/70">{contactDisplay}</span>
            <Badge className={`text-xs border ${TONE_STYLES[email.tone]}`}>
              {TONE_LABELS[email.tone]}
            </Badge>
          </div>
          <p className="text-sm font-semibold text-foreground mt-1 truncate">{email.subject}</p>
        </div>
        <EmailStatus email={email} />
      </div>

      {/* Body preview / expanded */}
      <div>
        <p
          className={`text-xs text-muted-foreground leading-relaxed ${
            expanded ? '' : 'line-clamp-2'
          }`}
        >
          {email.body}
        </p>
        {email.body.length > 120 && (
          <button
            className="text-xs text-primary hover:underline mt-1"
            onClick={() => setExpanded((v) => !v)}
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>

      {/* Timestamps */}
      {(email.sent_at || email.opened_at || email.replied_at) && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground border-t border-border/50 pt-2">
          {email.sent_at && (
            <span>Sent: <span className="text-foreground/60">{fmtDate(email.sent_at)}</span></span>
          )}
          {email.opened_at && (
            <span>Opened: <span className="text-blue-400">{fmtDate(email.opened_at)}</span></span>
          )}
          {email.replied_at && (
            <span>Replied: <span className="text-emerald-400">{fmtDate(email.replied_at)}</span></span>
          )}
        </div>
      )}

      {/* Actions */}
      {!email.sent_at && (
        <div className="flex justify-end">
          <Button
            size="sm"
            onClick={() => onSend(email.id)}
            disabled={sending}
            className="flex items-center gap-2 text-xs"
          >
            <Send className="h-3.5 w-3.5" />
            {sending ? 'Sending…' : 'Send via Gmail'}
          </Button>
        </div>
      )}
    </Card>
  );
}

// ── Composer dialog ───────────────────────────────────────────────────────────

type DraftTone = 'PROFESSIONAL' | 'WARM' | 'DIRECT';

interface ComposerProps {
  open: boolean;
  onClose: () => void;
}

function ComposerDialog({ open, onClose }: ComposerProps) {
  const queryClient = useQueryClient();
  const [to, setTo] = useState('');
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [tone, setTone] = useState<DraftTone>('PROFESSIONAL');
  const [status, setStatus] = useState<'idle' | 'generating' | 'sending' | 'done'>('idle');

  const generateMutation = useMutation({
    mutationFn: () =>
      outreachApi.draft({
        contact_id: to,
        subject,
        body,
        tone,
      }),
    onSuccess: (res) => {
      const d = res.data as Partial<OutreachEmail>;
      if (d.subject) setSubject(d.subject);
      if (d.body) setBody(d.body);
      setStatus('idle');
    },
    onError: () => setStatus('idle'),
  });

  const sendMutation = useMutation({
    mutationFn: async () => {
      // Draft first, then send
      const draftRes = await outreachApi.draft({ contact_id: to, subject, body, tone });
      const draftId = (draftRes.data as { id: string }).id;
      return outreachApi.send(draftId);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['outreach'] });
      setStatus('done');
      setTimeout(() => {
        setStatus('idle');
        onClose();
      }, 1500);
    },
    onError: () => setStatus('idle'),
  });

  function handleGenerate() {
    setStatus('generating');
    generateMutation.mutate();
  }

  function handleSend() {
    setStatus('sending');
    sendMutation.mutate();
  }

  function handleClose() {
    if (status === 'idle' || status === 'done') {
      setTo('');
      setSubject('');
      setBody('');
      setTone('PROFESSIONAL');
      setStatus('idle');
      onClose();
    }
  }

  const tones: DraftTone[] = ['PROFESSIONAL', 'WARM', 'DIRECT'];

  return (
    <Dialog open={open} onOpenChange={(v: boolean) => !v && handleClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>New Email Draft</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* To */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              To (contact ID or name)
            </label>
            <Input
              value={to}
              onChange={(e) => setTo(e.target.value)}
              placeholder="Contact name or ID…"
            />
          </div>

          {/* Subject */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Subject
            </label>
            <Input
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Email subject…"
            />
          </div>

          {/* Body */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Body
            </label>
            <textarea
              rows={6}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Write your message, or click Generate Draft to have AI draft it…"
              className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground outline-none focus:ring-2 focus:ring-ring/50 focus:border-ring transition-colors resize-none"
            />
          </div>

          {/* Tone */}
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Tone
            </label>
            <div className="flex gap-2">
              {tones.map((t) => (
                <button
                  key={t}
                  onClick={() => setTone(t)}
                  className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                    tone === t
                      ? TONE_STYLES[t]
                      : 'border-border text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {TONE_LABELS[t]}
                </button>
              ))}
            </div>
          </div>

          {status === 'done' && (
            <p className="text-xs text-emerald-400 flex items-center gap-1.5">
              <CheckCheck className="h-4 w-4" />
              Email sent successfully!
            </p>
          )}
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            size="sm"
            onClick={handleGenerate}
            disabled={status !== 'idle' || !to}
            className="flex items-center gap-2"
          >
            <Sparkles className="h-3.5 w-3.5" />
            {status === 'generating' ? 'Generating…' : 'Generate Draft'}
          </Button>
          <Button
            size="sm"
            onClick={handleSend}
            disabled={status !== 'idle' || !to || !subject || !body}
            className="flex items-center gap-2"
          >
            <Send className="h-3.5 w-3.5" />
            {status === 'sending' ? 'Sending…' : 'Send via Gmail'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ── Tab panel ─────────────────────────────────────────────────────────────────

interface TabPanelProps {
  tab: string;
}

function EmailTabPanel({ tab }: TabPanelProps) {
  const query = useOutreach(tab);
  const sendMutation = useSendEmail();

  if (query.isLoading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => <SkeletonCard key={i} lines={3} />)}
      </div>
    );
  }

  if (query.isError) {
    return (
      <ErrorState
        error={query.error as Error}
        onRetry={() => query.refetch()}
      />
    );
  }

  const emails = query.data ?? [];

  if (emails.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-border bg-card p-12 text-center">
        <Mail className="h-8 w-8 text-muted-foreground/40" />
        <p className="text-sm font-medium text-foreground">No email drafts yet</p>
        <p className="text-xs text-muted-foreground">
          Generate a draft from an action, or use the New Draft button above.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {emails.map((email) => (
        <EmailCard
          key={email.id}
          email={email}
          onSend={(id) => sendMutation.mutate(id)}
          sending={sendMutation.isPending && sendMutation.variables === email.id}
        />
      ))}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

const TABS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'sent', label: 'Sent' },
  { value: 'replied', label: 'Replied' },
] as const;

export default function OutreachPage() {
  const [activeTab, setActiveTab] = useState<string>('all');
  const [composerOpen, setComposerOpen] = useState(false);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Mail className="h-5 w-5 text-primary" />
          <h1 className="text-lg font-semibold text-foreground">Outreach</h1>
        </div>
        <Button
          size="sm"
          onClick={() => setComposerOpen(true)}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          New Draft
        </Button>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {TABS.map((t) => (
          <TabsContent key={t.value} value={t.value} className="mt-4">
            <EmailTabPanel tab={t.value} />
          </TabsContent>
        ))}
      </Tabs>

      {/* Composer dialog */}
      <ComposerDialog open={composerOpen} onClose={() => setComposerOpen(false)} />
    </div>
  );
}
