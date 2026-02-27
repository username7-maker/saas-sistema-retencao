import { api } from "./api";
import type { Lead, PaginatedResponse } from "../types";

export interface LeadCreatePayload {
  full_name: string;
  email?: string;
  phone?: string;
  source?: string;
  estimated_value?: number;
  notes?: string;
}

export interface LeadUpdatePayload {
  full_name?: string;
  email?: string;
  phone?: string;
  source?: string;
  estimated_value?: number;
  stage?: Lead["stage"];
  notes?: string;
  lost_reason?: string;
}

export const crmService = {
  async listLeads(): Promise<PaginatedResponse<Lead>> {
    const { data } = await api.get<PaginatedResponse<Lead>>("/api/v1/crm/leads", {
      params: { page_size: 200 },
    });
    return data;
  },

  async createLead(payload: LeadCreatePayload): Promise<Lead> {
    const { data } = await api.post<Lead>("/api/v1/crm/leads", payload);
    return data;
  },

  async updateLead(leadId: string, payload: LeadUpdatePayload): Promise<Lead> {
    const { data } = await api.patch<Lead>(`/api/v1/crm/leads/${leadId}`, payload);
    return data;
  },

  async updateLeadStage(leadId: string, stage: Lead["stage"]): Promise<Lead> {
    return crmService.updateLead(leadId, { stage });
  },

  async deleteLead(leadId: string): Promise<void> {
    await api.delete(`/api/v1/crm/leads/${leadId}`);
  },
};
