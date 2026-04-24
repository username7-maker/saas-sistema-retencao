import { api } from "./api";
import type { BookingStatus, CallScript, SalesBrief } from "../types";

export interface CallEventPayload {
  event_type: string;
  label?: string;
  details?: Record<string, unknown>;
  lost_reason?: string;
  next_step?: string;
}

export interface CallEventResponse {
  message: string;
  lead_id: string;
  stage: string;
  job_id?: string | null;
  job_status?: string | null;
}

export interface ProposalDispatchStatusResponse {
  lead_id: string;
  job_id: string;
  job_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  next_retry_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_code: string | null;
  error_message: string | null;
  result: Record<string, unknown> | null;
  related_entity_type: string | null;
  related_entity_id: string | null;
}

export const salesService = {
  async getSalesBrief(leadId: string): Promise<SalesBrief> {
    const { data } = await api.get<SalesBrief>(`/api/v1/leads/${leadId}/sales-brief`);
    return data;
  },

  async getCallScript(leadId: string): Promise<CallScript> {
    const { data } = await api.get<CallScript>(`/api/v1/leads/${leadId}/call-script`);
    return data;
  },

  async getBookingStatus(leadId: string): Promise<BookingStatus> {
    const { data } = await api.get<BookingStatus>(`/api/v1/leads/${leadId}/booking-status`);
    return data;
  },

  async createCallEvent(leadId: string, payload: CallEventPayload): Promise<CallEventResponse> {
    const { data } = await api.post<CallEventResponse>(
      `/api/v1/leads/${leadId}/call-events`,
      payload,
    );
    return data;
  },

  async getProposalDispatchStatus(leadId: string, jobId: string): Promise<ProposalDispatchStatusResponse> {
    const { data } = await api.get<ProposalDispatchStatusResponse>(
      `/api/v1/leads/${leadId}/proposal-dispatches/${jobId}`,
    );
    return data;
  },
};
