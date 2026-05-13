import { api } from "./api";
import type { AiServiceAgentDraft, AiServiceAgentPrepareResult, AiServiceAgentSettings } from "../types";

export const aiServiceAgentService = {
  async getSettings(): Promise<AiServiceAgentSettings> {
    const { data } = await api.get<AiServiceAgentSettings>("/api/v1/settings/ai-service-agent");
    return data;
  },

  async updateSettings(payload: Partial<AiServiceAgentSettings>): Promise<AiServiceAgentSettings> {
    const { data } = await api.put<AiServiceAgentSettings>("/api/v1/settings/ai-service-agent", payload);
    return data;
  },

  async listDrafts(status?: string): Promise<AiServiceAgentDraft[]> {
    const { data } = await api.get<AiServiceAgentDraft[]>("/api/v1/ai/service-agent/drafts", {
      params: status ? { status } : undefined,
    });
    return data;
  },

  async prepareKommo(draftId: string): Promise<AiServiceAgentPrepareResult> {
    const { data } = await api.post<AiServiceAgentPrepareResult>(`/api/v1/ai/service-agent/drafts/${draftId}/prepare-kommo`);
    return data;
  },
};
