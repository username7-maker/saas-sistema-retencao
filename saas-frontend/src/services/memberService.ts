import { api } from "./api";
import { assessmentService, type AssessmentSummary360, type Profile360 } from "./assessmentService";
import type { AIAssistantPayload, LeadToMemberIntelligenceContext, Member, PaginatedResponse, RiskLevel } from "../types";

export type MemberPlanCycle = "monthly" | "semiannual" | "annual";

export interface MemberFilters {
  page?: number;
  page_size?: number;
  search?: string;
  risk_level?: RiskLevel;
  status?: Member["status"];
  plan_cycle?: MemberPlanCycle;
  preferred_shift?: "overnight" | "morning" | "afternoon" | "evening";
  min_days_without_checkin?: number;
  provisional_only?: boolean;
}

export interface MemberCreatePayload {
  full_name: string;
  email?: string;
  phone?: string;
  birthdate?: string;
  plan_name: string;
  monthly_fee?: number;
  join_date: string;
  preferred_shift?: string;
}

export interface MemberUpdatePayload {
  full_name?: string;
  email?: string;
  phone?: string;
  birthdate?: string | null;
  plan_name?: string;
  monthly_fee?: number;
  status?: Member["status"];
  preferred_shift?: string;
  extra_data?: Record<string, unknown>;
}

export interface OnboardingScoreResult {
  score: number;
  status: 'active' | 'completed' | 'at_risk';
  factors: {
    checkin_frequency: number;
    first_assessment: number;
    task_completion: number;
    consistency: number;
    member_response: number;
  };
  days_since_join: number;
  checkin_count: number;
  completed_tasks: number;
  total_tasks: number;
  total_journey_tasks?: number | null;
  assistant?: AIAssistantPayload | null;
}

export interface OnboardingScoreSnapshot {
  member_id: string;
  score: number;
  status: 'active' | 'completed' | 'at_risk';
}

export interface PreferredShiftSyncResult {
  updated_count: number;
  message: string;
}

export interface OnboardingCockpitMember {
  member_id: string;
  full_name: string;
  plan_name?: string | null;
  preferred_shift?: string | null;
  days_since_join: number;
  score: number;
  status: string;
  phase_label: string;
  next_action: string;
  responsible_role: string;
  current_stage_offset?: number | null;
}

export interface OnboardingCockpitTaskStage {
  stage_key: string;
  label: string;
  day_offset?: number | null;
  total: number;
  due_now_total: number;
  future_total: number;
}

export interface OnboardingCockpit {
  summary: {
    active_total: number;
    at_risk_total: number;
    critical_total: number;
    due_today_total: number;
    overdue_total: number;
    unassigned_total: number;
  };
  members: OnboardingCockpitMember[];
  critical_members: OnboardingCockpitMember[];
  tasks_by_stage: OnboardingCockpitTaskStage[];
  score_distribution: Record<string, number>;
  metrics: {
    first_week_two_checkins_rate?: number | null;
    first_assessment_rate?: number | null;
    d30_ready_total: number;
    generated_at: string;
  };
  generated_at: string;
}

