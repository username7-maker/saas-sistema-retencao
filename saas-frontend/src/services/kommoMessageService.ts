import { api } from "./api";

export type KommoSendDomain =
  | "retention"
  | "onboarding"
  | "assessment"
  | "body_composition"
  | "finance"
  | "sales"
  | "student_ai"
  | "support";

export type KommoPdfDeliveryMode = "native_file_required" | "native_file_preferred" | "link_only";

export interface KommoSendMessagePayload {
  member_id?: string | null;
  lead_id?: string | null;
  domain: KommoSendDomain;
  message_text: string;
  source_type: string;
  source_id: string;
  pdf_kind?: "summary" | "technical" | null;
  pdf_delivery_mode?: KommoPdfDeliveryMode | null;
}

export interface KommoSendMessageResult {
  status: string;
  delivery_mode: string;
  detail: string | null;
  member_id: string | null;
  local_lead_id: string | null;
  source_type: string;
  source_id: string;
  domain: string;
  lead_id: string | null;
  contact_id: string | null;
  task_id: string | null;
  message_log_id: string | null;
  salesbot_id: string | null;
  pdf_url: string | null;
  kommo_file_uuid: string | null;
  file_upload_status: string | null;
  file_attach_status: string | null;
  pdf_delivery_mode: string | null;
  fallback_available: boolean;
}

export const kommoMessageService = {
  async sendMessage(payload: KommoSendMessagePayload): Promise<KommoSendMessageResult> {
    const { data } = await api.post<KommoSendMessageResult>("/api/v1/kommo/send-message", payload);
    return data;
  },
};
