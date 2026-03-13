import { api } from "./api";
import type { RiskLevel } from "../types";

export interface MemberTimelineEvent {
  type: string;
  timestamp: string;
  title: string;
  detail: string;
  icon: string;
  level?: string;
}

export interface TimelineMemberSummary {
  id: string;
  full_name: string;
  plan_name: string;
  risk_level: RiskLevel;
  risk_score: number;
  last_checkin_at?: string | null;
  email?: string | null;
  monthly_fee?: number | null;
}

export const memberTimelineService = {
  async list(memberId: string, limit = 50): Promise<MemberTimelineEvent[]> {
    const { data } = await api.get<MemberTimelineEvent[]>(`/api/v1/members/${memberId}/timeline`, {
      params: { limit },
    });
    return data;
  },
};
