'use client';

import { useState, useEffect } from 'react';
import {
  Settings,
  CheckCircle2,
  XCircle,
  Mail,
  Bell,
  Radio,
  KeyRound,
  Info,
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { outreachApi } from '@/lib/api/client';

// ── Constants ─────────────────────────────────────────────────────────────────

const API_KEYS = [
  { label: 'Anthropic API', env: 'ANTHROPIC_API_KEY', description: 'Powers all AI agents (Sonnet + Haiku)' },
  { label: 'OpenAI API', env: 'OPENAI_API_KEY', description: 'Generates vector embeddings' },
  { label: 'NewsData.io', env: 'NEWSDATA_API_KEY', description: 'Primary news signal source' },
  { label: 'GNews API', env: 'GNEWS_API_KEY', description: 'Backup news signal source' },
  { label: 'People Data Labs', env: 'PDL_API_KEY', description: 'Contact & company enrichment' },
  { label: 'Hunter.io', env: 'HUNTER_API_KEY', description: 'Email discovery by domain' },
  { label: 'Supabase URL', env: 'SUPABASE_URL', description: 'Database & auth' },
  { label: 'Supabase Anon Key', env: 'SUPABASE_ANON_KEY', description: 'Database & auth' },
] as const;

type IngestFrequency = 'hourly' | '4h' | 'daily';

interface SignalSourceSettings {
  rss: boolean;
  secEdgar: boolean;
  newsdata: boolean;
  gnews: boolean;
  frequency: IngestFrequency;
}

interface NotificationSettings {
  newOpportunity: boolean;
  highPriorityAction: boolean;
  emailReply: boolean;
}

const DEFAULT_SIGNAL_SOURCES: SignalSourceSettings = {
  rss: true,
  secEdgar: true,
  newsdata: true,
  gnews: true,
  frequency: '4h',
};

const DEFAULT_NOTIFICATIONS: NotificationSettings = {
  newOpportunity: true,
  highPriorityAction: true,
  emailReply: true,
};

// ── Toggle switch ─────────────────────────────────────────────────────────────

interface ToggleProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  label: string;
  description?: string;
}

