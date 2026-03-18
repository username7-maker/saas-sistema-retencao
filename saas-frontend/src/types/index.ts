export type Role = "owner" | "manager" | "salesperson" | "receptionist" | "trainer";

export interface User {
  id: string;
  gym_id: string;
  full_name: string;
  email: string;
  role: Role;
  is_active: boolean;
  created_at: string;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export type RiskLevel = "green" | "yellow" | "red";

export interface Member {
  id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
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
  notes: Array<string | { note: string; created_at?: string }>;
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
  skipped_duplicates: number;
  ignored_rows: number;
  provisional_members_created: number;
  provisional_members: string[];
  missing_members: MissingMemberEntry[];
  errors: ImportErrorEntry[];
}

export type EvaluationSource = "tezewa" | "manual" | "ocr_receipt" | "device_import" | "actuar_sync";
export type ActuarSyncMode = "disabled" | "http_api" | "csv_export" | "assisted_rpa";
export type ActuarSyncStatus = "disabled" | "pending" | "exported" | "synced" | "failed" | "skipped";
export type ActuarSyncAttemptStatus = "pending" | "processing" | "exported" | "synced" | "failed" | "skipped" | "disabled";
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
  body_composition_evaluation_id: string;
  sync_mode: ActuarSyncMode;
  provider: string;
  status: ActuarSyncAttemptStatus;
  error: string | null;
  payload_snapshot_json: Record<string, unknown> | unknown[] | null;
  created_at: string;
}

export interface BodyCompositionActuarSyncStatus {
  evaluation_id: string;
  sync_mode: ActuarSyncMode;
  sync_status: ActuarSyncStatus;
  external_id: string | null;
  last_synced_at: string | null;
  last_error: string | null;
  can_retry: boolean;
  attempts: BodyCompositionSyncAttempt[];
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
  created_at: string;
  updated_at: string;
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
