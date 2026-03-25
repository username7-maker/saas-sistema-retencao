import { api } from "./api";
import type { ImportPreview, ImportSummary } from "../types";

export interface ImportMappingPayload {
  columnMappings?: Record<string, string>;
  ignoredColumns?: string[];
}

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

function normalizeImportPreview(data: unknown): ImportPreview {
  const preview = (data && typeof data === "object" ? data : {}) as Partial<ImportPreview>;
  const unrecognizedColumns = Array.isArray(preview.unrecognized_columns) ? preview.unrecognized_columns : [];
  const sourceColumns = Array.isArray(preview.source_columns) ? preview.source_columns : [];

  return {
    preview_kind: typeof preview.preview_kind === "string" ? preview.preview_kind : "unknown",
    total_rows: typeof preview.total_rows === "number" ? preview.total_rows : 0,
    valid_rows: typeof preview.valid_rows === "number" ? preview.valid_rows : 0,
    would_create: typeof preview.would_create === "number" ? preview.would_create : 0,
    would_update: typeof preview.would_update === "number" ? preview.would_update : 0,
    would_skip: typeof preview.would_skip === "number" ? preview.would_skip : 0,
    ignored_rows: typeof preview.ignored_rows === "number" ? preview.ignored_rows : 0,
    provisional_members_possible:
      typeof preview.provisional_members_possible === "number" ? preview.provisional_members_possible : 0,
    recognized_columns: Array.isArray(preview.recognized_columns) ? preview.recognized_columns : [],
    unrecognized_columns: unrecognizedColumns,
    missing_members: Array.isArray(preview.missing_members) ? preview.missing_members : [],
    warnings: Array.isArray(preview.warnings) ? preview.warnings : [],
    sample_rows: Array.isArray(preview.sample_rows) ? preview.sample_rows : [],
    mapping_required:
      typeof preview.mapping_required === "boolean" ? preview.mapping_required : unrecognizedColumns.length > 0,
    can_confirm:
      typeof preview.can_confirm === "boolean"
        ? preview.can_confirm
        : sourceColumns.length === 0 && unrecognizedColumns.length === 0,
    resolved_mappings:
      preview.resolved_mappings && typeof preview.resolved_mappings === "object" ? preview.resolved_mappings : {},
    ignored_columns: Array.isArray(preview.ignored_columns) ? preview.ignored_columns : [],
    conflicting_targets: Array.isArray(preview.conflicting_targets) ? preview.conflicting_targets : [],
    blocking_issues: Array.isArray(preview.blocking_issues) ? preview.blocking_issues : [],
    source_columns: sourceColumns,
    errors: Array.isArray(preview.errors) ? preview.errors : [],
  };
}

export const importExportService = {
  async previewMembers(file: File, mapping?: ImportMappingPayload): Promise<ImportPreview> {
    const form = new FormData();
    form.append("file", file);
    if (mapping?.columnMappings && Object.keys(mapping.columnMappings).length > 0) {
      form.append("column_mappings", JSON.stringify(mapping.columnMappings));
    }
    if (mapping?.ignoredColumns && mapping.ignoredColumns.length > 0) {
      form.append("ignored_columns", JSON.stringify(mapping.ignoredColumns));
    }
    const response = await api.post("/api/v1/imports/members/preview", form, { timeout: 2 * 60 * 1000 });
    return normalizeImportPreview(response.data);
  },

  async importMembers(file: File, mapping?: ImportMappingPayload): Promise<ImportSummary> {
    const form = new FormData();
    form.append("file", file);
    if (mapping?.columnMappings && Object.keys(mapping.columnMappings).length > 0) {
      form.append("column_mappings", JSON.stringify(mapping.columnMappings));
    }
    if (mapping?.ignoredColumns && mapping.ignoredColumns.length > 0) {
      form.append("ignored_columns", JSON.stringify(mapping.ignoredColumns));
    }
    const response = await api.post("/api/v1/imports/members", form, { timeout: 10 * 60 * 1000 });
    return response.data;
  },

  async previewCheckins(
    file: File,
    autoCreateMissingMembers = false,
    mapping?: ImportMappingPayload,
  ): Promise<ImportPreview> {
    const form = new FormData();
    form.append("file", file);
    form.append("auto_create_missing_members", String(autoCreateMissingMembers));
    if (mapping?.columnMappings && Object.keys(mapping.columnMappings).length > 0) {
      form.append("column_mappings", JSON.stringify(mapping.columnMappings));
    }
    if (mapping?.ignoredColumns && mapping.ignoredColumns.length > 0) {
      form.append("ignored_columns", JSON.stringify(mapping.ignoredColumns));
    }
    const response = await api.post("/api/v1/imports/checkins/preview", form, { timeout: 2 * 60 * 1000 });
    return normalizeImportPreview(response.data);
  },

  async importCheckins(
    file: File,
    autoCreateMissingMembers = false,
    mapping?: ImportMappingPayload,
  ): Promise<ImportSummary> {
    const form = new FormData();
    form.append("file", file);
    form.append("auto_create_missing_members", String(autoCreateMissingMembers));
    if (mapping?.columnMappings && Object.keys(mapping.columnMappings).length > 0) {
      form.append("column_mappings", JSON.stringify(mapping.columnMappings));
    }
    if (mapping?.ignoredColumns && mapping.ignoredColumns.length > 0) {
      form.append("ignored_columns", JSON.stringify(mapping.ignoredColumns));
    }
    const response = await api.post("/api/v1/imports/checkins", form, { timeout: 10 * 60 * 1000 });
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