function Toggle({ checked, onChange, label, description }: ToggleProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-2">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        {description && (
          <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
        )}
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 ${
          checked ? 'bg-emerald-500' : 'bg-muted'
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 rounded-full bg-white shadow-sm transition-transform ${
            checked ? 'translate-x-4.5' : 'translate-x-0.5'
          }`}
        />
      </button>
    </div>
  );
}

// ── Section wrapper ───────────────────────────────────────────────────────────

interface SectionProps {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}

function Section({ icon, title, children }: SectionProps) {
  return (
    <Card className="p-6 bg-card border-border space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-primary">{icon}</span>
        <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      </div>
      <Separator />
      {children}
    </Card>
  );
}

// ── API key row ───────────────────────────────────────────────────────────────

interface ApiKeyRowProps {
  label: string;
  description: string;
  connected: boolean;
}

function ApiKeyRow({ label, description, connected }: ApiKeyRowProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <div>
        <p className="text-sm font-medium text-foreground">{label}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
      <div className={`flex items-center gap-1.5 text-xs font-medium ${connected ? 'text-emerald-400' : 'text-red-400'}`}>
        {connected ? (
          <>
            <CheckCircle2 className="h-4 w-4" />
            Connected
          </>
        ) : (
          <>
            <XCircle className="h-4 w-4" />
            Not set
          </>
        )}
      </div>
    </div>
  );
}

// ── Local storage helpers ─────────────────────────────────────────────────────

function loadLS<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function saveLS(key: string, value: unknown) {
  if (typeof window !== 'undefined') {
    localStorage.setItem(key, JSON.stringify(value));
  }
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [signalSources, setSignalSources] = useState<SignalSourceSettings>(DEFAULT_SIGNAL_SOURCES);
  const [notifications, setNotifications] = useState<NotificationSettings>(DEFAULT_NOTIFICATIONS);
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailMessage, setGmailMessage] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  // Load from localStorage after hydration
  useEffect(() => {
    setSignalSources(loadLS('apex_signal_sources', DEFAULT_SIGNAL_SOURCES));
    setNotifications(loadLS('apex_notifications', DEFAULT_NOTIFICATIONS));
    setGmailConnected(loadLS('apex_gmail_connected', false));
    setHydrated(true);
  }, []);

  function updateSignalSources(patch: Partial<SignalSourceSettings>) {
    setSignalSources((prev) => {
      const next = { ...prev, ...patch };
      saveLS('apex_signal_sources', next);
      return next;
    });
  }

  function updateNotifications(patch: Partial<NotificationSettings>) {
    setNotifications((prev) => {
      const next = { ...prev, ...patch };
      saveLS('apex_notifications', next);
      return next;
    });
  }

  async function handleConnectGmail() {
    try {
      const res = await outreachApi.connectGmail();
      const data = res.data as { redirect_url?: string; message?: string };
      if (data.redirect_url) {
        setGmailMessage(`Redirect to: ${data.redirect_url}`);
      } else {
        setGmailMessage(data.message ?? 'OAuth flow initiated. Follow the browser redirect.');
      }
      setGmailConnected(true);
      saveLS('apex_gmail_connected', true);
    } catch {
      setGmailMessage('Could not initiate Gmail OAuth — check that the backend is running.');
    }
  }

  // Static "connected" status — in dev these are never set via env, so all show Not set.
  // In production the backend exposes a /settings/keys-status endpoint (future work).
  const KEY_STATUS: Record<string, boolean> = {};

  if (!hydrated) {
    return null; // Prevent localStorage hydration mismatch
  }

  return (
    <div className="space-y-6 max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-2">
        <Settings className="h-5 w-5 text-primary" />
        <h1 className="text-lg font-semibold text-foreground">Settings</h1>
      </div>

      {/* Section 1: API Key Status */}
      <Section icon={<KeyRound className="h-4 w-4" />} title="API Key Status">
        <div className="flex items-start gap-2 rounded-lg bg-muted/50 border border-border px-3 py-2.5 mb-2">
          <Info className="h-4 w-4 text-muted-foreground shrink-0 mt-0.5" />
          <p className="text-xs text-muted-foreground">
            Configure API keys via the <code className="font-mono bg-muted rounded px-1">.env</code> file on the server.
            Keys are never exposed to the frontend — only connection status is shown.
          </p>
        </div>
        <div className="divide-y divide-border/50">
          {API_KEYS.map((k) => (
            <ApiKeyRow
              key={k.env}
              label={k.label}
              description={k.description}
              connected={KEY_STATUS[k.env] ?? false}
            />
          ))}
        </div>
      </Section>

      {/* Section 2: Signal Sources */}
      <Section icon={<Radio className="h-4 w-4" />} title="Signal Sources">
        <div className="space-y-1 divide-y divide-border/50">
          <Toggle
            checked={signalSources.rss}
            onChange={(v) => updateSignalSources({ rss: v })}
            label="RSS Feeds"
            description="Company blogs, press releases, expansion signals"
          />
          <Toggle
            checked={signalSources.secEdgar}
            onChange={(v) => updateSignalSources({ secEdgar: v })}
            label="SEC EDGAR"
            description="Form D (funding), 8-K (exec changes, contracts), 10-K/10-Q"
          />
          <Toggle
            checked={signalSources.newsdata}
            onChange={(v) => updateSignalSources({ newsdata: v })}
            label="NewsData.io"
            description="Funding, leadership changes, market entry (200 req/day free)"
          />
          <Toggle
            checked={signalSources.gnews}
            onChange={(v) => updateSignalSources({ gnews: v })}
            label="GNews API"
            description="Backup news source, broad coverage (100 req/day free)"
          />
        </div>

        <div className="pt-2">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
            Ingest frequency
          </p>
          <div className="flex gap-3">
            {(
              [
                { value: 'hourly', label: 'Hourly' },
                { value: '4h', label: 'Every 4h' },
                { value: 'daily', label: 'Daily' },
              ] as { value: IngestFrequency; label: string }[]
            ).map((opt) => (
              <label
                key={opt.value}
                className={`flex items-center gap-2 cursor-pointer rounded-lg border px-3 py-2 text-sm transition-colors ${
                  signalSources.frequency === opt.value
                    ? 'border-violet-500/50 bg-violet-500/10 text-violet-400'
                    : 'border-border text-muted-foreground hover:border-border/80'
                }`}
              >
                <input
                  type="radio"
                  name="frequency"
                  value={opt.value}
                  checked={signalSources.frequency === opt.value}
                  onChange={() => updateSignalSources({ frequency: opt.value })}
                  className="sr-only"
                />
                {opt.label}
              </label>
            ))}
          </div>
        </div>
      </Section>

      {/* Section 3: Notifications */}
      <Section icon={<Bell className="h-4 w-4" />} title="Notifications">
        <div className="divide-y divide-border/50">
          <Toggle
            checked={notifications.newOpportunity}
            onChange={(v) => updateNotifications({ newOpportunity: v })}
            label="New opportunity detected"
            description="Alert when a high-confidence opportunity is predicted"
          />
          <Toggle
            checked={notifications.highPriorityAction}
            onChange={(v) => updateNotifications({ highPriorityAction: v })}
            label="High-priority action due"
            description="Remind when a HIGH priority action is due soon"
          />
          <Toggle
            checked={notifications.emailReply}
            onChange={(v) => updateNotifications({ emailReply: v })}
            label="Email reply detected"
            description="Alert when a sent email gets a reply"
          />
        </div>
        <p className="text-xs text-muted-foreground pt-1">
          Notification preferences are stored locally. In-app alerts only for v1.0.
        </p>
      </Section>

      {/* Section 4: Connected Accounts */}
      <Section icon={<Mail className="h-4 w-4" />} title="Connected Accounts">
        <div className="flex items-center justify-between py-1">
          <div>
            <p className="text-sm font-medium text-foreground">Gmail</p>
            <p className="text-xs text-muted-foreground">
              {gmailConnected
                ? 'Connected — outreach emails can be sent via Gmail'
                : 'Not connected — connect to enable automated outreach'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div
              className={`flex items-center gap-1 text-xs font-medium ${
                gmailConnected ? 'text-emerald-400' : 'text-muted-foreground'
              }`}
            >
              {gmailConnected ? (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  Connected
                </>
              ) : (
                <>
                  <XCircle className="h-4 w-4" />
                  Not connected
                </>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleConnectGmail}
            >
              {gmailConnected ? 'Reconnect Gmail' : 'Connect Gmail'}
            </Button>
          </div>
        </div>
        {gmailMessage && (
          <div className="text-xs text-blue-400 bg-blue-500/10 border border-blue-500/30 rounded-lg px-3 py-2 mt-2 font-mono break-all">
            {gmailMessage}
          </div>
        )}
      </Section>
    </div>
  );
}
