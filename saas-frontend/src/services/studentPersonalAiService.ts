import { api } from "./api";
import type { StudentPersonalAiDraft, StudentPersonalAiPrepareResult, StudentPersonalAiSettings } from "../types";

interface ListDraftsParams {
  status?: string;
  member_id?: string;
}

export const studentPersonalAiService = {
  async getSettings(): Promise<StudentPersonalAiSettings> {
    const { data } = await api.get<StudentPersonalAiSettings>("/api/v1/settings/student-personal-ai");
    return data;
  },

  async updateSettings(payload: Partial<StudentPersonalAiSettings>): Promise<StudentPersonalAiSettings> {
    const { data } = await api.put<StudentPersonalAiSettings>("/api/v1/settings/student-personal-ai", payload);
    return data;
  },

  async listDrafts(params?: string | ListDraftsParams): Promise<StudentPersonalAiDraft[]> {
    const requestParams = typeof params === "string" ? { status: params } : params;
    const { data } = await api.get<StudentPersonalAiDraft[]>("/api/v1/ai/student-personal/drafts", {
      params: requestParams,
    });
    return data;
  },

  async prepareKommo(draftId: string): Promise<StudentPersonalAiPrepareResult> {
    const { data } = await api.post<StudentPersonalAiPrepareResult>(`/api/v1/ai/student-personal/drafts/${draftId}/prepare-kommo`);
    return data;
  },

  async reject(draftId: string, reason: string): Promise<StudentPersonalAiDraft> {
    const { data } = await api.post<StudentPersonalAiDraft>(`/api/v1/ai/student-personal/drafts/${draftId}/reject`, { reason });
    return data;
  },
};
