import { api } from "./api";
import type { AutopilotMetrics, AutopilotSettings } from "../types";

export type AutopilotSettingsPayload = Partial<AutopilotSettings>;

export const autopilotService = {
  async getSettings(): Promise<AutopilotSettings> {
    const { data } = await api.get<AutopilotSettings>("/api/v1/settings/autopilot");
    return data;
  },

  async updateSettings(payload: AutopilotSettingsPayload): Promise<AutopilotSettings> {
    const { data } = await api.put<AutopilotSettings>("/api/v1/settings/autopilot", payload);
    return data;
  },

  async getMetrics(): Promise<AutopilotMetrics> {
    const { data } = await api.get<AutopilotMetrics>("/api/v1/autopilot/metrics");
    return data;
  },
};