export interface MemberOperationalNote {
  id: string;
  gym_id: string;
  member_id: string;
  author_user_id: string | null;
  note_type: string;
  body: string;
  visibility: string;
  extra_data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface MemberOperationalProfile {
  generated_at: string;
  member: Record<string, unknown>;
  permissions: Record<string, unknown>;
  summary: Record<string, unknown>;
  lifecycle: Record<string, unknown>;
  risk: Record<string, unknown>;
  activity: Record<string, unknown>;
  assessment: Record<string, unknown>;
  financial: Record<string, unknown> | null;
  commercial: Record<string, unknown> | null;
  communication: Record<string, unknown>;
  tasks: {
    open_total?: number;
    by_domain?: Record<string, number>;
    top_open?: Record<string, unknown>[];
  };
  autopilot: {
    state?: string;
    actions_open_total?: number;
    latest_action?: Record<string, unknown> | null;
  };
  next_best_action: {
    key?: string;
    domain?: string;
    title?: string;
    reason?: string;
    priority?: string;
    owner_role?: string;
    can_autopilot?: boolean;
    autopilot_mode?: string;
    blocked_reasons?: string[];
    evidence?: string[];
    context_path?: string;
  };
  signals: Record<string, unknown>[];
  timeline_preview: Record<string, unknown>[];
  data_quality_flags: Record<string, unknown>[];
  notes: MemberOperationalNote[];
}

export interface MemberNoteCreatePayload {
  note_type?: "internal" | "retention" | "coach" | "manager" | "sales_handoff" | "health_context";
  body: string;
  visibility?: "internal" | "team" | "manager" | "coach" | "sales";
  extra_data?: Record<string, unknown>;
}

const MEMBER_STATUSES = new Set<Member["status"]>(["active", "paused", "cancelled"]);
const RISK_LEVELS = new Set<RiskLevel>(["green", "yellow", "red"]);

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function asRecord(value: unknown): Record<string, unknown> {
  return isRecord(value) ? value : {};
}

function asString(value: unknown, fallback = ""): string {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function asNullableString(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return null;
}

function asNumber(value: unknown, fallback = 0): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const normalized = value.trim().replace(",", ".");
    const parsed = Number(normalized);
    if (Number.isFinite(parsed)) return parsed;
  }
  return fallback;
}

function asInteger(value: unknown, fallback = 0): number {
  return Math.trunc(asNumber(value, fallback));
}

function asStatus(value: unknown): Member["status"] {
  return typeof value === "string" && MEMBER_STATUSES.has(value as Member["status"])
    ? (value as Member["status"])
    : "active";
}

function asRiskLevel(value: unknown): RiskLevel {
  return typeof value === "string" && RISK_LEVELS.has(value as RiskLevel) ? (value as RiskLevel) : "green";
}

function normalizeMember(value: unknown, index: number): Member {
  const source = asRecord(value);
  const createdAt = asString(source.created_at, "");
  const updatedAt = asString(source.updated_at, createdAt);

  return {
    id: asString(source.id, `member-${index + 1}`),
    full_name: asString(source.full_name, "Sem nome"),
    email: asNullableString(source.email),
    phone: asNullableString(source.phone),
    birthdate: asNullableString(source.birthdate),
    status: asStatus(source.status),
    plan_name: asString(source.plan_name, "Plano nao informado"),
    monthly_fee: asNumber(source.monthly_fee, 0),
    join_date: asString(source.join_date, ""),
    preferred_shift: asNullableString(source.preferred_shift),
    nps_last_score: asInteger(source.nps_last_score, 0),
    loyalty_months: asInteger(source.loyalty_months, 0),
    risk_score: asInteger(source.risk_score, 0),
    risk_level: asRiskLevel(source.risk_level),
    last_checkin_at: asNullableString(source.last_checkin_at),
    extra_data: asRecord(source.extra_data),
    suggested_action: asNullableString(source.suggested_action),
    onboarding_status: asNullableString(source.onboarding_status) as Member["onboarding_status"],
    onboarding_score: asInteger(source.onboarding_score, 0),
    lifecycle_stage: asNullableString(source.lifecycle_stage),
    lifecycle_label: asNullableString(source.lifecycle_label),
    operational_lane: asNullableString(source.operational_lane),
    recommended_owner_role: asNullableString(source.recommended_owner_role),
    lifecycle_priority: asInteger(source.lifecycle_priority, 0),
    lifecycle_reason: asNullableString(source.lifecycle_reason),
    lifecycle_next_focus: asNullableString(source.lifecycle_next_focus),
    created_at: createdAt,
    updated_at: updatedAt,
  };
}

