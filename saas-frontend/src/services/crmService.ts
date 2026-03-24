import { api } from "./api";
import type { Lead, PaginatedResponse } from "../types";

export interface LeadCreatePayload {
  full_name: string;
  email?: string;
  phone?: string;
  source?: string;
  estimated_value?: number;
  notes?: Array<string | Record<string, unknown>>;
}

export interface LeadConversionHandoffPayload {
  plan_name: string;
  join_date: string;
  email_confirmed: boolean;
  phone_confirmed: boolean;
  notes?: string;
}

export interface LeadUpdatePayload {
  full_name?: string;
  email?: string;
  phone?: string;
  source?: string;
  estimated_value?: number;
  stage?: Lead["stage"];
  notes?: Array<string | Record<string, unknown>>;
  lost_reason?: string;
  conversion_handoff?: LeadConversionHandoffPayload;
}

export interface LeadNotePayload {
  text: string;
  entry_type?: string;
  channel?: string;
  outcome?: string;
  occurred_at?: string;
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

  async appendLeadNote(leadId: string, payload: LeadNotePayload): Promise<Lead> {
    const { data } = await api.post<Lead>(`/api/v1/crm/leads/${leadId}/notes`, payload);
    return data;
  },
};
