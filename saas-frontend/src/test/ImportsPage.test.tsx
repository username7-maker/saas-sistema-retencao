import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ImportsPage } from "../pages/imports/ImportsPage";
import { importExportService } from "../services/importExportService";

vi.mock("../services/importExportService", () => ({
  importExportService: {
    previewMembers: vi.fn(),
    importMembers: vi.fn(),
    previewCheckins: vi.fn(),
    importCheckins: vi.fn(),
    previewAssessments: vi.fn(),
    importAssessments: vi.fn(),
    exportMembersCsv: vi.fn(),
    exportCheckinsCsv: vi.fn(),
    downloadMembersTemplateCsv: vi.fn(),
    downloadCheckinsTemplateCsv: vi.fn(),
  },
}));

vi.mock("react-hot-toast", () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ImportsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ImportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(importExportService.previewMembers).mockResolvedValue({
      preview_kind: "members",
      total_rows: 1,
      valid_rows: 1,
      would_create: 1,
      would_update: 0,
      would_skip: 0,
      ignored_rows: 0,
      provisional_members_possible: 0,
      recognized_columns: ["nome", "email"],
      unrecognized_columns: [],
      detected_columns: ["nome", "email"],
      suggested_mapping: { nome: "full_name", email: "email" },
      mapping_options: [
        { value: "full_name", label: "Nome completo", required: false },
        { value: "email", label: "E-mail", required: false },
      ],
      missing_required_fields: [],
      duplicate_target_fields: [],
      mapping_ready: true,
      missing_members: [],
      warnings: [],
      sample_rows: [
        {
          row_number: 2,
          action: "create_member",
          preview: { full_name: "Ana Silva", email: "ana@teste.com", plan_name: "Plano Base" },
        },
      ],
      errors: [],
    });
    vi.mocked(importExportService.importMembers).mockResolvedValue({
      imported: 1,
      skipped_duplicates: 0,
      ignored_rows: 0,
      provisional_members_created: 0,
      provisional_members: [],
      missing_members: [],
      errors: [],
    });
    vi.mocked(importExportService.previewCheckins).mockResolvedValue({
      preview_kind: "checkins",
      total_rows: 0,
      valid_rows: 0,
      would_create: 0,
      would_update: 0,
      would_skip: 0,
      ignored_rows: 0,
      provisional_members_possible: 0,
      recognized_columns: [],
      unrecognized_columns: [],
      detected_columns: [],
      suggested_mapping: {},
      mapping_options: [],
      missing_required_fields: [],
      duplicate_target_fields: [],
      mapping_ready: true,
      missing_members: [],
      warnings: [],
      sample_rows: [],
      errors: [],
    });
    vi.mocked(importExportService.importCheckins).mockResolvedValue({
      imported: 0,
      skipped_duplicates: 0,
      ignored_rows: 0,
      provisional_members_created: 0,
      provisional_members: [],
      missing_members: [],
      errors: [],
    });
    vi.mocked(importExportService.previewAssessments).mockResolvedValue({
      preview_kind: "assessments",
      total_rows: 0,
      valid_rows: 0,
      would_create: 0,
      would_update: 0,
      would_skip: 0,
      ignored_rows: 0,
      provisional_members_possible: 0,
      recognized_columns: [],
      unrecognized_columns: [],
      detected_columns: [],
      suggested_mapping: {},
      mapping_options: [],
      missing_required_fields: [],
      duplicate_target_fields: [],
      mapping_ready: true,
      missing_members: [],
      warnings: [],
      sample_rows: [],
      errors: [],
    });
    vi.mocked(importExportService.importAssessments).mockResolvedValue({
      imported: 0,
      skipped_duplicates: 0,
      ignored_rows: 0,
      provisional_members_created: 0,
      provisional_members: [],
      missing_members: [],
      errors: [],
    });
    vi.mocked(importExportService.exportMembersCsv).mockResolvedValue();
    vi.mocked(importExportService.exportCheckinsCsv).mockResolvedValue();
    vi.mocked(importExportService.downloadMembersTemplateCsv).mockResolvedValue();
    vi.mocked(importExportService.downloadCheckinsTemplateCsv).mockResolvedValue();
  });

  it("requires preview before confirming members import", async () => {
    const { container } = renderPage();
    const fileInputs = container.querySelectorAll('input[type="file"]');
    const membersFileInput = fileInputs[0] as HTMLInputElement;
    const file = new File(["nome,email\nAna Silva,ana@teste.com"], "membros.csv", { type: "text/csv" });

    fireEvent.change(membersFileInput, { target: { files: [file] } });
    fireEvent.click(screen.getAllByRole("button", { name: "Validar arquivo" })[0]);

    expect(await screen.findByText("Preview validado. Nada foi gravado ainda.")).toBeInTheDocument();

    fireEvent.click(screen.getAllByRole("button", { name: "Confirmar importacao" })[0]);

    await waitFor(() => {
      expect(importExportService.importMembers).toHaveBeenCalledWith(file, {
        email: "email",
        nome: "full_name",
      });
    });
  });
});
