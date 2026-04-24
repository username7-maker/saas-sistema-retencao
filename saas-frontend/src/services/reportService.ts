import { api } from "./api";

export type DashboardReportType = "executive" | "operational" | "commercial" | "financial" | "retention" | "consolidated";

export interface AsyncJobAcceptedResponse {
  message: string;
  job_id: string;
  job_type: string;
  status: string;
}

export interface AsyncJobStatusResponse {
  job_id: string;
  job_type: string;
  status: string;
  attempt_count: number;
  max_attempts: number;
  next_retry_at?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  error_code?: string | null;
  error_message?: string | null;
  result?: Record<string, unknown> | null;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
}

function parseFilename(contentDisposition?: string): string {
  if (!contentDisposition) return "report.pdf";
  const match = /filename="?([^"]+)"?/i.exec(contentDisposition);
  return match?.[1] ?? "report.pdf";
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const reportService = {
  async exportDashboardPdf(dashboard: DashboardReportType): Promise<void> {
    const response = await api.get(`/api/v1/reports/dashboard/${dashboard}/pdf`, {
      responseType: "blob",
    });
    const filename = parseFilename(response.headers["content-disposition"]);
    triggerBrowserDownload(response.data, filename);
  },

  async dispatchMonthlyReports(): Promise<AsyncJobAcceptedResponse> {
    const { data } = await api.post<AsyncJobAcceptedResponse>("/api/v1/reports/monthly-dispatch");
    return data;
  },

  async getMonthlyDispatchStatus(jobId: string): Promise<AsyncJobStatusResponse> {
    const { data } = await api.get<AsyncJobStatusResponse>(`/api/v1/reports/monthly-dispatches/${jobId}`);
    return data;
  },
};
