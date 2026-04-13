'use client';

import * as React from 'react';
import Link from 'next/link';
import {
  Mail,
  RefreshCw,
  Search,
  Phone,
  Calendar,
  Building2,
  Sparkles,
  ExternalLink,
  CheckCircle2,
  Clock,
} from 'lucide-react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from '@/components/ui/sheet';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { cn } from '@/lib/utils';
import type { Action } from '@/types';

// ── Colour maps ───────────────────────────────────────────────────────────────

const PRIORITY_CLASSES: Record<Action['priority'], string> = {
  HIGH:   'bg-red-500/20 text-red-400 border-red-500/30',
  MEDIUM: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  LOW:    'bg-muted text-muted-foreground border-border',
};

const TYPE_ICON: Record<Action['type'], React.ReactNode> = {
  OUTREACH:   <Mail className="h-4 w-4" />,
  FOLLOW_UP:  <RefreshCw className="h-4 w-4" />,
  RESEARCH:   <Search className="h-4 w-4" />,
  CALL:       <Phone className="h-4 w-4" />,
};

const TYPE_LABEL: Record<Action['type'], string> = {
  OUTREACH:   'Outreach',
  FOLLOW_UP:  'Follow-up',
  RESEARCH:   'Research',
  CALL:       'Call',
};

const TYPE_COLOR: Record<Action['type'], string> = {
  OUTREACH:   'text-blue-400',
  FOLLOW_UP:  'text-violet-400',
  RESEARCH:   'text-amber-400',
  CALL:       'text-emerald-400',
};

const STATUS_OPTIONS: { value: Action['status']; label: string }[] = [
  { value: 'TODO',        label: 'Todo' },
  { value: 'IN_PROGRESS', label: 'In Progress' },
  { value: 'DONE',        label: 'Done' },
  { value: 'SNOOZED',     label: 'Snoozed' },
];

// ── Props ─────────────────────────────────────────────────────────────────────

interface ActionDetailProps {
  action: Action | null;
  onClose: () => void;
  onStatusChange: (id: string, status: Action['status']) => void;
  onDraftEmail: (id: string) => void;
  isDrafting?: boolean;
}

// ── Component ─────────────────────────────────────────────────────────────────

export function ActionDetail({
  action,
  onClose,
  onStatusChange,
  onDraftEmail,
  isDrafting = false,
}: ActionDetailProps) {
  const isOpen = action !== null;

  const displayDue = action?.dueDate ?? action?.due_date ?? '';
  const displayCompany = action?.company ?? action?.company_id ?? '';
  const createdDate = action
    ? new Date(action.created_at).toLocaleDateString('en-GB', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
      })
    : '';

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
        {action && (
          <>
            <SheetHeader className="pb-4 border-b border-border">
              {/* Type + priority badges */}
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className={cn('flex items-center gap-1.5 text-xs font-medium', TYPE_COLOR[action.type])}>
                  {TYPE_ICON[action.type]}
                  {TYPE_LABEL[action.type]}
                </span>
                <Badge
                  variant="outline"
                  className={`text-[10px] px-1.5 py-0 ${PRIORITY_CLASSES[action.priority]}`}
                >
                  {action.priority}
                </Badge>
              </div>

              <SheetTitle className="text-base leading-snug pr-6">
                {action.title}
              </SheetTitle>

              {displayCompany && (
                <SheetDescription className="flex items-center gap-1.5 text-sm">
                  <Building2 className="h-3.5 w-3.5 shrink-0" />
                  {displayCompany}
                </SheetDescription>
              )}
            </SheetHeader>

            {/* ── Body ──────────────────────────────────────────────── */}
            <div className="p-4 space-y-5">

              {/* Description */}
              {action.description && (
                <section>
                  <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
                    Description
                  </p>
                  <p className="text-sm text-foreground leading-relaxed">
                    {action.description}
                  </p>
                </section>
              )}

              {/* Due date + created */}
              <section className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Calendar className="h-3.5 w-3.5" />
                    <span className="text-[10px] uppercase tracking-wide font-medium">Due</span>
                  </div>
                  <p className="text-sm font-medium text-foreground">{displayDue || '—'}</p>
                </div>
                <div className="rounded-lg border border-border bg-muted/30 p-3 space-y-1">
                  <div className="flex items-center gap-1.5 text-muted-foreground">
                    <Clock className="h-3.5 w-3.5" />
                    <span className="text-[10px] uppercase tracking-wide font-medium">Created</span>
                  </div>
                  <p className="text-sm font-medium text-foreground">{createdDate}</p>
                </div>
              </section>

              {/* Status selector */}
              <section>
                <p className="text-xs font-medium text-muted-foreground mb-2 uppercase tracking-wider">
                  Status
                </p>
                <Select
                  value={action.status}
                  onValueChange={(val) =>
                    onStatusChange(action.id, val as Action['status'])
                  }
                >
                  <SelectTrigger size="sm" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STATUS_OPTIONS.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>
                        {opt.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </section>

              {/* Opportunity link */}
              {action.opportunity_id && (
                <section>
                  <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
                    Linked Opportunity
                  </p>
                  <Link
                    href="/opportunities"
                    className="flex items-center gap-2 text-sm text-violet-400 hover:text-violet-300 transition-colors"
                  >
                    <Sparkles className="h-4 w-4" />
                    View predicted opportunity
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </Link>
                </section>
              )}

              {/* Source signal link */}
              {(action.sourceSignalId ?? action.source_signal_id) && (
                <section>
                  <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">
                    Source Signal
                  </p>
                  <Link
                    href="/signals"
                    className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
                  >
                    View signal
                    <ExternalLink className="h-3 w-3 ml-auto" />
                  </Link>
                </section>
              )}

              {/* Mark done shortcut */}
              {action.status !== 'DONE' && (
                <button
                  type="button"
                  onClick={() => onStatusChange(action.id, 'DONE')}
                  className="w-full flex items-center justify-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-sm font-medium py-2.5 hover:bg-emerald-500/20 transition-colors"
                >
                  <CheckCircle2 className="h-4 w-4" />
                  Mark as Done
                </button>
              )}
            </div>

            {/* ── Footer ────────────────────────────────────────────── */}
            <SheetFooter className="border-t border-border">
              {action.type === 'OUTREACH' || action.type === 'FOLLOW_UP' ? (
                <Button
                  size="sm"
                  className="w-full gap-2"
                  onClick={() => onDraftEmail(action.id)}
                  disabled={isDrafting}
                >
                  <Mail className="h-3.5 w-3.5" />
                  {isDrafting ? 'Queuing draft…' : 'Draft Email'}
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  className="w-full"
                  onClick={onClose}
                >
                  Close
                </Button>
              )}
            </SheetFooter>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
