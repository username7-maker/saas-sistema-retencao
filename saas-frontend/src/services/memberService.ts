import { api } from "./api";
import { assessmentService, type AssessmentSummary360, type Profile360 } from "./assessmentService";
import type { AIAssistantPayload, Member, PaginatedResponse, RiskLevel } from "../types";

export type MemberPlanCycle = "monthly" | "semiannual" | "annual";

export interface MemberFilters {
  page?: number;
  page_size?: number;
  search?: string;
  risk_level?: RiskLevel;
  status?: Member["status"];
  plan_cycle?: MemberPlanCycle;
  min_days_without_checkin?: number;
  provisional_only?: boolean;
}

export type MemberBulkUpdateTargetMode = "selected" | "filtered";

export interface MemberBulkUpdateFilters extends Omit<MemberFilters, "page" | "page_size"> {}

export interface MemberBulkUpdateChanges {
  status?: Member["status"];
  plan_name?: string;
  monthly_fee?: number;
  preferred_shift?: string;
}

export interface MemberBulkUpdatePayload {
  target_mode: MemberBulkUpdateTargetMode;
  selected_member_ids: string[];
  filters: MemberBulkUpdateFilters;
  changes: MemberBulkUpdateChanges;
}

export interface MemberBulkUpdatePreviewMember {
  id: string;
  full_name: string;
  email: string | null;
  current_values: Record<string, unknown>;
  next_values: Record<string, unknown>;
}

export interface MemberBulkUpdatePreviewResult {
  target_mode: MemberBulkUpdateTargetMode;
  target_description: string;
  total_candidates: number;
  would_update: number;
  unchanged: number;
  changed_fields: string[];
  sample_members: MemberBulkUpdatePreviewMember[];
}

export interface MemberBulkUpdateResult {
  target_mode: MemberBulkUpdateTargetMode;
  target_description: string;
  updated: number;
  unchanged: number;
  changed_fields: string[];
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
  assistant?: AIAssistantPayload | null;
}

export const memberService = {
  async listMembers(filters: MemberFilters = {}): Promise<PaginatedResponse<Member>> {
    const { data } = await api.get<PaginatedResponse<Member>>("/api/v1/members/", {
      params: { page_size: 20, ...filters },
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

  async previewBulkUpdate(payload: MemberBulkUpdatePayload): Promise<MemberBulkUpdatePreviewResult> {
    const { data } = await api.post<MemberBulkUpdatePreviewResult>("/api/v1/members/bulk-update/preview", payload);
    return data;
  },

  async bulkUpdate(payload: MemberBulkUpdatePayload): Promise<MemberBulkUpdateResult> {
    const { data } = await api.post<MemberBulkUpdateResult>("/api/v1/members/bulk-update", payload);
    return data;
  },

  async getOnboardingScore(memberId: string): Promise<OnboardingScoreResult> {
    const { data } = await api.get<OnboardingScoreResult>(`/api/v1/members/${memberId}/onboarding-score`);
    return data;
  },

  async getProfile360(memberId: string): Promise<Profile360> {
    return assessmentService.profile360(memberId);
  },

  async getAssessmentSummary(memberId: string): Promise<AssessmentSummary360> {
    return assessmentService.summary360(memberId);
  },
};
