export type Role = "owner" | "manager" | "salesperson" | "receptionist" | "trainer";

export interface User {
  id: string;
  gym_id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  job_title?: string | null;
  work_shift?: "morning" | "afternoon" | "evening" | null;
  avatar_url?: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in: number;
}

export type RiskLevel = "green" | "yellow" | "red";

export interface AIAssistantPayload {
  summary: string;
  why_it_matters: string;
  next_best_action: string;
  suggested_message?: string | null;
  evidence: string[];
  provider: string;
  mode: string;
  fallback_used: boolean;
  manual_required: boolean;
  confidence_label: string;
  recommended_channel: string;
  cta_target: string;
  cta_label: string;
}

export type AITriageSourceDomain = "retention" | "onboarding";
export type AITriageApprovalState = "pending" | "approved" | "rejected";
export type AITriageSuggestionState = "suggested" | "reviewed";
export type AITriageExecutionState = "pending" | "blocked" | "prepared" | "queued" | "running" | "completed" | "failed";
export type AITriageOutcomeState = "pending" | "dismissed" | "positive" | "neutral" | "negative";
export type AITriageSafeActionType =
  | "create_task"
  | "assign_owner"
  | "open_follow_up"
  | "prepare_outbound_message"
  | "enqueue_approved_job";

export interface AITriageRecommendedOwner {
  user_id: string | null;
  role: string | null;
  label: string | null;
}

export interface AITriageRecommendation {
  id: string;
  source_domain: AITriageSourceDomain;
  source_entity_kind: string;
  source_entity_id: string;
  member_id: string | null;
  lead_id: string | null;
  subject_name: string;
  priority_score: number;
  priority_bucket: string;
  why_now_summary: string;
  why_now_details: string[];
  recommended_action: string;
  recommended_channel: string | null;
  recommended_owner: AITriageRecommendedOwner | null;
  suggested_message: string | null;
  expected_impact: string;
  operator_summary: string;
  primary_action_type: AITriageSafeActionType | string | null;
  primary_action_label: string | null;
  requires_explicit_approval: boolean;
  show_outcome_step: boolean;
  suggestion_state: AITriageSuggestionState | string;
  approval_state: AITriageApprovalState;
  execution_state: AITriageExecutionState | string;
  outcome_state: AITriageOutcomeState | string;
  metadata: Record<string, unknown>;
  last_refreshed_at: string;
}

export interface AITriageApprovalUpdateInput {
  decision: "approved" | "rejected";
  note?: string | null;
}

export interface AITriageSafeActionInput {
  action: AITriageSafeActionType;
  assigned_to_user_id?: string | null;
  owner_role?: string | null;
  owner_label?: string | null;
  note?: string | null;
  operator_note?: string | null;
  auto_approve?: boolean;
  confirm_approval?: boolean;
}

export interface AITriageSafeActionResult {
  recommendation: AITriageRecommendation;
  action: AITriageSafeActionType | string;
  supported: boolean;
  detail: string;
  task_id: string | null;
  follow_up_url: string | null;
  prepared_message: string | null;
  metadata: Record<string, unknown>;
}

export interface AITriageOutcomeUpdateInput {
  outcome: "pending" | "positive" | "neutral" | "negative";
  note?: string | null;
}

export interface AITriageMetricsSummary {
  total_active: number;
  pending_approval_total: number;
  approved_total: number;
  rejected_total: number;
  prepared_action_total: number;
  positive_outcome_total: number;
  neutral_outcome_total: number;
  negative_outcome_total: number;
  acceptance_rate: number | null;
  average_time_to_approval_seconds: number | null;
  median_time_to_approval_seconds: number | null;
  same_day_prepared_total: number;
}

export type WorkQueueSourceType = "task" | "ai_triage";
export type WorkQueueState = "do_now" | "awaiting_outcome" | "done";
export type WorkQueueOutcome =
  | "responded"
  | "no_response"
  | "scheduled_assessment"
  | "will_return"
  | "not_interested"
  | "invalid_number"
  | "postponed"
  | "forwarded_to_trainer"
  | "forwarded_to_reception"
  | "forwarded_to_manager"
  | "payment_confirmed"
  | "payment_promised"
  | "payment_link_sent"
  | "charge_disputed"
  | "completed";

