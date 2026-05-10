export type CompanyProfile = {
  id: string
  name: string
  description?: string | null
  capabilities: string[]
  naics_codes: string[]
  certifications: string[]
  location?: string | null
  small_business_status: boolean
  clearance_status?: string | null
  preferred_role: 'prime' | 'sub' | 'either'
  created_at: string
  updated_at?: string | null
}

export type RunStatus = 'pending' | 'running' | 'complete' | 'partial' | 'failed'

export type TraceEvent = {
  type: string
  ts?: string
  run_id?: string
  step_id?: string
  label?: string
  tool?: string
  decision?: string
  score?: number
  summary?: string
  input?: Record<string, unknown>
  output?: Record<string, unknown> | null
  error?: string | null
  latency_ms?: number
  cost_usd?: number
  [key: string]: unknown
}

export type AgentRun = {
  id: string
  goal: string
  status: RunStatus
  steps: TraceEvent[]
  opportunities: string[]
  selected_opportunity_id?: string | null
  action_package_id?: string | null
  company_profile_id?: string | null
  completed_at?: string | null
  created_at: string
}

export type Opportunity = {
  id: string
  slug: string
  title: string
  agency: string
  due_date?: string | null
  set_aside?: string | null
  naics?: string | null
  description?: string | null
  source_url?: string | null
}

export type Decision = 'strong_pursue' | 'pursue' | 'maybe' | 'reject'

export type ExtractedRequirement = {
  id: string
  type: string
  title: string
  value?: string
  description?: string
  confidence: 'high' | 'medium' | 'low' | 'unknown'
  evidence_snippet?: string
  source_document?: string
  page_number?: number | null
  is_blocker: boolean
}

export type FitScore = {
  total_score: number
  decision: Decision
  confidence: 'high' | 'medium' | 'low'
  strengths: string[]
  weaknesses: string[]
  blockers: string[]
}

export type RiskFlag = {
  id: string
  category: string
  severity: 'critical_blocker' | 'major_risk' | 'moderate_risk' | 'minor_concern'
  title: string
  description: string
  evidence?: string
  mitigation?: string
  requires_human_review: boolean
}

export type ActionPackage = {
  id: string
  opportunity_id: string
  company_profile_id: string
  executive_summary: string
  decision: Decision
  fit_score: number
  fit_rationale: string
  compliance_matrix: Array<{
    requirement: string
    status: string
    evidence: string
    next_action: string
    owner: string
  }>
  risk_register: Array<{
    risk: string
    severity: string
    explanation: string
    mitigation: string
  }>
  proposal_checklist: string[]
  timeline: Array<{ date: string; task: string; owner: string }>
  partner_suggestions: Array<{
    partner_type: string
    gap_solved: string
    why_needed: string
    outreach_angle: string
    confidence: string
  }> | null
  outreach_draft?: { subject: string; body: string } | null
  approval_required: string[]
  approved_at?: string | null
  approved_by?: string | null
  created_at: string
}

export type ApiKey = {
  id: string
  owner_profile_id: string
  name: string
  prefix: string
  scopes: string[]
  last_used_at?: string | null
  revoked_at?: string | null
  created_at: string
}

export type ApiKeyMint = {
  id: string
  name: string
  prefix: string
  plaintext_key: string
  created_at: string
}
