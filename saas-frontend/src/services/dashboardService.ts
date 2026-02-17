import { api } from "./api";
import type {
  ChurnPoint,
  ConversionBySource,
  ExecutiveDashboard,
  GrowthPoint,
  HeatmapPoint,
  LTVPoint,
  Lead,
  Member,
  NPSEvolutionPoint,
  ProjectionPoint,
  RevenuePoint,
} from "../types";

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
  }> {
    const { data } = await api.get("/api/v1/dashboards/retention");
    return data;
  },
};