export interface WorkQueueItem {
  source_type: WorkQueueSourceType;
  source_id: string;
  subject_name: string;
  member_id: string | null;
  lead_id: string | null;
  subject_phone: string | null;
  domain: "retention" | "onboarding" | "assessment" | "commercial" | "finance" | "manual" | string;
  severity: "critical" | "high" | "medium" | "low" | "info" | string;
  preferred_shift: "morning" | "afternoon" | "evening" | "unassigned" | string | null;
  reason: string;
  primary_action_label: string;
  primary_action_type: string;
  suggested_message: string | null;
  requires_confirmation: boolean;
  state: WorkQueueState;
  due_at: string | null;
  assigned_to_user_id: string | null;
  context_path: string | null;
  outcome_state: string | null;
}

export interface WorkQueueActionResult {
  item: WorkQueueItem;
  detail: string;
  prepared_message: string | null;
  context_path: string | null;
  task_id?: string | null;
  metadata: Record<string, unknown>;
}

export interface Member {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  birthdate?: string | null;
  status: "active" | "paused" | "cancelled";
  plan_name: string;
  monthly_fee: number;
  join_date: string;
  preferred_shift: string | null;
  nps_last_score: number;
  loyalty_months: number;
  risk_score: number;
  risk_level: RiskLevel;
  last_checkin_at: string | null;
  extra_data?: Record<string, unknown>;
  suggested_action?: string | null;
  onboarding_status?: 'active' | 'completed' | 'at_risk' | null;
  onboarding_score?: number | null;
  created_at: string;
  updated_at: string;
}

export type MemberIntelligenceSignalSeverity = "neutral" | "info" | "success" | "warning" | "danger";

export interface MemberIntelligenceSignal {
  key: string;
  label: string;
  value: string | number | boolean | null;
  severity: MemberIntelligenceSignalSeverity;
  source: string;
  observed_at: string | null;
}

export interface LeadToMemberIntelligenceContext {
  version: "lead-member-context-v1" | string;
  generated_at: string;
  member: {
    member_id: string;
    full_name: string;
    email: string | null;
    phone: string | null;
    status: string;
    plan_name: string | null;
    monthly_fee: number | null;
    join_date: string | null;
    preferred_shift: string | null;
    assigned_user_id: string | null;
    is_vip: boolean;
  };
  lead: {
    lead_id: string | null;
    source: string | null;
    stage: string | null;
    owner_id: string | null;
    last_contact_at: string | null;
    estimated_value: number | null;
    acquisition_cost: number | null;
    converted: boolean;
    notes_count: number;
  } | null;
  consent: {
    lgpd: boolean | null;
    communication: boolean | null;
    image: boolean | null;
    contract: boolean | null;
    source: string;
    missing: string[];
  };
  lifecycle: {
    onboarding_status: string | null;
    onboarding_score: number | null;
    retention_stage: string | null;
    churn_type: string | null;
    loyalty_months: number | null;
  };
  activity: {
    last_checkin_at: string | null;
    days_without_checkin: number | null;
    checkins_30d: number;
    checkins_90d: number;
    preferred_shift: string | null;
  };
  assessment: {
    assessments_total: number;
    latest_assessment_at: string | null;
    body_composition_total: number;
    latest_body_composition_at: string | null;
    latest_body_fat_percent: number | null;
    latest_muscle_mass_kg: number | null;
    latest_weight_kg: number | null;
  };
  operations: {
    open_tasks_total: number;
    overdue_tasks_total: number;
    next_task_due_at: string | null;
    latest_completed_task_at: string | null;
  };
  risk: {
    risk_level: string | null;
    risk_score: number | null;
    open_alerts_total: number;
    nps_last_score: number | null;
  };
  signals: MemberIntelligenceSignal[];
  data_quality_flags: string[];
}

