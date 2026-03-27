export type Role = "owner" | "manager" | "salesperson" | "receptionist" | "trainer";

export interface User {
  id: string;
  gym_id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  job_title?: string | null;
  avatar_url?: string | null;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
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
  confidence_label: string;
  recommended_channel: string;
  cta_target: string;
  cta_label: string;
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

export interface Task {
  id: string;
  title: string;
  description: string | null;
  member_id: string | null;
  lead_id: string | null;
  assigned_to_user_id: string | null;
  member_name: string | null;
  lead_name: string | null;
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
export type ActuarSyncMode = "disabled" | "http_api" | "csv_export" | "assisted_rpa";
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

export interface BodyCompositionRangeValue {
  min: number | null;
  max: number | null;
}

export interface BodyCompositionOcrWarning {
  field: string | null;
  message: string;
  severity: OcrWarningSeverity;
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

export interface BodyCompositionEvaluation {
  id: string;
  gym_id: string;
  member_id: string;
  evaluation_date: string;
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
  ocr_warnings_json: BodyCompositionOcrWarning[] | null;
  needs_review: boolean;
  reviewed_manually: boolean;
  device_model: string | null;
  device_profile: string | null;
  parsed_from_image: boolean;
  ocr_source_file_ref: string | null;
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

export interface BodyCompositionEvaluationCreate {
  evaluation_date: string;
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
  ocr_warnings_json?: BodyCompositionOcrWarning[] | null;
  needs_review?: boolean;
  reviewed_manually?: boolean;
  device_model?: string | null;
  device_profile?: string | null;
  parsed_from_image?: boolean;
  ocr_source_file_ref?: string | null;
  measured_ranges_json?: Record<string, BodyCompositionRangeValue> | null;
}

export type BodyCompositionEvaluationUpdate = BodyCompositionEvaluationCreate;

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
