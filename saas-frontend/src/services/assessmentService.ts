import { api } from "./api";
import type { ActuarSyncQueueItem, AIAssistantPayload, RiskLevel } from "../types";

export interface Assessment {
  id: string;
  gym_id: string;
  member_id: string;
  evaluator_id: string | null;
  assessment_number: number;
  assessment_date: string;
  next_assessment_due: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  bmi: number | null;
  body_fat_pct: number | null;
  lean_mass_kg: number | null;
  waist_cm: number | null;
  hip_cm: number | null;
  chest_cm: number | null;
  arm_cm: number | null;
  thigh_cm: number | null;
  resting_hr: number | null;
  blood_pressure_systolic: number | null;
  blood_pressure_diastolic: number | null;
  vo2_estimated: number | null;
  strength_score: number | null;
  flexibility_score: number | null;
  cardio_score: number | null;
  observations: string | null;
  ai_analysis: string | null;
  ai_recommendations: string | null;
  ai_risk_flags: string | null;
  extra_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AssessmentMini {
  id: string;
  assessment_number: number;
  assessment_date: string;
  next_assessment_due: string | null;
  weight_kg: number | null;
  bmi: number | null;
  body_fat_pct: number | null;
  strength_score: number | null;
  flexibility_score: number | null;
  cardio_score: number | null;
  ai_analysis: string | null;
}

export interface MemberGoal {
  id: string;
  gym_id: string;
  member_id: string;
  assessment_id: string | null;
  title: string;
  description: string | null;
  category: string;
  target_value: number | null;
  current_value: number;
  unit: string | null;
  target_date: string | null;
  status: string;
  progress_pct: number;
  achieved: boolean;
  achieved_at: string | null;
  notes: string | null;
  extra_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TrainingPlan {
  id: string;
  gym_id: string;
  member_id: string;
  assessment_id: string | null;
  created_by_user_id: string | null;
  name: string;
  objective: string | null;
  sessions_per_week: number;
  split_type: string | null;
  start_date: string;
  end_date: string | null;
  is_active: boolean;
  plan_data: Record<string, unknown>;
  notes: string | null;
  extra_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MemberConstraints {
  id: string;
  gym_id: string;
  member_id: string;
  medical_conditions: string | null;
  injuries: string | null;
  medications: string | null;
  contraindications: string | null;
  preferred_training_times: string | null;
  restrictions: Record<string, unknown>;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface MemberMini {
  id: string;
  full_name: string;
  email?: string | null;
  plan_name: string;
  risk_level: RiskLevel;
  risk_score: number;
  last_checkin_at?: string | null;
  extra_data?: Record<string, unknown>;
}

export interface Profile360 {
  member: MemberMini;
  latest_assessment: AssessmentMini | null;
  constraints: MemberConstraints | null;
  goals: MemberGoal[];
  active_training_plan: TrainingPlan | null;
  insight_summary: string | null;
}

export interface EvolutionData {
  labels: string[];
  weight: Array<number | null>;
  body_fat: Array<number | null>;
  lean_mass: Array<number | null>;
  bmi: Array<number | null>;
  strength: Array<number | null>;
  flexibility: Array<number | null>;
  cardio: Array<number | null>;
  checkins_labels: string[];
  checkins_per_month: number[];
  main_lift_load: Array<number | null>;
  main_lift_label: string | null;
  deltas: Record<string, number | null>;
}

export interface AssessmentDashboard {
  total_members: number;
  assessed_last_90_days: number;
  overdue_assessments: number;
  never_assessed: number;
  upcoming_7_days: number;
  attention_now: AssessmentQueueItem[];
  total_members_items: MemberMini[];
  assessed_members: MemberMini[];
  overdue_members: MemberMini[];
  never_assessed_members: MemberMini[];
  upcoming_members: MemberMini[];
}

export type AssessmentQueueBucket = "overdue" | "never" | "week" | "upcoming" | "covered";
export type AssessmentQueueFilter = "all" | AssessmentQueueBucket;

export interface AssessmentQueueItem {
  id: string;
  full_name: string;
  email: string | null;
  plan_name: string;
  risk_level: RiskLevel;
  risk_score: number;
  last_checkin_at: string | null;
  next_assessment_due: string | null;
  queue_bucket: AssessmentQueueBucket;
  coverage_label: string;
  due_label: string;
  urgency_score: number;
}

export interface AssessmentQueueResponse {
  items: AssessmentQueueItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AssessmentFactor {
  key: string;
  label: string;
  score: number;
  reason: string;
}

export interface AssessmentDiagnosis {
  primary_bottleneck: string;
  primary_bottleneck_label: string;
  secondary_bottleneck: string;
  secondary_bottleneck_label: string;
  explanation: string;
  evolution_factors: string[];
  stagnation_factors: string[];
  frustration_risk: number;
  confidence: string;
  factors: AssessmentFactor[];
}

export interface AssessmentForecast {
  goal_type: string;
  probability_30d: number;
  probability_60d: number;
  probability_90d: number;
  corrected_probability_90d: number;
  likely_days_to_goal: number | null;
  current_summary: string;
  corrected_summary: string;
  consistency_score: number;
  progress_score: number;
  adherence_score: number;
  recovery_score: number;
  overall_score: number;
  blocked: boolean;
  confidence: string;
}

export interface AssessmentBenchmark {
  cohort_label: string;
  sample_size: number;
  percentile: number;
  expected_curve_status: string;
  explanation: string;
  position_label: string;
  peer_average_score: number | null;
}

export interface AssessmentNarratives {
  coach_summary: string;
  member_summary: string;
  retention_summary: string;
}

export interface AssessmentAction {
  key: string;
  title: string;
  owner_role: string;
  priority: string;
  reason: string;
  due_in_days: number;
  suggested_message: string;
}

export interface AssessmentSummary360 {
  member: MemberMini;
  latest_assessment: AssessmentMini | null;
  goal_type: string;
  status: string;
  days_since_last_checkin: number | null;
  recent_weekly_checkins: number;
  target_frequency_per_week: number;
  forecast: AssessmentForecast;
  diagnosis: AssessmentDiagnosis;
  benchmark: AssessmentBenchmark;
  narratives: AssessmentNarratives;
  next_best_action: AssessmentAction;
  actions: AssessmentAction[];
  assistant?: AIAssistantPayload | null;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function asString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function asNullableString(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function asNullableNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function asStringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === "string") : [];
}

function normalizeAssistant(payload: unknown): AIAssistantPayload | null {
  if (!payload || typeof payload !== "object") return null;
  const data = asRecord(payload);
  return {
    summary: asString(data.summary, ""),
    why_it_matters: asString(data.why_it_matters, ""),
    next_best_action: asString(data.next_best_action, ""),
    suggested_message: asNullableString(data.suggested_message),
    evidence: asStringArray(data.evidence),
    confidence_label: asString(data.confidence_label, "Inicial"),
    recommended_channel: asString(data.recommended_channel, "Contexto"),
    cta_target: asString(data.cta_target, "/"),
    cta_label: asString(data.cta_label, "Abrir contexto"),
  };
}

function normalizeMemberMini(payload: unknown): MemberMini {
  const data = asRecord(payload);
  return {
    id: asString(data.id),
    full_name: asString(data.full_name, "Aluno sem identificacao"),
    email: asNullableString(data.email),
    plan_name: asString(data.plan_name, "Plano nao informado"),
    risk_level: (asString(data.risk_level, "green") as RiskLevel),
    risk_score: asNumber(data.risk_score),
    last_checkin_at: asNullableString(data.last_checkin_at),
    extra_data: asRecord(data.extra_data),
  };
}

function normalizeAssessmentQueueItem(payload: unknown): AssessmentQueueItem {
  const data = asRecord(payload);
  return {
    id: asString(data.id),
    full_name: asString(data.full_name, "Aluno sem identificacao"),
    email: asNullableString(data.email),
    plan_name: asString(data.plan_name, "Plano nao informado"),
    risk_level: asString(data.risk_level, "green") as RiskLevel,
    risk_score: asNumber(data.risk_score),
    last_checkin_at: asNullableString(data.last_checkin_at),
    next_assessment_due: asNullableString(data.next_assessment_due),
    queue_bucket: asString(data.queue_bucket, "covered") as AssessmentQueueBucket,
    coverage_label: asString(data.coverage_label, "Sem cobertura operacional"),
    due_label: asString(data.due_label, "Sem janela definida"),
    urgency_score: asNumber(data.urgency_score),
  };
}

function normalizeAssessmentQueueResponse(payload: unknown): AssessmentQueueResponse {
  const data = asRecord(payload);
  return {
    items: Array.isArray(data.items) ? data.items.map(normalizeAssessmentQueueItem) : [],
    total: asNumber(data.total),
    page: asNumber(data.page, 1),
    page_size: asNumber(data.page_size, 50),
  };
}

function normalizeAssessmentDashboard(payload: unknown): AssessmentDashboard {
  const data = asRecord(payload);
  return {
    total_members: asNumber(data.total_members),
    assessed_last_90_days: asNumber(data.assessed_last_90_days),
    overdue_assessments: asNumber(data.overdue_assessments),
    never_assessed: asNumber(data.never_assessed),
    upcoming_7_days: asNumber(data.upcoming_7_days),
    attention_now: Array.isArray(data.attention_now) ? data.attention_now.map(normalizeAssessmentQueueItem) : [],
    total_members_items: Array.isArray(data.total_members_items) ? data.total_members_items.map(normalizeMemberMini) : [],
    assessed_members: Array.isArray(data.assessed_members) ? data.assessed_members.map(normalizeMemberMini) : [],
    overdue_members: Array.isArray(data.overdue_members) ? data.overdue_members.map(normalizeMemberMini) : [],
    never_assessed_members: Array.isArray(data.never_assessed_members) ? data.never_assessed_members.map(normalizeMemberMini) : [],
    upcoming_members: Array.isArray(data.upcoming_members) ? data.upcoming_members.map(normalizeMemberMini) : [],
  };
}

function normalizeAssessmentMini(payload: unknown): AssessmentMini | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = asRecord(payload);
  return {
    id: asString(data.id),
    assessment_number: asNumber(data.assessment_number),
    assessment_date: asString(data.assessment_date),
    next_assessment_due: asNullableString(data.next_assessment_due),
    weight_kg: asNullableNumber(data.weight_kg),
    bmi: asNullableNumber(data.bmi),
    body_fat_pct: asNullableNumber(data.body_fat_pct),
    strength_score: asNullableNumber(data.strength_score),
    flexibility_score: asNullableNumber(data.flexibility_score),
    cardio_score: asNullableNumber(data.cardio_score),
    ai_analysis: asNullableString(data.ai_analysis),
  };
}

function normalizeConstraints(payload: unknown): MemberConstraints | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = asRecord(payload);
  return {
    id: asString(data.id),
    gym_id: asString(data.gym_id),
    member_id: asString(data.member_id),
    medical_conditions: asNullableString(data.medical_conditions),
    injuries: asNullableString(data.injuries),
    medications: asNullableString(data.medications),
    contraindications: asNullableString(data.contraindications),
    preferred_training_times: asNullableString(data.preferred_training_times),
    restrictions: asRecord(data.restrictions),
    notes: asNullableString(data.notes),
    created_at: asString(data.created_at),
    updated_at: asString(data.updated_at),
  };
}

function normalizeGoal(payload: unknown): MemberGoal {
  const data = asRecord(payload);
  return {
    id: asString(data.id),
    gym_id: asString(data.gym_id),
    member_id: asString(data.member_id),
    assessment_id: asNullableString(data.assessment_id),
    title: asString(data.title, "Objetivo"),
    description: asNullableString(data.description),
    category: asString(data.category, "general"),
    target_value: asNullableNumber(data.target_value),
    current_value: asNumber(data.current_value),
    unit: asNullableString(data.unit),
    target_date: asNullableString(data.target_date),
    status: asString(data.status, "active"),
    progress_pct: asNumber(data.progress_pct),
    achieved: Boolean(data.achieved),
    achieved_at: asNullableString(data.achieved_at),
    notes: asNullableString(data.notes),
    extra_data: asRecord(data.extra_data),
    created_at: asString(data.created_at),
    updated_at: asString(data.updated_at),
  };
}

function normalizeTrainingPlan(payload: unknown): TrainingPlan | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  const data = asRecord(payload);
  return {
    id: asString(data.id),
    gym_id: asString(data.gym_id),
    member_id: asString(data.member_id),
    assessment_id: asNullableString(data.assessment_id),
    created_by_user_id: asNullableString(data.created_by_user_id),
    name: asString(data.name, "Plano"),
    objective: asNullableString(data.objective),
    sessions_per_week: asNumber(data.sessions_per_week, 3),
    split_type: asNullableString(data.split_type),
    start_date: asString(data.start_date),
    end_date: asNullableString(data.end_date),
    is_active: data.is_active !== false,
    plan_data: asRecord(data.plan_data),
    notes: asNullableString(data.notes),
    extra_data: asRecord(data.extra_data),
    created_at: asString(data.created_at),
    updated_at: asString(data.updated_at),
  };
}

function normalizeProfile360(payload: unknown): Profile360 {
  const data = asRecord(payload);
  return {
    member: normalizeMemberMini(data.member),
    latest_assessment: normalizeAssessmentMini(data.latest_assessment),
    constraints: normalizeConstraints(data.constraints),
    goals: Array.isArray(data.goals) ? data.goals.map(normalizeGoal) : [],
    active_training_plan: normalizeTrainingPlan(data.active_training_plan),
    insight_summary: asNullableString(data.insight_summary),
  };
}

function normalizeAssessmentFactor(payload: unknown): AssessmentFactor {
  const data = asRecord(payload);
  return {
    key: asString(data.key),
    label: asString(data.label, "Fator"),
    score: asNumber(data.score),
    reason: asString(data.reason),
  };
}

function normalizeDiagnosis(payload: unknown): AssessmentDiagnosis {
  const data = asRecord(payload);
  return {
    primary_bottleneck: asString(data.primary_bottleneck, "unknown"),
    primary_bottleneck_label: asString(data.primary_bottleneck_label, "Sem leitura suficiente"),
    secondary_bottleneck: asString(data.secondary_bottleneck, "unknown"),
    secondary_bottleneck_label: asString(data.secondary_bottleneck_label, "Sem leitura complementar"),
    explanation: asString(data.explanation, "Nao ha dados suficientes para diagnostico causal completo."),
    evolution_factors: asStringArray(data.evolution_factors),
    stagnation_factors: asStringArray(data.stagnation_factors),
    frustration_risk: asNumber(data.frustration_risk),
    confidence: asString(data.confidence, "low"),
    factors: Array.isArray(data.factors) ? data.factors.map(normalizeAssessmentFactor) : [],
  };
}

function normalizeForecast(payload: unknown): AssessmentForecast {
  const data = asRecord(payload);
  return {
    goal_type: asString(data.goal_type, "general"),
    probability_30d: asNumber(data.probability_30d),
    probability_60d: asNumber(data.probability_60d),
    probability_90d: asNumber(data.probability_90d),
    corrected_probability_90d: asNumber(data.corrected_probability_90d),
    likely_days_to_goal: asNullableNumber(data.likely_days_to_goal),
    current_summary: asString(data.current_summary, "Sem previsao consolidada."),
    corrected_summary: asString(data.corrected_summary, "Ainda nao ha acao corretiva sugerida."),
    consistency_score: asNumber(data.consistency_score),
    progress_score: asNumber(data.progress_score),
    adherence_score: asNumber(data.adherence_score),
    recovery_score: asNumber(data.recovery_score),
    overall_score: asNumber(data.overall_score),
    blocked: Boolean(data.blocked),
    confidence: asString(data.confidence, "low"),
  };
}

function normalizeBenchmark(payload: unknown): AssessmentBenchmark {
  const data = asRecord(payload);
  return {
    cohort_label: asString(data.cohort_label, "Cohort indisponivel"),
    sample_size: asNumber(data.sample_size),
    percentile: asNumber(data.percentile),
    expected_curve_status: asString(data.expected_curve_status, "unknown"),
    explanation: asString(data.explanation, "Sem benchmark suficiente para comparar."),
    position_label: asString(data.position_label, "Sem benchmark"),
    peer_average_score: asNullableNumber(data.peer_average_score),
  };
}

function normalizeNarratives(payload: unknown): AssessmentNarratives {
  const data = asRecord(payload);
  return {
    coach_summary: asString(data.coach_summary, "Sem narrativa disponivel para a equipe."),
    member_summary: asString(data.member_summary, "Sem narrativa disponivel para o aluno."),
    retention_summary: asString(data.retention_summary, "Sem narrativa disponivel para retencao."),
  };
}

function normalizeAction(payload: unknown): AssessmentAction {
  const data = asRecord(payload);
  return {
    key: asString(data.key, "no_action"),
    title: asString(data.title, "Nenhuma acao recomendada"),
    owner_role: asString(data.owner_role, "manager"),
    priority: asString(data.priority, "medium"),
    reason: asString(data.reason, "Sem dados suficientes para priorizar uma acao."),
    due_in_days: asNumber(data.due_in_days),
    suggested_message: asString(data.suggested_message, "Reavalie o aluno quando houver mais contexto."),
  };
}

export function normalizeAssessmentSummary360(payload: unknown): AssessmentSummary360 {
  const data = asRecord(payload);
  const actions = Array.isArray(data.actions) ? data.actions.map(normalizeAction) : [];
  const nextBestAction = normalizeAction(data.next_best_action);

  return {
    member: normalizeMemberMini(data.member),
    latest_assessment: normalizeAssessmentMini(data.latest_assessment),
    goal_type: asString(data.goal_type, "general"),
    status: asString(data.status, "attention"),
    days_since_last_checkin: asNullableNumber(data.days_since_last_checkin),
    recent_weekly_checkins: asNumber(data.recent_weekly_checkins),
    target_frequency_per_week: asNumber(data.target_frequency_per_week, 3),
    forecast: normalizeForecast(data.forecast),
    diagnosis: normalizeDiagnosis(data.diagnosis),
    benchmark: normalizeBenchmark(data.benchmark),
    narratives: normalizeNarratives(data.narratives),
    next_best_action: nextBestAction.title === "Nenhuma acao recomendada" && actions.length > 0 ? actions[0] : nextBestAction,
    actions,
    assistant: normalizeAssistant(data.assistant),
  };
}

export interface AssessmentCreateInput {
  assessment_date?: string;
  height_cm?: number;
  weight_kg?: number;
  body_fat_pct?: number;
  lean_mass_kg?: number;
  waist_cm?: number;
  hip_cm?: number;
  chest_cm?: number;
  arm_cm?: number;
  thigh_cm?: number;
  resting_hr?: number;
  blood_pressure_systolic?: number;
  blood_pressure_diastolic?: number;
  vo2_estimated?: number;
  strength_score?: number;
  flexibility_score?: number;
  cardio_score?: number;
  observations?: string;
  extra_data?: Record<string, unknown>;
}

export interface MemberConstraintsUpsertInput {
  medical_conditions?: string;
  injuries?: string;
  medications?: string;
  contraindications?: string;
  preferred_training_times?: string;
  restrictions?: Record<string, unknown>;
  notes?: string;
}

export interface MemberGoalCreateInput {
  assessment_id?: string;
  title: string;
  description?: string;
  category?: string;
  target_value?: number;
  current_value?: number;
  unit?: string;
  target_date?: string;
  status?: string;
  progress_pct?: number;
  achieved?: boolean;
  notes?: string;
  extra_data?: Record<string, unknown>;
}

export interface TrainingPlanCreateInput {
  assessment_id?: string;
  name: string;
  objective?: string;
  sessions_per_week?: number;
  split_type?: string;
  start_date?: string;
  end_date?: string;
  is_active?: boolean;
  plan_data?: Record<string, unknown>;
  notes?: string;
  extra_data?: Record<string, unknown>;
}

export interface AssessmentQueueParams {
  page?: number;
  page_size?: number;
  search?: string;
  bucket?: AssessmentQueueFilter;
}

export interface ActuarSyncQueueParams {
  sync_status?: string;
  error_code?: string;
  search?: string;
}

export const assessmentService = {
  async dashboard(): Promise<AssessmentDashboard> {
    const { data } = await api.get<AssessmentDashboard>("/api/v1/assessments/dashboard");
    return normalizeAssessmentDashboard(data);
  },

  async queue(params: AssessmentQueueParams = {}): Promise<AssessmentQueueResponse> {
    const { data } = await api.get<AssessmentQueueResponse>("/api/v1/assessments/queue", {
      params: {
        page: params.page ?? 1,
        page_size: params.page_size ?? 50,
        search: params.search?.trim() ? params.search.trim() : undefined,
        bucket: params.bucket ?? "all",
      },
    });
    return normalizeAssessmentQueueResponse(data);
  },

  async actuarSyncQueue(params: ActuarSyncQueueParams = {}): Promise<ActuarSyncQueueItem[]> {
    const { data } = await api.get<ActuarSyncQueueItem[]>("/api/v1/assessments/actuar-sync-queue", {
      params: {
        sync_status: params.sync_status || undefined,
        error_code: params.error_code || undefined,
        search: params.search?.trim() ? params.search.trim() : undefined,
      },
    });
    return data;
  },

  async profile360(memberId: string): Promise<Profile360> {
    const { data } = await api.get<Profile360>(`/api/v1/assessments/members/${memberId}/profile`);
    return normalizeProfile360(data);
  },

  async summary360(memberId: string): Promise<AssessmentSummary360> {
    const { data } = await api.get<AssessmentSummary360>(`/api/v1/assessments/members/${memberId}/summary-360`);
    return normalizeAssessmentSummary360(data);
  },

  async diagnosis(memberId: string): Promise<AssessmentDiagnosis> {
    const { data } = await api.get<AssessmentDiagnosis>(`/api/v1/assessments/members/${memberId}/diagnosis`);
    return data;
  },

  async forecast(memberId: string): Promise<AssessmentForecast> {
    const { data } = await api.get<AssessmentForecast>(`/api/v1/assessments/members/${memberId}/forecast`);
    return data;
  },

  async benchmark(memberId: string): Promise<AssessmentBenchmark> {
    const { data } = await api.get<AssessmentBenchmark>(`/api/v1/assessments/members/${memberId}/benchmark`);
    return data;
  },

  async actions(memberId: string): Promise<AssessmentAction[]> {
    const { data } = await api.get<AssessmentAction[]>(`/api/v1/assessments/members/${memberId}/actions`);
    return data;
  },

  async list(memberId: string): Promise<Assessment[]> {
    const { data } = await api.get<Assessment[]>(`/api/v1/assessments/members/${memberId}`);
    return data;
  },

  async create(memberId: string, payload: AssessmentCreateInput): Promise<Assessment> {
    const { data } = await api.post<Assessment>(`/api/v1/assessments/members/${memberId}`, payload);
    return data;
  },

  async evolution(memberId: string): Promise<EvolutionData> {
    const { data } = await api.get<EvolutionData>(`/api/v1/assessments/members/${memberId}/evolution`);
    return data;
  },

  async upsertConstraints(memberId: string, payload: MemberConstraintsUpsertInput): Promise<MemberConstraints> {
    const { data } = await api.put<MemberConstraints>(`/api/v1/assessments/members/${memberId}/constraints`, payload);
    return data;
  },

  async createGoal(memberId: string, payload: MemberGoalCreateInput): Promise<MemberGoal> {
    const { data } = await api.post<MemberGoal>(`/api/v1/assessments/members/${memberId}/goals`, payload);
    return data;
  },

  async updateGoal(memberId: string, goalId: string, payload: MemberGoalCreateInput): Promise<MemberGoal> {
    const { data } = await api.put<MemberGoal>(`/api/v1/assessments/members/${memberId}/goals/${goalId}`, payload);
    return data;
  },

  async listGoals(memberId: string): Promise<MemberGoal[]> {
    const { data } = await api.get<MemberGoal[]>(`/api/v1/assessments/members/${memberId}/goals`);
    return data;
  },

  async createTrainingPlan(memberId: string, payload: TrainingPlanCreateInput): Promise<TrainingPlan> {
    const { data } = await api.post<TrainingPlan>(`/api/v1/assessments/members/${memberId}/training-plans`, payload);
    return data;
  },

  async updateTrainingPlan(memberId: string, planId: string, payload: TrainingPlanCreateInput): Promise<TrainingPlan> {
    const { data } = await api.put<TrainingPlan>(`/api/v1/assessments/members/${memberId}/training-plans/${planId}`, payload);
    return data;
  },
};