export interface Lead {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  source: string;
  stage: "new" | "contact" | "visit" | "trial" | "proposal" | "meeting_scheduled" | "proposal_sent" | "won" | "lost";
  estimated_value: number;
  acquisition_cost: number;
  owner_id: string | null;
  last_contact_at: string | null;
  converted_member_id: string | null;
  notes: Array<string | Record<string, unknown>>;
  lost_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface AcquisitionQualification {
  score: number;
  label: "hot" | "warm" | "cold" | string;
  next_action: string;
  recommended_stage: Lead["stage"] | string;
  reasons: string[];
  missing_fields: string[];
}

export interface AcquisitionLeadSummary {
  lead_id: string;
  full_name: string;
  source: string | null;
  channel: string | null;
  campaign: string | null;
  desired_goal: string | null;
  preferred_shift: string | null;
  qualification_score: number | null;
  qualification_label: string | null;
  next_action: string | null;
  has_trial_booking: boolean;
  next_booking_at: string | null;
  consent_lgpd: boolean | null;
  consent_communication: boolean | null;
  reasons: string[];
  missing_fields: string[];
}

export interface AcquisitionCaptureResponse {
  lead: Lead;
  booking: unknown | null;
  qualification: AcquisitionQualification;
  summary: AcquisitionLeadSummary;
}

export type GrowthAudienceId =
  | "conversion_hot_leads"
  | "conversion_stale_leads"
  | "reactivation_inactive_members"
  | "renewal_attention"
  | "upsell_promoters"
  | "nps_recovery";

export type GrowthChannel = "whatsapp" | "email" | "task" | "crm_note" | "kommo";

export interface GrowthOpportunity {
  id: string;
  audience_id: GrowthAudienceId;
  subject_type: "lead" | "member";
  subject_id: string;
  display_name: string;
  contact: string | null;
  preferred_shift: string | null;
  stage_or_status: string | null;
  score: number;
  priority: "low" | "medium" | "high" | "urgent";
  channel: GrowthChannel;
  action_label: string;
  reason: string;
  suggested_message: string;
  next_step: string;
  consent_required: boolean;
  consent_ok: boolean;
  source_tags: string[];
  metadata: Record<string, unknown>;
}

export interface GrowthAudience {
  id: GrowthAudienceId;
  label: string;
  objective: string;
  count: number;
  priority: "low" | "medium" | "high" | "urgent";
  recommended_channel: GrowthChannel;
  cta_label: string;
  summary: string;
  experiment_hint: string;
  items: GrowthOpportunity[];
}

export interface GrowthOpportunityPrepared {
  opportunity_id: string;
  prepared_action: string;
  action_label: string;
  channel: GrowthChannel;
  target_name: string;
  message: string;
  whatsapp_url: string | null;
  task_id: string | null;
  crm_note_created: boolean;
  kommo_status: string | null;
  warnings: string[];
}

export type ConsentType = "lgpd" | "communication" | "image" | "contract" | "terms";
export type ConsentStatus = "accepted" | "revoked" | "expired" | "missing";

export interface MemberConsentCurrent {
  consent_type: ConsentType | string;
  status: ConsentStatus | string;
  accepted: boolean;
  source: string | null;
  document_title: string | null;
  document_version: string | null;
  signed_at: string | null;
  revoked_at: string | null;
  expires_at: string | null;
  record_id: string | null;
  missing: boolean;
  expired: boolean;
}

export interface MemberConsentRecord {
  id: string;
  gym_id: string;
  member_id: string;
  consent_type: ConsentType | string;
  status: ConsentStatus | string;
  source: string;
  document_title: string | null;
  document_version: string | null;
  evidence_ref: string | null;
  notes: string | null;
  signed_at: string | null;
  revoked_at: string | null;
  expires_at: string | null;
  extra_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MemberConsentSummary {
  member_id: string;
  current: MemberConsentCurrent[];
  records: MemberConsentRecord[];
  missing: string[];
  expired: string[];
  updated_at: string;
}

export interface Task {
  id: string;
  title: string;
  description: string | null;
  member_id: string | null;
  lead_id: string | null;
  assigned_to_user_id: string | null;
  member_name: string | null;
  lead_name: string | null;
  preferred_shift?: string | null;
  priority: "low" | "medium" | "high" | "urgent";
  status: "todo" | "doing" | "done" | "cancelled";
  kanban_column: string;
  due_date: string | null;
  completed_at: string | null;
  suggested_message: string | null;
  extra_data?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface RevenuePoint {
  month: string;
  value: number;
}

export interface ChurnPoint {
  month: string;
  churn_rate: number;
}

export interface LTVPoint {
  month: string;
  ltv: number;
}

export interface GrowthPoint {
  month: string;
  growth_mom: number;
}

export interface ExecutiveDashboard {
  total_members: number;
  active_members: number;
  mrr: number;
  churn_rate: number;
  nps_avg: number;
  risk_distribution: {
    green: number;
    yellow: number;
    red: number;
  };
}

export interface WeeklySummary {
  checkins_this_week: number;
  checkins_last_week: number;
  checkins_delta_pct: number;
  new_registrations: number;
  new_at_risk: number;
  mrr_at_risk: number;
  total_active: number;
}

export interface HeatmapPoint {
  weekday: number;
  hour_bucket: number;
  total_checkins: number;
}

export interface ConversionBySource {
  source: string;
  total: number;
  won: number;
  conversion_rate: number;
}

export interface ProjectionPoint {
  horizon_months: number;
  projected_revenue: number;
}

export type FinancialEntryType = "receivable" | "payable" | "cash_in" | "cash_out";
export type FinancialEntryStatus = "open" | "paid" | "overdue" | "cancelled";

export interface FinancialEntry {
  id: string;
  gym_id: string;
  member_id: string | null;
  lead_id: string | null;
  created_by_user_id: string | null;
  entry_type: FinancialEntryType | string;
  status: FinancialEntryStatus | string;
  category: string;
  description: string | null;
  amount: number;
  due_date: string | null;
  occurred_at: string | null;
  paid_at: string | null;
  source: string;
  external_ref: string | null;
  notes: string | null;
  extra_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export type TaskEventType =
  | "comment"
  | "execution_started"
  | "contact_attempt"
  | "outcome_recorded"
  | "snoozed"
  | "status_changed"
  | "reassigned"
  | "forwarded"
  | "delinquency_stage_updated";

export type TaskContactChannel = "whatsapp" | "call" | "in_person" | "other";

export interface TaskEvent {
  id: string;
  gym_id: string;
  task_id: string;
  member_id: string | null;
  lead_id: string | null;
  user_id: string | null;
  event_type: TaskEventType | string;
  outcome: WorkQueueOutcome | string | null;
  contact_channel: TaskContactChannel | string | null;
  note: string | null;
  scheduled_for: string | null;
  metadata_json: Record<string, unknown>;
  created_at: string;
}

export interface TaskMetricsOwner {
  user_id: string | null;
  owner_name: string;
  open_total: number;
  overdue_total: number;
  completed_7d_total: number;
}

export interface TaskMetricsBreakdown {
  key: string;
  label: string;
  total: number;
}

export interface TaskMetrics {
  open_total: number;
  overdue_total: number;
  due_today_total: number;
  completed_today_total: number;
  completed_7d_total: number;
  avg_completion_hours: number | null;
  on_time_rate_pct: number | null;
  by_owner: TaskMetricsOwner[];
  by_source: TaskMetricsBreakdown[];
  by_outcome: TaskMetricsBreakdown[];
}

export interface FinancialEntryPayload {
  entry_type: FinancialEntryType;
  status?: FinancialEntryStatus;
  category: string;
  description?: string;
  amount: number;
  due_date?: string;
  occurred_at?: string;
  paid_at?: string;
  member_id?: string;
  lead_id?: string;
  source?: string;
  external_ref?: string;
  notes?: string;
  extra_data?: Record<string, unknown>;
}

export type DelinquencyStage = "d1" | "d3" | "d7" | "d15" | "d30";

export interface DelinquencyItem {
  member_id: string;
  member_name: string;
  member_phone: string | null;
  member_email: string | null;
  plan_name: string | null;
  preferred_shift: string | null;
  overdue_amount: number;
  overdue_entries_count: number;
  oldest_due_date: string;
  days_overdue: number;
  stage: DelinquencyStage;
  severity: string;
  primary_action_label: string;
  suggested_message: string;
  open_task_id: string | null;
}

export interface DelinquencyStageSummary {
  stage: DelinquencyStage;
  label: string;
  members_count: number;
  overdue_amount: number;
}

export interface DelinquencySummary {
  overdue_amount: number;
  delinquent_members_count: number;
  open_task_count: number;
  recovered_30d: number;
  by_stage: DelinquencyStageSummary[];
  generated_at: string;
}

export interface DelinquencyMaterializeResult {
  created_count: number;
  updated_count: number;
  skipped_count: number;
  normalized_entries_count: number;
  items_count: number;
}

export interface DREBasic {
  revenue: number;
  expenses: number;
  net_result: number;
  margin_pct: number | null;
}

export interface FinancialDashboard {
  monthly_revenue: RevenuePoint[];
  delinquency_rate: number;
  projections: ProjectionPoint[];
  daily_cash_in: number;
  daily_cash_out: number;
  daily_net_cash: number;
  open_receivables: number;
  open_payables: number;
  overdue_receivables: number;
  overdue_payables: number;
  revenue_at_risk: number;
  dre_basic: DREBasic;
  data_quality_flags: string[];
}

export interface BICohortPoint {
  month: string;
  joined: number;
  active: number;
  retained_rate: number;
  mrr: number;
}

export interface BIFollowUpImpact {
  prepared_actions_30d: number;
  positive_outcomes_30d: number;
  completed_followups_30d: number;
  retention_contacts_30d: number;
  acceptance_rate: number | null;
  data_quality: string;
}

export interface BIFoundationDashboard {
  generated_at: string;
  cohort: BICohortPoint[];
  ltv: LTVPoint[];
  forecast: ProjectionPoint[];
  revenue_at_risk: number;
  revenue_at_risk_members: number;
  follow_up_impact: BIFollowUpImpact;
  data_quality_flags: string[];
}

export interface NPSEvolutionPoint {
  month: string;
  average_score: number;
  responses: number;
}

export interface InAppNotification {
  id: string;
  member_id: string | null;
  user_id: string | null;
  title: string;
  message: string;
  category: string;
  read_at: string | null;
  created_at: string;
  extra_data: Record<string, unknown>;
}

export interface RiskAlert {
  id: string;
  member_id: string;
  score: number;
  level: RiskLevel;
  reasons: Record<string, unknown>;
  action_history: Array<Record<string, unknown>>;
  automation_stage: string | null;
  resolved: boolean;
  created_at: string;
}

export interface ImportErrorEntry {
  row_number: number;
  reason: string;
  payload: Record<string, unknown>;
}

export interface MissingMemberEntry {
  name: string;
  occurrences: number;
  sample_plan: string | null;
}

export interface ImportSummary {
  imported: number;
  updated_existing: number;
  skipped_duplicates: number;
  ignored_rows: number;
  provisional_members_created: number;
  provisional_members: string[];
  missing_members: MissingMemberEntry[];
  errors: ImportErrorEntry[];
}

export interface ImportPreviewRow {
  row_number: number;
  action: string;
  preview: Record<string, unknown>;
}

export type ImportSourceColumnStatus = "recognized" | "mapped" | "needs_mapping" | "ignored" | "conflict";

export interface ImportPreviewSourceColumn {
  source_key: string;
  source_label: string;
  status: ImportSourceColumnStatus;
  suggested_target: string | null;
  applied_target: string | null;
  sample_values: string[];
  can_ignore: boolean;
}

export interface ImportPreview {
  preview_kind: string;
  total_rows: number;
  valid_rows: number;
  would_create: number;
  would_update: number;
  would_skip: number;
  ignored_rows: number;
  provisional_members_possible: number;
  recognized_columns: string[];
  unrecognized_columns: string[];
  missing_members: MissingMemberEntry[];
  warnings: string[];
  sample_rows: ImportPreviewRow[];
  mapping_required: boolean;
  can_confirm: boolean;
  resolved_mappings: Record<string, string>;
  ignored_columns: string[];
  conflicting_targets: string[];
  blocking_issues: string[];
  source_columns: ImportPreviewSourceColumn[];
  errors: ImportErrorEntry[];
}

export type EvaluationSource = "tezewa" | "manual" | "ocr_receipt" | "device_import" | "actuar_sync";
export type ActuarSyncMode = "disabled" | "http_api" | "csv_export" | "assisted_rpa" | "local_bridge";
export type ActuarSyncStatus =
  | "draft"
  | "saved"
  | "sync_pending"
  | "syncing"
  | "synced_to_actuar"
  | "sync_failed"
  | "needs_review"
  | "manual_sync_required";
export type ActuarSyncJobStatus = "pending" | "processing" | "synced" | "failed" | "needs_review" | "cancelled";
export type ActuarSyncAttemptStatus = "started" | "succeeded" | "failed";
export type OcrWarningSeverity = "warning" | "critical";
export type BodyCompositionSex = "male" | "female";
export type BodyCompositionDataQualityFlag =
  | "missing_body_fat_percent"
  | "missing_muscle_mass"
  | "suspect_bmi"
  | "ocr_low_confidence"
  | "manually_review_required";
export type BodyCompositionTrend = "up" | "down" | "stable" | "insufficient";
export type BodyCompositionRangeStatus = "low" | "adequate" | "high" | "unknown";
export type BodyCompositionInsightTone = "positive" | "warning" | "neutral";

export interface BodyCompositionRangeValue {
  min: number | null;
  max: number | null;
}

export interface BodyCompositionOcrWarning {
  field: string | null;
  message: string;
  severity: OcrWarningSeverity;
}

export interface BodyCompositionReportHeader {
  member_name: string;
  gym_name: string | null;
  trainer_name: string | null;
  measured_at: string;
  age_years: number | null;
  sex: BodyCompositionSex | null;
  height_cm: number | null;
  weight_kg: number | null;
}

export interface BodyCompositionMetricCard {
  key: string;
  label: string;
  value: number | null;
  unit: string | null;
  formatted_value: string;
  delta_absolute: number | null;
  delta_percent: number | null;
  trend: BodyCompositionTrend;
}

export interface BodyCompositionReferenceMetric {
  key: string;
  label: string;
  value: number | null;
  unit: string | null;
  formatted_value: string;
  reference_min: number | null;
  reference_max: number | null;
  status: BodyCompositionRangeStatus;
  hint: string | null;
}

export interface BodyCompositionComparisonRow {
  key: string;
  label: string;
  unit: string | null;
  previous_value: number | null;
  current_value: number | null;
  previous_formatted: string;
  current_formatted: string;
  difference_absolute: number | null;
  difference_percent: number | null;
  trend: BodyCompositionTrend;
}

export interface BodyCompositionHistoryPoint {
  evaluation_id: string;
  measured_at: string;
  evaluation_date: string;
  value: number | null;
}

export interface BodyCompositionHistorySeries {
  key: string;
  label: string;
  unit: string | null;
  points: BodyCompositionHistoryPoint[];
}

export interface BodyCompositionInsight {
  key: string;
  title: string;
  message: string;
  tone: BodyCompositionInsightTone;
  reasons: string[];
}

export interface BodyCompositionReport {
  header: BodyCompositionReportHeader;
  current_evaluation_id: string;
  previous_evaluation_id: string | null;
  reviewed_manually: boolean;
  parsing_confidence: number | null;
  data_quality_flags: BodyCompositionDataQualityFlag[];
  primary_cards: BodyCompositionMetricCard[];
  composition_metrics: BodyCompositionReferenceMetric[];
  muscle_fat_metrics: BodyCompositionReferenceMetric[];
  risk_metrics: BodyCompositionReferenceMetric[];
  goal_metrics: BodyCompositionReferenceMetric[];
  comparison_rows: BodyCompositionComparisonRow[];
  history_series: BodyCompositionHistorySeries[];
  insights: BodyCompositionInsight[];
  teacher_notes: string | null;
  methodological_note: string;
  segmental_analysis_available: boolean;
}

export interface BodyCompositionTrainingFocus {
  primary_goal: string;
  secondary_goal: string;
  suggested_focuses: string[];
  cautions: string[];
}

export interface BodyCompositionSyncAttempt {
  id: string;
  gym_id: string;
  sync_job_id: string;
  status: ActuarSyncAttemptStatus;
  started_at: string;
  finished_at: string | null;
  action_log_json: Array<Record<string, unknown>> | unknown[] | null;
  screenshot_path: string | null;
  page_html_path: string | null;
  error_code: string | null;
  error_message: string | null;
  worker_id: string | null;
}

export interface ActuarSyncJob {
  id: string;
  gym_id: string;
  member_id: string;
  body_composition_evaluation_id: string;
  job_type: "body_composition_push";
  status: ActuarSyncJobStatus;
  error_code: string | null;
  error_message: string | null;
  retry_count: number;
  max_retries: number;
  next_retry_at: string | null;
  locked_at: string | null;
  locked_by: string | null;
  synced_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface LeadNoteEntry {
  id: string;
  text: string;
  type: string;
  channel: string | null;
  outcome: string | null;
  created_at: string | null;
  author_name: string | null;
  author_role: string | null;
  legacy: boolean;
}

export interface ActuarMemberLink {
  id: string;
  member_id: string;
  actuar_external_id: string | null;
  actuar_search_name: string | null;
  actuar_search_birthdate: string | null;
  linked_at: string | null;
  linked_by_user_id: string | null;
  match_confidence: number | null;
  is_active: boolean;
}

export interface ActuarFieldMapping {
  field: string;
  actuar_field: string | null;
  value: string | number | boolean | null;
  classification: "critical_direct" | "critical_derived" | "non_critical_direct" | "unsupported" | "text_note_only";
  required: boolean;
  supported: boolean;
}

export interface BodyCompositionManualSyncSummary {
  evaluation_id: string;
  member_id: string;
  sync_status: ActuarSyncStatus;
  training_ready: boolean;
  critical_fields: ActuarFieldMapping[];
  summary_text: string;
}

export interface ActuarSyncQueueItem {
  evaluation_id: string;
  member_id: string;
  member_name: string;
  evaluation_date: string;
  sync_status: ActuarSyncStatus;
  training_ready: boolean;
  error_code: string | null;
  error_message: string | null;
  next_retry_at: string | null;
  current_job: ActuarSyncJob | null;
}

export interface BodyCompositionActuarSyncStatus {
  evaluation_id: string;
  member_id: string;
  sync_mode: ActuarSyncMode;
  sync_status: ActuarSyncStatus;
  training_ready: boolean;
  sync_required_for_training: boolean;
  external_id: string | null;
  last_synced_at: string | null;
  last_attempt_at: string | null;
  last_error_code: string | null;
  last_error: string | null;
  can_retry: boolean;
  critical_fields: ActuarFieldMapping[];
  unsupported_fields: ActuarFieldMapping[];
  fallback_manual_summary: BodyCompositionManualSyncSummary;
  current_job: ActuarSyncJob | null;
  attempts: BodyCompositionSyncAttempt[];
  member_link: ActuarMemberLink | null;
}

export interface ActuarSettings {
  actuar_enabled: boolean;
  actuar_auto_sync_body_composition: boolean;
  actuar_base_url: string | null;
  actuar_username: string | null;
  actuar_has_password: boolean;
  environment_enabled: boolean;
  environment_sync_mode: ActuarSyncMode | "disabled";
  effective_sync_mode: ActuarSyncMode | "disabled";
  automatic_sync_ready: boolean;
  bridge_device_count: number;
  bridge_online_device_count: number;
  bridge_devices: ActuarBridgeDevice[];
}

export interface ActuarConnectionTestResult {
  success: boolean;
  provider: string;
  effective_sync_mode: ActuarSyncMode | "disabled";
  automatic_sync_ready: boolean;
  message: string;
  detail: string | null;
}

export interface ActuarSettingsUpdateInput {
  actuar_enabled: boolean;
  actuar_auto_sync_body_composition: boolean;
  actuar_base_url?: string | null;
  actuar_username?: string | null;
  actuar_password?: string | null;
  clear_password?: boolean;
}

export interface ActuarBridgeDevice {
  id: string;
  gym_id: string;
  device_name: string;
  status: "pairing" | "online" | "offline" | "revoked";
  bridge_version: string | null;
  browser_name: string | null;
  paired_at: string | null;
  last_seen_at: string | null;
  last_job_claimed_at: string | null;
  last_job_completed_at: string | null;
  last_error_code: string | null;
  last_error_message: string | null;
  revoked_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ActuarBridgePairingCode {
  device_id: string;
  pairing_code: string;
  expires_at: string;
}

export interface KommoSettings {
  kommo_enabled: boolean;
  kommo_base_url: string | null;
  kommo_has_access_token: boolean;
  kommo_default_pipeline_id: string | null;
  kommo_default_stage_id: string | null;
  kommo_default_responsible_user_id: string | null;
  automatic_handoff_ready: boolean;
}

export interface KommoConnectionTestResult {
  success: boolean;
  automatic_handoff_ready: boolean;
  message: string;
  detail: string | null;
  base_url: string | null;
}

export interface KommoSettingsUpdateInput {
  kommo_enabled: boolean;
  kommo_base_url?: string | null;
  kommo_access_token?: string | null;
  kommo_default_pipeline_id?: string | null;
  kommo_default_stage_id?: string | null;
  kommo_default_responsible_user_id?: string | null;
  clear_access_token?: boolean;
}

export interface BodyCompositionEvaluation {
  id: string;
  gym_id: string;
  member_id: string;
  evaluation_date: string;
  measured_at: string | null;
  age_years: number | null;
  sex: BodyCompositionSex | null;
  height_cm: number | null;
  weight_kg: number | null;
  body_fat_kg: number | null;
  body_fat_percent: number | null;
  waist_hip_ratio: number | null;
  fat_free_mass_kg: number | null;
  inorganic_salt_kg: number | null;
  protein_kg: number | null;
  body_water_kg: number | null;
  lean_mass_kg: number | null;
  muscle_mass_kg: number | null;
  skeletal_muscle_kg: number | null;
  body_water_percent: number | null;
  visceral_fat_level: number | null;
  bmi: number | null;
  basal_metabolic_rate_kcal: number | null;
  target_weight_kg: number | null;
  weight_control_kg: number | null;
  muscle_control_kg: number | null;
  fat_control_kg: number | null;
  total_energy_kcal: number | null;
  physical_age: number | null;
  health_score: number | null;
  source: EvaluationSource;
  notes: string | null;
  report_file_url: string | null;
  raw_ocr_text: string | null;
  ocr_confidence: number | null;
  parsing_confidence: number | null;
  ocr_warnings_json: BodyCompositionOcrWarning[] | null;
  data_quality_flags_json: BodyCompositionDataQualityFlag[] | null;
  needs_review: boolean;
  reviewed_manually: boolean;
  reviewer_user_id: string | null;
  device_model: string | null;
  device_profile: string | null;
  parsed_from_image: boolean;
  ocr_source_file_ref: string | null;
  import_batch_id: string | null;
  measured_ranges_json: Record<string, BodyCompositionRangeValue> | null;
  ai_coach_summary: string | null;
  ai_member_friendly_summary: string | null;
  ai_risk_flags_json: string[] | null;
  ai_training_focus_json: BodyCompositionTrainingFocus | null;
  ai_generated_at: string | null;
  actuar_sync_status: ActuarSyncStatus;
  actuar_sync_mode: ActuarSyncMode;
  actuar_external_id: string | null;
  actuar_last_synced_at: string | null;
  actuar_last_error: string | null;
  sync_required_for_training: boolean;
  sync_last_attempt_at: string | null;
  sync_last_success_at: string | null;
  sync_last_error_code: string | null;
  sync_last_error_message: string | null;
  actuar_sync_job_id: string | null;
  training_ready: boolean;
  created_at: string;
  updated_at: string;
  assistant?: AIAssistantPayload | null;
}

export interface BodyCompositionWhatsAppDispatch {
  log_id: string;
  member_id: string;
  evaluation_id: string;
  status: string;
  recipient: string;
  pdf_filename: string | null;
  error_detail: string | null;
}

export interface BodyCompositionKommoDispatch {
  member_id: string;
  evaluation_id: string;
  status: string;
  lead_id: string | null;
  contact_id: string | null;
  task_id: string | null;
  detail: string | null;
}

export interface BodyCompositionEvaluationCreate {
  evaluation_date: string;
  measured_at?: string | null;
  age_years?: number | null;
  sex?: BodyCompositionSex | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  body_fat_kg?: number | null;
  body_fat_percent?: number | null;
  waist_hip_ratio?: number | null;
  fat_free_mass_kg?: number | null;
  inorganic_salt_kg?: number | null;
  protein_kg?: number | null;
  body_water_kg?: number | null;
  lean_mass_kg?: number | null;
  muscle_mass_kg?: number | null;
  skeletal_muscle_kg?: number | null;
  body_water_percent?: number | null;
  visceral_fat_level?: number | null;
  bmi?: number | null;
  basal_metabolic_rate_kcal?: number | null;
  target_weight_kg?: number | null;
  weight_control_kg?: number | null;
  muscle_control_kg?: number | null;
  fat_control_kg?: number | null;
  total_energy_kcal?: number | null;
  physical_age?: number | null;
  health_score?: number | null;
  source?: EvaluationSource;
  notes?: string | null;
  report_file_url?: string | null;
  raw_ocr_text?: string | null;
  ocr_confidence?: number | null;
  parsing_confidence?: number | null;
  ocr_warnings_json?: BodyCompositionOcrWarning[] | null;
  needs_review?: boolean;
  reviewed_manually?: boolean;
  device_model?: string | null;
  device_profile?: string | null;
  parsed_from_image?: boolean;
  ocr_source_file_ref?: string | null;
  import_batch_id?: string | null;
  measured_ranges_json?: Record<string, BodyCompositionRangeValue> | null;
}

export type BodyCompositionEvaluationUpdate = BodyCompositionEvaluationCreate;
export type BodyCompositionEvaluationReviewInput = BodyCompositionEvaluationCreate;

export interface SalesHistoryItem {
  kind: string;
  channel: string | null;
  title: string;
  detail: string | null;
  occurred_at: string;
  metadata: Record<string, unknown>;
}

export interface SalesArgument {
  title: string;
  body: string;
  usage: string;
}

export interface SalesBrief {
  profile: {
    lead_id: string;
    full_name: string;
    email: string | null;
    phone: string | null;
    source: string;
    stage: Lead["stage"];
    gym_name: string | null;
    city: string | null;
    estimated_members: number | null;
    avg_monthly_fee: number | null;
    current_management_system: string | null;
  };
  diagnosis: {
    has_diagnosis: boolean;
    message: string | null;
    red_total: number;
    yellow_total: number;
    mrr_at_risk: number;
    annual_loss_projection: number;
    estimated_recovered_members: number;
    estimated_preserved_annual_revenue: number;
  };
  history: SalesHistoryItem[];
  ai_arguments: SalesArgument[];
  next_step_recommended: string;
}

export interface KnownObjection {
  summary: string;
  response_text: string;
  source: string;
}

export interface CallScript {
  lead_id: string;
  opening: string;
  qualification_questions: string[];
  presentation_points: string[];
  objections: KnownObjection[];
  closing: string;
  quick_responses: Record<string, string>;
}

export interface BookingStatus {
  has_booking: boolean;
  booking_id: string | null;
  scheduled_for: string | null;
  status: string | null;
  provider_name: string | null;
}
