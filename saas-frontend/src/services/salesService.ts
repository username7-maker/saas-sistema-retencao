import { api } from "./api";
import type { BookingStatus, CallScript, SalesBrief } from "../types";

export interface CallEventPayload {
  event_type: string;
  label?: string;
  details?: Record<string, unknown>;
  lost_reason?: string;
  next_step?: string;
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

  async createCallEvent(leadId: string, payload: CallEventPayload): Promise<{ message: string; lead_id: string; stage: string }> {
    const { data } = await api.post<{ message: string; lead_id: string; stage: string }>(
      `/api/v1/leads/${leadId}/call-events`,
      payload,
    );
    return data;
  },
};
