import { api } from "./api";

export type DashboardReportType = "executive" | "operational" | "commercial" | "financial" | "retention" | "consolidated";

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

  async dispatchMonthlyReports(): Promise<void> {
    await api.post("/api/v1/reports/monthly-dispatch");
  },
};
