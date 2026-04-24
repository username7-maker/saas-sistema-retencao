import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MemberBodyCompositionTab } from "../components/assessments/MemberBodyCompositionTab";
import { actuarSettingsService } from "../services/actuarSettingsService";
import { bodyCompositionService } from "../services/bodyCompositionService";
import type { ActuarSettings, BodyCompositionActuarSyncStatus, BodyCompositionEvaluation } from "../types";

vi.mock("../hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "user-1", role: "owner", full_name: "Automicai Owner" },
  }),
}));

vi.mock("../services/bodyCompositionService", () => ({
  bodyCompositionService: {
    list: vi.fn(),
    getActuarSyncStatus: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    retryActuarSync: vi.fn(),
    enqueueActuarSync: vi.fn(),
    confirmManualSync: vi.fn(),
    upsertActuarLink: vi.fn(),
    sendWhatsAppSummary: vi.fn(),
    sendKommoHandoff: vi.fn(),
    getManualSyncSummary: vi.fn(),
    readWithAssistedFallback: vi.fn(),
    openPdf: vi.fn(),
  },
}));

vi.mock("../services/actuarSettingsService", () => ({
  actuarSettingsService: {
    getSettings: vi.fn(),
  },
}));

function makeEvaluation(): BodyCompositionEvaluation {
  return {
    id: "eval-1",
    gym_id: "gym-1",
    member_id: "member-1",
    evaluation_date: "2026-04-14",
    measured_at: "2026-04-14T10:00:00Z",
    age_years: 21,
    sex: "female",
    height_cm: 168,
    weight_kg: 64.2,
    body_fat_kg: 17.1,
    body_fat_percent: 26.6,
    waist_hip_ratio: 0.82,
    fat_free_mass_kg: 47.1,
    inorganic_salt_kg: 2.9,
    protein_kg: 13.8,
    body_water_kg: 34.8,
    lean_mass_kg: null,
    muscle_mass_kg: 25.7,
    skeletal_muscle_kg: 24.1,
    body_water_percent: null,
    visceral_fat_level: 7.2,
    bmi: 22.8,
    basal_metabolic_rate_kcal: 1420,
    target_weight_kg: 61.5,
    weight_control_kg: -2.7,
    muscle_control_kg: 0.4,
    fat_control_kg: -3.1,
    total_energy_kcal: 2180,
    physical_age: 24,
    health_score: 78,
    source: "ocr_receipt",
    notes: "Boa evolucao geral.",
    report_file_url: null,
    raw_ocr_text: "tezewa raw",
    ocr_confidence: 0.91,
    parsing_confidence: 0.91,
    ocr_warnings_json: [],
    data_quality_flags_json: [],
    needs_review: false,
    reviewed_manually: true,
    reviewer_user_id: "user-1",
    device_model: "tezewa_t6100",
    device_profile: "tezewa_receipt_v1",
    parsed_from_image: true,
    ocr_source_file_ref: "local://tezewa.jpg",
    import_batch_id: null,
    measured_ranges_json: null,
    ai_coach_summary: null,
    ai_member_friendly_summary: null,
    ai_risk_flags_json: [],
    ai_training_focus_json: null,
    ai_generated_at: null,
    actuar_sync_status: "saved",
    actuar_sync_mode: "disabled",
    actuar_external_id: null,
    actuar_last_synced_at: null,
    actuar_last_error: null,
    sync_required_for_training: false,
    sync_last_attempt_at: null,
    sync_last_success_at: null,
    sync_last_error_code: null,
    sync_last_error_message: null,
    actuar_sync_job_id: null,
    training_ready: true,
    created_at: "2026-04-14T10:30:00Z",
    updated_at: "2026-04-14T10:30:00Z",
    assistant: null,
  };
}

function makeSyncStatus(): BodyCompositionActuarSyncStatus {
  return {
    evaluation_id: "eval-1",
    member_id: "member-1",
    sync_mode: "disabled",
    sync_status: "saved",
    training_ready: true,
    sync_required_for_training: false,
    external_id: null,
    last_synced_at: null,
    last_attempt_at: null,
    last_error_code: null,
    last_error: null,
    can_retry: false,
    critical_fields: [],
    unsupported_fields: [],
    fallback_manual_summary: {
      evaluation_id: "eval-1",
      member_id: "member-1",
      sync_status: "saved",
      training_ready: true,
      critical_fields: [],
      summary_text: "",
    },
    current_job: null,
    attempts: [],
    member_link: null,
  };
}

function makeSettings(): ActuarSettings {
  return {
    actuar_enabled: false,
    actuar_auto_sync_body_composition: false,
    actuar_base_url: null,
    actuar_username: null,
    actuar_has_password: false,
    environment_enabled: false,
    environment_sync_mode: "disabled",
    effective_sync_mode: "disabled",
    automatic_sync_ready: false,
    bridge_device_count: 0,
    bridge_online_device_count: 0,
    bridge_devices: [],
  };
}

function renderTab() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <MemberBodyCompositionTab memberId="member-1" memberName="Evelane" memberPhone="11999990000" />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("MemberBodyCompositionTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(bodyCompositionService.list).mockResolvedValue([makeEvaluation()]);
    vi.mocked(bodyCompositionService.getActuarSyncStatus).mockResolvedValue(makeSyncStatus());
    vi.mocked(actuarSettingsService.getSettings).mockResolvedValue(makeSettings());
  });

  it("shows the premium report CTA in the member workspace for an existing evaluation", async () => {
    renderTab();

    expect(await screen.findByText("Relatorio premium pronto")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir relatorio" })).toHaveAttribute(
      "href",
      "/assessments/members/member-1/body-composition/eval-1/report",
    );
    expect(screen.getByRole("button", { name: "Resumo do aluno" })).toBeInTheDocument();
    expect(screen.getByText("Sexo: Feminino")).toBeInTheDocument();
  });

  it("opens the summary pdf through the authenticated service instead of navigating to /api directly", async () => {
    vi.mocked(bodyCompositionService.openPdf).mockResolvedValue(undefined);
    const windowOpenSpy = vi.spyOn(window, "open").mockReturnValue({ location: { href: "" }, close: vi.fn() } as unknown as Window);

    renderTab();

    fireEvent.click(await screen.findByRole("button", { name: "Resumo do aluno" }));

    await waitFor(() => {
      expect(bodyCompositionService.openPdf).toHaveBeenCalledWith("member-1", "eval-1", "summary", expect.anything());
    });

    windowOpenSpy.mockRestore();
  });
});
