import { api } from "./api";
import type {
  AIAssistantPayload,
  BIFoundationDashboard,
  ChurnPoint,
  ConversionBySource,
  ExecutiveDashboard,
  FinancialDashboard,
  GrowthPoint,
  HeatmapPoint,
  LTVPoint,
  Lead,
  Member,
  NPSEvolutionPoint,
  PaginatedResponse,
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
  retention_stage: string | null;
  retention_stage_label: string | null;
  retention_stage_priority: number;
  recommended_owner_role: string | null;
  operational_lane: string | null;
  cooldown_until: string | null;
  signals_summary: string;
  next_action: string | null;
  reasons: Record<string, unknown>;
  action_history: Array<Record<string, unknown>>;
  playbook_steps: RetentionPlaybookStep[];
  assistant?: AIAssistantPayload | null;
}

export type RetentionQueueResponse = PaginatedResponse<RetentionQueueItem> & {
  data_freshness?: {
    last_import_at: string | null;
    latest_checkin_at: string | null;
    coverage_verified: boolean;
    warning_codes: string[];
  } | null;
  stage_counts?: Record<string, number>;
};

export interface RetentionExclusion {
  id: string;
  scope: "member" | "plan";
  member_id: string | null;
  member_name: string | null;
  plan_name: string | null;
  reason: string | null;
  created_by_name: string;
  created_at: string;
}

export interface RetentionQueueFilters {
  search?: string;
  level?: "all" | "red" | "yellow";
  member_status?: "all" | "active" | "inactive";
  churn_type?: string;
  plan_cycle?: "monthly" | "semiannual" | "annual";
  preferred_shift?: "overnight" | "morning" | "afternoon" | "evening";
  retention_stage?: "monitoring" | "attention" | "recovery" | "reactivation" | "manager_escalation" | "cold_base";
}

export interface RetentionQueueBulkResolveResult {
  matched_count: number;
  resolved_count: number;
  skipped_count: number;
}

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

  async financial(): Promise<FinancialDashboard> {
    const { data } = await api.get<FinancialDashboard>("/api/v1/dashboards/financial");
    return data;
  },

  async biFoundation(): Promise<BIFoundationDashboard> {
    const { data } = await api.get<BIFoundationDashboard>("/api/v1/dashboards/bi-foundation");
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

  async retentionQueue(params?: RetentionQueueFilters & {
    page?: number;
    page_size?: number;
  }): Promise<RetentionQueueResponse> {
    const { data } = await api.get<RetentionQueueResponse>("/api/v1/dashboards/retention/queue", {
      params,
    });
    return data;
  },

  async resolveRetentionQueue(
    payload: RetentionQueueFilters & { expected_count: number; resolution_note?: string },
  ): Promise<RetentionQueueBulkResolveResult> {
    const { data } = await api.post<RetentionQueueBulkResolveResult>(
      "/api/v1/dashboards/retention/queue/resolve",
      payload,
    );
    return data;
  },

  async createRetentionExclusion(payload: {
    scope: "member" | "plan";
    member_id?: string;
    plan_name?: string;
    reason?: string;
  }): Promise<RetentionExclusion> {
    const { data } = await api.post<RetentionExclusion>("/api/v1/dashboards/retention/exclusions", payload);
    return data;
  },

  async retentionExclusions(search?: string): Promise<{ items: RetentionExclusion[]; total: number }> {
    const { data } = await api.get<{ items: RetentionExclusion[]; total: number }>(
      "/api/v1/dashboards/retention/exclusions",
      { params: { search: search || undefined } },
    );
    return data;
  },

  async revokeRetentionExclusion(exclusionId: string): Promise<void> {
    await api.delete(`/api/v1/dashboards/retention/exclusions/${exclusionId}`);
  },

  async exportRetentionSpreadsheet(params?: RetentionQueueFilters): Promise<void> {
    const response = await api.get("/api/v1/dashboards/retention/export.xlsx", { params, responseType: "blob" });
    const disposition = String(response.headers["content-disposition"] ?? "");
    const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] ?? `retencao-${new Date().toISOString().slice(0, 10)}.xlsx`;
    const url = window.URL.createObjectURL(
      new Blob([response.data], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" }),
    );
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    window.URL.revokeObjectURL(url);
  },

  async weeklySummary(): Promise<WeeklySummary> {
    const { data } = await api.get<WeeklySummary>("/api/v1/dashboards/weekly-summary");
    return data;
  },

  async contactLog(memberId: string, outcome: "answered" | "no_answer" | "voicemail" | "invalid_number", note?: string): Promise<void> {
    await api.post(`/api/v1/members/${memberId}/contact-log`, { outcome, note });
  },
};
