import { api } from "./api";
import type { PaginatedResponse, RiskAlert } from "../types";

export const riskAlertService = {
  async listUnresolved(level?: "green" | "yellow" | "red"): Promise<PaginatedResponse<RiskAlert>> {
    const { data } = await api.get<PaginatedResponse<RiskAlert>>("/api/v1/risk-alerts", {
      params: {
        page_size: 20,
        resolved: false,
        level,
      },
    });
    return data;
  },

  async resolve(alertId: string, resolution_note?: string): Promise<RiskAlert> {
    const { data } = await api.patch<RiskAlert>(`/api/v1/risk-alerts/${alertId}/resolve`, {
      resolution_note,
    });
    return data;
  },
};
