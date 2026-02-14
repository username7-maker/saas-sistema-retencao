import { api } from "./api";
import type { Lead, PaginatedResponse } from "../types";

export const crmService = {
  async listLeads(): Promise<PaginatedResponse<Lead>> {
    const { data } = await api.get<PaginatedResponse<Lead>>("/api/v1/crm/leads", {
      params: { page_size: 200 },
    });
    return data;
  },

  async updateLeadStage(leadId: string, stage: Lead["stage"]): Promise<Lead> {
    const { data } = await api.patch<Lead>(`/api/v1/crm/leads/${leadId}`, { stage });
    return data;
  },
};
