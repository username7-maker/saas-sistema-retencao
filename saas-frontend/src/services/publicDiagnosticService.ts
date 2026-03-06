import { api } from "./api";


export interface PublicDiagnosisQueuedResponse {
  message: string;
  diagnosis_id: string;
  lead_id: string;
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
};
