import { api } from "./api";
import type { ConsentStatus, ConsentType, MemberConsentRecord, MemberConsentSummary } from "../types";

export interface MemberConsentRecordPayload {
  consent_type: ConsentType;
  status?: Exclude<ConsentStatus, "missing">;
  source?: string;
  document_title?: string;
  document_version?: string;
  evidence_ref?: string;
  notes?: string;
  signed_at?: string;
  expires_at?: string;
  extra_data?: Record<string, unknown>;
}

export const lgpdService = {
  async getMemberConsents(memberId: string): Promise<MemberConsentSummary> {
    const { data } = await api.get<MemberConsentSummary>(`/api/v1/lgpd/member/${memberId}/consents`);
    return data;
  },

  async recordMemberConsent(memberId: string, payload: MemberConsentRecordPayload): Promise<MemberConsentRecord> {
    const { data } = await api.post<MemberConsentRecord>(`/api/v1/lgpd/member/${memberId}/consents`, payload);
    return data;
  },

  async exportMemberPdf(memberId: string): Promise<void> {
    const { data } = await api.get(`/api/v1/lgpd/export/member/${memberId}`, {
      responseType: "blob",
    });
    const url = window.URL.createObjectURL(new Blob([data as BlobPart]));
    const link = document.createElement("a");
    link.href = url;
    link.download = `dados_membro_${memberId}.pdf`;
    link.click();
    window.URL.revokeObjectURL(url);
  },

  async anonymizeMember(memberId: string): Promise<void> {
    await api.post(`/api/v1/lgpd/anonymize/member/${memberId}`);
  },
};
