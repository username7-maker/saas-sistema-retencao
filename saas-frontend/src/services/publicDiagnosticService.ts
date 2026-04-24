import { api } from "./api";


export interface PublicDiagnosisQueuedResponse {
  message: string;
  diagnosis_id: string;
  job_id: string;
  lead_id: string;
  status: string;
}

export interface PublicDiagnosisStatusResponse {
  diagnosis_id: string;
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

export interface PublicDiagnosisInput {
  fullName: string;
  email: string;
  whatsapp: string;
  gymName: string;
  totalMembers: number;
  avgMonthlyFee: number;
  csvFile: File;
}

export const publicDiagnosticService = {
  async submitDiagnosis(input: PublicDiagnosisInput): Promise<PublicDiagnosisQueuedResponse> {
    const form = new FormData();
    form.append("full_name", input.fullName);
    form.append("email", input.email);
    form.append("whatsapp", input.whatsapp);
    form.append("gym_name", input.gymName);
    form.append("total_members", String(input.totalMembers));
    form.append("avg_monthly_fee", String(input.avgMonthlyFee));
    form.append("csv_file", input.csvFile);

    const response = await api.post<PublicDiagnosisQueuedResponse>("/api/v1/public/diagnostico", form, {
      headers: { "Content-Type": "multipart/form-data" },
      timeout: 120000,
    });
    return response.data;
  },

  async getDiagnosisStatus(diagnosisId: string, leadId: string): Promise<PublicDiagnosisStatusResponse> {
    const response = await api.get<PublicDiagnosisStatusResponse>(`/api/v1/public/diagnostico/${diagnosisId}/status`, {
      params: { lead_id: leadId },
      timeout: 20000,
    });
    return response.data;
  },
};
