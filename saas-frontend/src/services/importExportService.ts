import { api } from "./api";
import type { ImportPreview, ImportSummary } from "../types";


function parseFilename(contentDisposition?: string): string {
  if (!contentDisposition) return "export.csv";
  const match = /filename="?([^"]+)"?/i.exec(contentDisposition);
  return match?.[1] ?? "export.csv";
}

function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const importExportService = {
  async previewMembers(file: File): Promise<ImportPreview> {
    const form = new FormData();
    form.append("file", file);
    const response = await api.post("/api/v1/imports/members/preview", form, { timeout: 2 * 60 * 1000 });
    return response.data;
  },

  async importMembers(file: File): Promise<ImportSummary> {
    const form = new FormData();
    form.append("file", file);
    const response = await api.post("/api/v1/imports/members", form, { timeout: 10 * 60 * 1000 });
    return response.data;
  },

  async previewCheckins(file: File, autoCreateMissingMembers = false): Promise<ImportPreview> {
    const form = new FormData();
    form.append("file", file);
    form.append("auto_create_missing_members", String(autoCreateMissingMembers));
    const response = await api.post("/api/v1/imports/checkins/preview", form, { timeout: 2 * 60 * 1000 });
    return response.data;
  },

  async importCheckins(file: File, autoCreateMissingMembers = false): Promise<ImportSummary> {
    const form = new FormData();
    form.append("file", file);
    form.append("auto_create_missing_members", String(autoCreateMissingMembers));
    const response = await api.post("/api/v1/imports/checkins", form, { timeout: 10 * 60 * 1000 });
    return response.data;
  },

  async previewAssessments(file: File): Promise<ImportPreview> {
    const form = new FormData();
    form.append("file", file);
    const response = await api.post("/api/v1/imports/assessments/preview", form, { timeout: 2 * 60 * 1000 });
    return response.data;
  },

  async importAssessments(file: File): Promise<ImportSummary> {
    const form = new FormData();
    form.append("file", file);
    const response = await api.post("/api/v1/imports/assessments", form, { timeout: 10 * 60 * 1000 });
    return response.data;
  },

  async exportMembersCsv(): Promise<void> {
    const response = await api.get("/api/v1/exports/members.csv", { responseType: "blob" });
    const filename = parseFilename(response.headers["content-disposition"]);
    downloadBlob(response.data, filename);
  },

  async exportCheckinsCsv(dateFrom?: string, dateTo?: string): Promise<void> {
    const params = new URLSearchParams();
    if (dateFrom) params.set("date_from", dateFrom);
    if (dateTo) params.set("date_to", dateTo);
    const suffix = params.toString() ? `?${params.toString()}` : "";
    const response = await api.get(`/api/v1/exports/checkins.csv${suffix}`, { responseType: "blob" });
    const filename = parseFilename(response.headers["content-disposition"]);
    downloadBlob(response.data, filename);
  },

  async downloadMembersTemplateCsv(): Promise<void> {
    const response = await api.get("/api/v1/exports/templates/members.csv", { responseType: "blob" });
    const filename = parseFilename(response.headers["content-disposition"]);
    downloadBlob(response.data, filename);
  },

  async downloadCheckinsTemplateCsv(): Promise<void> {
    const response = await api.get("/api/v1/exports/templates/checkins.csv", { responseType: "blob" });
    const filename = parseFilename(response.headers["content-disposition"]);
    downloadBlob(response.data, filename);
  },
};
