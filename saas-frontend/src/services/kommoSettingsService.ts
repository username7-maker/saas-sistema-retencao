import type { KommoConnectionTestResult, KommoNativeFileUploadTestResult, KommoSettings, KommoSettingsUpdateInput } from "../types";
import { api } from "./api";

export const kommoSettingsService = {
  async getSettings(): Promise<KommoSettings> {
    const { data } = await api.get<KommoSettings>("/api/v1/settings/kommo");
    return data;
  },

  async updateSettings(payload: KommoSettingsUpdateInput): Promise<KommoSettings> {
    const { data } = await api.put<KommoSettings>("/api/v1/settings/kommo", payload);
    return data;
  },

  async testConnection(): Promise<KommoConnectionTestResult> {
    const { data } = await api.post<KommoConnectionTestResult>("/api/v1/settings/kommo/test-connection");
    return data;
  },

  async testNativeFileUpload(leadId?: string | null): Promise<KommoNativeFileUploadTestResult> {
    const { data } = await api.post<KommoNativeFileUploadTestResult>("/api/v1/kommo/test-native-file-upload", {
      lead_id: leadId?.trim() || null,
    });
    return data;
  },
};
