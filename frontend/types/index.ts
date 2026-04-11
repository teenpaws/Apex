export interface Signal {
  id: string;
  user_id: string;
  company_id: string;
  type: 'FUNDING' | 'EXEC_HIRE' | 'EXPANSION' | 'LAYOFF' | 'JOB_POSTING_PATTERN' | 'MA' | 'CONTRACT' | 'EARNINGS';
  source: string;
  title: string;
  description: string;
  signal_date: string;
  relevance_score: number;
  processed_at: string;
  is_duplicate: boolean;
  // UI-friendly fields (denormalized for display)
  company?: string;
  date?: string;
  linkedOpportunityIds?: string[];
}

export interface Opportunity {
  id: string;
  user_id: string;
  company_id: string;
  predicted_role: string;
  confidence: 'HIGH' | 'MEDIUM' | 'SPECULATIVE';
  timeline_weeks: number;
  why_fit: string;
  positioning_notes: string;
  predicted_salary_range?: string;
  fit_score: number;
  key_contact_id?: string;
  signal_ids: string[];
  status: 'PREDICTED' | 'APPROACHED' | 'INTERVIEWING' | 'CLOSED';
  created_at: string;
  updated_at: string;
  // UI-friendly fields
  company?: string;
  role?: string;
  timeline?: string;
  whyFit?: string;
  keyContact?: string;
  predictedSalary?: string;
}

export interface Action {
  id: string;
  user_id: string;
  opportunity_id: string;
  company_id: string;
  contact_id?: string;
  title: string;
  description: string;
  type: 'OUTREACH' | 'FOLLOW_UP' | 'RESEARCH' | 'CALL';
  priority: 'HIGH' | 'MEDIUM' | 'LOW';
  status: 'TODO' | 'IN_PROGRESS' | 'DONE' | 'SNOOZED';
  due_date: string;
  source_signal_id?: string;
  created_at: string;
  // UI-friendly fields
  company?: string;
  dueDate?: string;
  sourceSignalId?: string;
}

export interface Company {
  id: string;
  name: string;
  domain: string;
  industry: string;
  size_range: string;
  location: string;
  linkedin_url?: string;
  enrichment_json?: Record<string, unknown>;
  last_enriched_at?: string;
}

export interface Contact {
  id: string;
  company_id: string;
  name: string;
  title: string;
  linkedin_url?: string;
  email?: string;
  enrichment_json?: Record<string, unknown>;
  last_enriched_at?: string;
}

export interface CareerProfile {
  id: string;
  user_id: string;
  current_role: string;
  target_roles: string[];
  industries: string[];
  aspirations_text: string;
  updated_at: string;
}

export interface OutreachEmail {
  id: string;
  user_id: string;
  action_id: string;
  contact_id: string;
  subject: string;
  body: string;
  tone: 'PROFESSIONAL' | 'WARM' | 'DIRECT';
  draft_json?: Record<string, unknown>;
  sent_at?: string;
  gmail_message_id?: string;
  opened_at?: string;
  replied_at?: string;
  reply_detected_at?: string;
}

export interface AgentRun {
  id: string;
  user_id: string;
  agent_name: string;
  model_used: string;
  input_hash: string;
  output_hash: string;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  duration_ms: number;
  status: 'SUCCESS' | 'FAILED' | 'RETRIED';
  error_message?: string;
  created_at: string;
}

export interface DashboardStats {
  signals_this_week: number;
  new_opportunities: number;
  actions_completed: number;
  pipeline_stages: {
    signals: number;
    opportunities: number;
    actions: number;
    outreach: number;
  };
}

export interface ApiResponse<T> {
  data: T;
  error?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  per_page: number;
}

export interface RunStatus {
  run_id: string;
  status: 'queued' | 'running' | 'SUCCESS' | 'FAILED';
  progress?: number;
  result_id?: string;
  error?: string;
}
