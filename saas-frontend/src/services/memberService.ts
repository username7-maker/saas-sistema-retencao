import { api } from "./api";
import type { Member, PaginatedResponse, RiskLevel } from "../types";

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

export interface MemberCreatePayload {
  full_name: string;
  email?: string;
  phone?: string;
  plan_name: string;
  monthly_fee?: number;
  join_date: string;
  preferred_shift?: string;
}

export interface MemberUpdatePayload {
  full_name?: string;
  email?: string;
  phone?: string;
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
    nps_response: number;
  };
  days_since_join: number;
  checkin_count: number;
  completed_tasks: number;
  total_tasks: number;
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

  async getOnboardingScore(memberId: string): Promise<OnboardingScoreResult> {
    const { data } = await api.get<OnboardingScoreResult>(`/api/v1/members/${memberId}/onboarding-score`);
    return data;
  },

  async getProfile360(memberId: string): Promise<Record<string, unknown>> {
    const { data } = await api.get<Record<string, unknown>>(`/api/v1/assessments/members/${memberId}/profile`);
    return data;
  },
};
