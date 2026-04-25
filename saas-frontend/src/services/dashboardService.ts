import { api } from "./api";
import type {
  AIAssistantPayload,
  ChurnPoint,
  ConversionBySource,
  ExecutiveDashboard,
  GrowthPoint,
  HeatmapPoint,
  LTVPoint,
  Lead,
  Member,
  NPSEvolutionPoint,
  PaginatedResponse,
  ProjectionPoint,
  RiskLevel,
  RevenuePoint,
  WeeklySummary,
} from "../types";

export interface RetentionPlaybookStep {
  action: string;
  priority: string;
  title: string;
  message: string;
  due_days: number;
  owner: string;
}

export interface RetentionQueueItem {
  alert_id: string;
  member_id: string;
  full_name: string;
  email: string | null;
  phone: string | null;
  plan_name: string;
  preferred_shift?: string | null;
  risk_level: RiskLevel;
  risk_score: number;
  nps_last_score: number;
  days_without_checkin: number | null;
  last_checkin_at: string | null;
  last_contact_at: string | null;
  churn_type: string | null;
  automation_stage: string | null;
  created_at: string;
  forecast_60d: number | null;
  signals_summary: string;
  next_action: string | null;
  reasons: Record<string, unknown>;
  action_history: Array<Record<string, unknown>>;
  playbook_steps: RetentionPlaybookStep[];
  assistant?: AIAssistantPayload | null;
}

export type RetentionQueueResponse = PaginatedResponse<RetentionQueueItem>;

export const dashboardService = {
  async executive(): Promise<ExecutiveDashboard> {
    const { data } = await api.get<ExecutiveDashboard>("/api/v1/dashboards/executive");
    return data;
  },

  async mrr(): Promise<RevenuePoint[]> {
    const { data } = await api.get<RevenuePoint[]>("/api/v1/dashboards/mrr");
    return data;
  },

  async churn(): Promise<ChurnPoint[]> {
    const { data } = await api.get<ChurnPoint[]>("/api/v1/dashboards/churn");
    return data;
  },

  async ltv(): Promise<LTVPoint[]> {
    const { data } = await api.get<LTVPoint[]>("/api/v1/dashboards/ltv");
    return data;
  },

  async growth(): Promise<GrowthPoint[]> {
    const { data } = await api.get<GrowthPoint[]>("/api/v1/dashboards/growth-mom");
    return data;
  },

  async operational(): Promise<{
    realtime_checkins: number;
    heatmap: HeatmapPoint[];
    inactive_7d_total: number;
    inactive_7d_items: Member[];
    birthday_today_total: number;
    birthday_today_items: Member[];
  }> {
    const { data } = await api.get("/api/v1/dashboards/operational");
    return data;
  },

  async commercial(): Promise<{
    pipeline: Record<string, number>;
    conversion_by_source: ConversionBySource[];
    cac: number;
    stale_leads_total: number;
    stale_leads: Lead[];
  }> {
    const { data } = await api.get("/api/v1/dashboards/commercial");
    return data;
  },

  async financial(): Promise<{
    monthly_revenue: RevenuePoint[];
    delinquency_rate: number;
    projections: ProjectionPoint[];
  }> {
    const { data } = await api.get("/api/v1/dashboards/financial");
    return data;
  },

  async retention(): Promise<{
    red: { total: number; items: Member[] };
    yellow: { total: number; items: Member[] };
    nps_trend: NPSEvolutionPoint[];
    mrr_at_risk: number;
    avg_red_score: number;
    avg_yellow_score: number;
    churn_distribution: Record<string, number>;
    last_contact_map: Record<string, string>;
  }> {
    const { data } = await api.get("/api/v1/dashboards/retention");
    return data;
  },

  async retentionQueue(params?: {
    page?: number;
    page_size?: number;
    search?: string;
    level?: "all" | "red" | "yellow";
    churn_type?: string;
    plan_cycle?: "monthly" | "semiannual" | "annual";
    preferred_shift?: "morning" | "afternoon" | "evening";
  }): Promise<RetentionQueueResponse> {
    const { data } = await api.get<RetentionQueueResponse>("/api/v1/dashboards/retention/queue", {
      params,
    });
    return data;
  },

  async weeklySummary(): Promise<WeeklySummary> {
    const { data } = await api.get<WeeklySummary>("/api/v1/dashboards/weekly-summary");
    return data;
  },

  async contactLog(memberId: string, outcome: "answered" | "no_answer" | "voicemail" | "invalid_number", note?: string): Promise<void> {
    await api.post(`/api/v1/members/${memberId}/contact-log`, { outcome, note });
  },
};
