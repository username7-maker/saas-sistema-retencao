import { api } from "./api";
import type {
  AcquisitionCaptureResponse,
  AcquisitionLeadSummary,
  GrowthAudience,
  GrowthChannel,
  GrowthOpportunityPrepared,
  Lead,
  LeadNoteEntry,
  PaginatedResponse,
} from "../types";

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

export interface AcquisitionCapturePayload {
  full_name: string;
  email?: string;
  phone?: string;
  source?: string;
  channel?: string;
  campaign?: string;
  desired_goal?: string;
  preferred_shift?: string;
  trial_interest?: boolean;
  scheduled_for?: string;
  consent_lgpd?: boolean;
  consent_communication?: boolean;
  operator_note?: string;
  qualification_answers?: Record<string, unknown>;
  estimated_value?: number;
  acquisition_cost?: number;
  owner_id?: string;
}

export interface GrowthOpportunityPreparePayload {
  channel?: GrowthChannel;
  operator_note?: string;
  create_task?: boolean;
}

function hasIsoDate(value: unknown): value is string {
  return typeof value === "string" && !Number.isNaN(Date.parse(value));
}

function normalizeLeadNoteEntry(raw: string | Record<string, unknown>, index: number): LeadNoteEntry | null {
  if (typeof raw === "string") {
    const text = raw.trim();
    if (!text) return null;
    return {
      id: `legacy-${index}-${text.slice(0, 24)}`,
      text,
      type: "note",
      channel: null,
      outcome: null,
      created_at: null,
      author_name: null,
      author_role: null,
      legacy: true,
    };
  }

  const noteValue = typeof raw.note === "string" ? raw.note.trim() : "";
  const textValue = typeof raw.text === "string" ? raw.text.trim() : "";
  const text = noteValue || textValue;
  if (!text) return null;

  const createdAt = hasIsoDate(raw.created_at)
    ? raw.created_at
    : hasIsoDate(raw.occurred_at)
      ? raw.occurred_at
      : null;

  return {
    id:
      typeof raw.id === "string" && raw.id.trim()
        ? raw.id
        : `${createdAt ?? "note"}-${index}-${text.slice(0, 24)}`,
    text,
    type:
      typeof raw.type === "string" && raw.type.trim()
        ? raw.type
        : typeof raw.entry_type === "string" && raw.entry_type.trim()
          ? raw.entry_type
          : "note",
    channel: typeof raw.channel === "string" && raw.channel.trim() ? raw.channel : null,
    outcome: typeof raw.outcome === "string" && raw.outcome.trim() ? raw.outcome : null,
    created_at: createdAt,
    author_name: typeof raw.author_name === "string" && raw.author_name.trim() ? raw.author_name : null,
    author_role: typeof raw.author_role === "string" && raw.author_role.trim() ? raw.author_role : null,
    legacy: typeof raw.type !== "string" && typeof raw.entry_type !== "string",
  };
}

export function normalizeLeadNotes(notes: Lead["notes"]): LeadNoteEntry[] {
  if (!Array.isArray(notes)) return [];

  return notes
    .map((entry, index) => normalizeLeadNoteEntry(entry, index))
    .filter((entry): entry is LeadNoteEntry => entry !== null)
    .sort((left, right) => {
      const leftTime = left.created_at ? Date.parse(left.created_at) : Number.NaN;
      const rightTime = right.created_at ? Date.parse(right.created_at) : Number.NaN;
      if (Number.isFinite(leftTime) && Number.isFinite(rightTime)) {
        return rightTime - leftTime;
      }
      if (Number.isFinite(rightTime)) return 1;
      if (Number.isFinite(leftTime)) return -1;
      return 0;
    });
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

  async captureAcquisitionLead(payload: AcquisitionCapturePayload): Promise<AcquisitionCaptureResponse> {
    const { data } = await api.post<AcquisitionCaptureResponse>("/api/v1/crm/acquisition/capture", payload);
    return data;
  },

  async listAcquisitionSummaries(): Promise<AcquisitionLeadSummary[]> {
    const { data } = await api.get<AcquisitionLeadSummary[]>("/api/v1/crm/acquisition/summary");
    return data;
  },

  async listGrowthAudiences(): Promise<GrowthAudience[]> {
    const { data } = await api.get<GrowthAudience[]>("/api/v1/crm/growth/audiences", {
      params: { limit_per_audience: 30 },
    });
    return data;
  },

  async prepareGrowthOpportunity(
    opportunityId: string,
    payload: GrowthOpportunityPreparePayload,
  ): Promise<GrowthOpportunityPrepared> {
    const { data } = await api.post<GrowthOpportunityPrepared>(
      `/api/v1/crm/growth/opportunities/${encodeURIComponent(opportunityId)}/prepare`,
      payload,
    );
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
