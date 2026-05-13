import { api } from "./api";
import type { PersonalAiContext, PersonalAiDraft, PersonalAiPrepareResult, PersonalAiSettings } from "../types";

interface ListDraftsParams {
  status?: string;
  member_id?: string;
}

interface CreateDraftPayload {
  question: string;
  domain?: "training_guidance" | "routine_support" | "assessment_explanation" | "body_composition_explanation";
  channel?: "internal" | "kommo";
}

export const personalAiService = {
  async getSettings(): Promise<PersonalAiSettings> {
    const { data } = await api.get<PersonalAiSettings>("/api/v1/settings/personal-ai");
    return data;
  },

  async updateSettings(payload: Partial<PersonalAiSettings>): Promise<PersonalAiSettings> {
    const { data } = await api.put<PersonalAiSettings>("/api/v1/settings/personal-ai", payload);
    return data;
  },

  async getContext(memberId: string): Promise<PersonalAiContext> {
    const { data } = await api.get<PersonalAiContext>(`/api/v1/members/${memberId}/personal-ai/context`);
    return data;
  },

  async createDraft(memberId: string, payload: CreateDraftPayload): Promise<PersonalAiDraft> {
    const { data } = await api.post<PersonalAiDraft>(`/api/v1/members/${memberId}/personal-ai/drafts`, payload);
    return data;
  },

  async listDrafts(params?: string | ListDraftsParams): Promise<PersonalAiDraft[]> {
    const requestParams = typeof params === "string" ? { status: params } : params;
    const { data } = await api.get<PersonalAiDraft[]>("/api/v1/personal-ai/drafts", {
      params: requestParams,
    });
    return data;
  },

  async prepareKommo(draftId: string): Promise<PersonalAiPrepareResult> {
    const { data } = await api.post<PersonalAiPrepareResult>(`/api/v1/personal-ai/drafts/${draftId}/prepare-kommo`);
    return data;
  },
};
