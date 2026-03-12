import { api } from "./api";
import type { RiskLevel } from "../types";

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
  total_members_items: MemberMini[];
  assessed_members: MemberMini[];
  overdue_members: MemberMini[];
  never_assessed_members: MemberMini[];
  upcoming_members: MemberMini[];
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

export const assessmentService = {
  async dashboard(): Promise<AssessmentDashboard> {
    const { data } = await api.get<AssessmentDashboard>("/api/v1/assessments/dashboard");
    return data;
  },

  async profile360(memberId: string): Promise<Profile360> {
    const { data } = await api.get<Profile360>(`/api/v1/assessments/members/${memberId}/profile`);
    return data;
  },

  async summary360(memberId: string): Promise<AssessmentSummary360> {
    const { data } = await api.get<AssessmentSummary360>(`/api/v1/assessments/members/${memberId}/summary-360`);
    return data;
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

  async listGoals(memberId: string): Promise<MemberGoal[]> {
    const { data } = await api.get<MemberGoal[]>(`/api/v1/assessments/members/${memberId}/goals`);
    return data;
  },

  async createTrainingPlan(memberId: string, payload: TrainingPlanCreateInput): Promise<TrainingPlan> {
    const { data } = await api.post<TrainingPlan>(`/api/v1/assessments/members/${memberId}/training-plans`, payload);
    return data;
  },
};
