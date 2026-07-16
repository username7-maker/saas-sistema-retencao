import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { MemberBodyCompositionTab } from "../components/assessments/MemberBodyCompositionTab";
import { actuarSettingsService } from "../services/actuarSettingsService";
import { assessmentService, type Assessment } from "../services/assessmentService";
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

vi.mock("../services/assessmentService", () => ({
  assessmentService: {
    list: vi.fn(),
    openAnthropometryPdf: vi.fn(),
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
    body_fat_bioimpedance_percent: 26.6,
    body_fat_anthropometric_percent: 24.2,
    body_fat_used_percent: 24.2,
    body_fat_used_source: "anthropometry",
    body_fat_method: "geneos_composite",
    body_fat_confidence: "medium_high",
    body_fat_range_min: 22.2,
    body_fat_range_max: 26.2,
    body_fat_manual_override_percent: null,
    preferred_body_fat_source: "geneos_composite",
    fat_mass_estimated_kg: 15.54,
    lean_mass_estimated_kg: 48.66,
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
    measurement_source: "composite_geneos",
    measurement_protocol: "geneos_composite",
    neck_cm: 33,
    shoulders_cm: 102,
    chest_cm: 90,
    waist_cm: 74,
    abdomen_cm: 78,
    hip_cm: 94,
    right_arm_relaxed_cm: 28,
    left_arm_relaxed_cm: 27.8,
    right_arm_flexed_cm: 31,
    left_arm_flexed_cm: 30.5,
    right_thigh_cm: 54,
    left_thigh_cm: 53.5,
    right_calf_cm: 35,
    left_calf_cm: 34.7,
    anthropometry_notes: "Medidas revisadas.",
    body_fat_manual_review_required: false,
    body_fat_manual_review_completed: true,
    anthropometry_review_completed: true,
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

function makeAnthropometryAssessment(): Assessment {
  return {
    id: "assessment-1",
    gym_id: "gym-1",
    member_id: "member-1",
    evaluator_id: "user-1",
    assessment_number: 2,
    assessment_date: "2026-07-16",
    next_assessment_due: "2026-10-14",
    height_cm: 189,
    weight_kg: 87,
    bmi: 24.36,
    body_fat_pct: 16.33,
    lean_mass_kg: 72.79,
    fat_mass_kg: 14.21,
    waist_hip_ratio: 1.02,
    basal_metabolic_rate: 1901,
    assessment_method: "manual_anthropometry",
    record_origin: "cordex",
    sex_used_for_formula: "male",
    age_used_for_formula: 38,
    height_used_for_formula: 189,
    weight_used_for_formula: 87,
    measurement_protocol: "petroski_1995_male_18_66",
    formula_version: "anthropometry-v1:petroski_1995_male_18_66",
    calculation_hash: "hash-123",
    anthropometry_snapshot_json: {
      protocol: { label: "Petroski (1995), Homens, 18-66 anos" },
      measurements: {
        waist_cm: { consolidated_value: "88.9" },
        hip_cm: { consolidated_value: "87.0" },
        shoulders_cm: { consolidated_value: "112.0" },
        chest_cm: { consolidated_value: "98.0" },
      },
    },
    history_badge: "Antropometria",
    comparison_warning: "Metodos diferentes; comparacao direta limitada",
    waist_cm: 88.9,
    hip_cm: 87,
    chest_cm: 98,
    arm_cm: 34,
    thigh_cm: 56,
    resting_hr: null,
    blood_pressure_systolic: null,
    blood_pressure_diastolic: null,
    vo2_estimated: null,
    strength_score: null,
    flexibility_score: null,
    cardio_score: null,
    observations: "Sem intercorrencias.",
    ai_analysis: null,
    ai_recommendations: null,
    ai_risk_flags: null,
    extra_data: {
      perimetry_evolution: {
        waist_cm: "88.9",
        hip_cm: "87.0",
        shoulders_cm: "112.0",
        chest_cm: "98.0",
      },
    },
    created_at: "2026-07-16T20:00:00Z",
    updated_at: "2026-07-16T20:00:00Z",
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
    vi.mocked(assessmentService.list).mockResolvedValue([]);
    vi.mocked(assessmentService.openAnthropometryPdf).mockResolvedValue(undefined);
    vi.mocked(actuarSettingsService.getSettings).mockResolvedValue(makeSettings());
    Object.defineProperty(navigator, "clipboard", {
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
      configurable: true,
    });
  });

  it("shows the premium report CTA in the member workspace for an existing evaluation", async () => {
    renderTab();

    expect(await screen.findByText("Relatorio premium pronto")).toBeInTheDocument();
    expect(screen.getByText("Agua corporal calculada (%)")).toBeInTheDocument();
    expect(
      screen.getByText("Calculada por agua corporal (kg) / peso (kg) x 100. Este percentual nao vem impresso na folha."),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir relatorio" })).toHaveAttribute(
      "href",
      "/assessments/members/member-1/body-composition/eval-1/report",
    );
    expect(screen.getByRole("button", { name: "Resumo do aluno" })).toBeInTheDocument();
    expect(screen.getByText("Sexo: Feminino")).toBeInTheDocument();
    expect(screen.getByText("Composicao corporal por medidas")).toBeInTheDocument();
    expect(screen.getByText("Protocolo antropometrico")).toBeInTheDocument();
    expect(screen.getByText("Checklist do protocolo")).toBeInTheDocument();
    expect(screen.getByText("Comparativo bilateral")).toBeInTheDocument();
    expect(screen.getByText("Dobras cutaneas")).toBeInTheDocument();
    expect(screen.getByText("Jackson e Pollock (1978), 3 dobras - Homens brancos, 18-61 anos")).toBeInTheDocument();
    expect(screen.getByText("Preencha pares direito/esquerdo para comparar.")).toBeInTheDocument();
    expect(screen.getByText("Previa antes de salvar")).toBeInTheDocument();
    expect(screen.getByText("Revisao manual do percentual concluida")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Editar atual" }));

    await waitFor(() => {
      expect(screen.getByText("Braco contraido")).toBeInTheDocument();
    });
  });

  it("does not render the removed no-photo strategy surface", async () => {
    renderTab();

    await screen.findByText("Interpretacao de apoio");
    expect(screen.queryByText("Leitura estrategica sem foto")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Copiar mensagem" })).not.toBeInTheDocument();
  });

  it("preserves anthropometry when a bioimpedance photo is read into the current evaluation", async () => {
    vi.mocked(bodyCompositionService.readWithAssistedFallback).mockResolvedValue({
      localResult: null,
      result: {
        device_profile: "tezewa_receipt_v1",
        device_model: "Tezewa",
        values: {
          weight_kg: 84.5,
          body_fat_kg: 19.46,
          body_fat_percent: 23,
        },
        ranges: {},
        warnings: [],
        confidence: 0.95,
        raw_text: "Weight 84.5",
        needs_review: false,
        engine: "local",
        fallback_used: false,
      },
      fallbackReasons: [],
      assistedAttempted: false,
      assistedUsed: false,
      assistedError: null,
    });

    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Editar atual" }));

    expect(screen.getByDisplayValue("33")).toBeInTheDocument();
    expect(screen.getByDisplayValue("54")).toBeInTheDocument();

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
    fireEvent.change(fileInput, {
      target: { files: [new File(["fake-image"], "receipt.jpg", { type: "image/jpeg" })] },
    });
    fireEvent.click(screen.getByRole("button", { name: "Ler foto" }));

    await waitFor(() => {
      expect(bodyCompositionService.readWithAssistedFallback).toHaveBeenCalledWith("member-1", expect.any(File), {
        deviceProfile: "tezewa_receipt_v1",
        forceAssisted: false,
      });
    });
    expect(screen.getByDisplayValue("33")).toBeInTheDocument();
    expect(screen.getByDisplayValue("54")).toBeInTheDocument();
    expect(screen.getByDisplayValue("84.5")).toBeInTheDocument();
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

  it("renders manual anthropometry in the same composition history with support interpretation", async () => {
    vi.mocked(assessmentService.list).mockResolvedValue([makeAnthropometryAssessment()]);
    const windowOpenSpy = vi.spyOn(window, "open").mockReturnValue({ location: { href: "" }, close: vi.fn() } as unknown as Window);

    renderTab();

    expect(await screen.findByText("Historico de composicao corporal")).toBeInTheDocument();
    expect(screen.getAllByText("Antropometria")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Petroski (1995), Homens, 18-66 anos").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Massa livre").length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Massa muscular, agua corporal, gordura visceral/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/IA da antropometria/i)).toBeInTheDocument();
    expect(screen.getByText("Perimetria usada para evolucao")).toBeInTheDocument();
    expect(screen.getAllByText(/Cintura: 88.9 cm/).length).toBeGreaterThan(0);

    const reportButtons = screen.getAllByRole("button", { name: "Relatorio" });
    fireEvent.click(reportButtons[0]);

    await waitFor(() => {
      expect(assessmentService.openAnthropometryPdf).toHaveBeenCalledWith("member-1", "assessment-1", expect.anything());
    });

    windowOpenSpy.mockRestore();
  });
});