function normalizeMembersResponse(data: unknown, filters: MemberFilters): PaginatedResponse<Member> {
  const source = asRecord(data);
  const rawItems = Array.isArray(data) ? data : Array.isArray(source.items) ? source.items : [];
  const items = rawItems.map(normalizeMember);
  const page = asInteger(source.page, filters.page ?? 1);
  const pageSize = asInteger(source.page_size, filters.page_size ?? (items.length || 20));

  return {
    items,
    total: asInteger(source.total, items.length),
    page,
    page_size: pageSize,
  };
}

export const memberService = {
  async listMembers(filters: MemberFilters = {}): Promise<PaginatedResponse<Member>> {
    const { data } = await api.get<unknown>("/api/v1/members/", {
      params: { page_size: 20, ...filters },
    });
    return normalizeMembersResponse(data, filters);
  },

  async listMemberIndex(filters: Omit<MemberFilters, "page" | "page_size"> = {}): Promise<Member[]> {
    const { data } = await api.get<Member[]>("/api/v1/members/index", {
      params: filters,
      timeout: 60_000,
    });
    return data;
  },

  async getMember(memberId: string): Promise<Member> {
    const { data } = await api.get<Member>(`/api/v1/members/${memberId}`);
    return data;
  },

  async createMember(payload: MemberCreatePayload): Promise<Member> {
    const { data } = await api.post<Member>("/api/v1/members/", payload);
    return data;
  },

  async updateMember(memberId: string, payload: MemberUpdatePayload): Promise<Member> {
    const { data } = await api.patch<Member>(`/api/v1/members/${memberId}`, payload);
    return data;
  },

  async deleteMember(memberId: string): Promise<void> {
    await api.delete(`/api/v1/members/${memberId}`);
  },

  async syncPreferredShifts(): Promise<PreferredShiftSyncResult> {
    const { data } = await api.post<PreferredShiftSyncResult>("/api/v1/members/preferred-shifts/sync");
    return data;
  },

  async getOnboardingScore(memberId: string): Promise<OnboardingScoreResult> {
    const { data } = await api.get<OnboardingScoreResult>(`/api/v1/members/${memberId}/onboarding-score`);
    return data;
  },

  async getOnboardingScoreboard(): Promise<OnboardingScoreSnapshot[]> {
    const { data } = await api.get<OnboardingScoreSnapshot[]>("/api/v1/members/onboarding-scoreboard", {
      params: { ts: Date.now() },
    });
    return data;
  },

  async getOnboardingCockpit(): Promise<OnboardingCockpit> {
    const { data } = await api.get<OnboardingCockpit>("/api/v1/onboarding/cockpit", {
      params: { ts: Date.now() },
    });
    return data;
  },

  async getIntelligenceContext(memberId: string): Promise<LeadToMemberIntelligenceContext> {
    const { data } = await api.get<LeadToMemberIntelligenceContext>(`/api/v1/members/${memberId}/intelligence-context`);
    return data;
  },

  async getOperationalProfile(memberId: string): Promise<MemberOperationalProfile> {
    const { data } = await api.get<MemberOperationalProfile>(`/api/v1/members/${memberId}/operational-profile`, {
      params: { ts: Date.now() },
    });
    return data;
  },

  async listNotes(memberId: string): Promise<MemberOperationalNote[]> {
    const { data } = await api.get<MemberOperationalNote[]>(`/api/v1/members/${memberId}/notes`);
    return data;
  },

  async createNote(memberId: string, payload: MemberNoteCreatePayload): Promise<MemberOperationalNote> {
    const { data } = await api.post<MemberOperationalNote>(`/api/v1/members/${memberId}/notes`, payload);
    return data;
  },

  async getProfile360(memberId: string): Promise<Profile360> {
    return assessmentService.profile360(memberId);
  },

  async getAssessmentSummary(memberId: string): Promise<AssessmentSummary360> {
    return assessmentService.summary360(memberId);
  },
};
