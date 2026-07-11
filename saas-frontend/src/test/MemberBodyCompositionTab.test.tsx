import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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
    window.sessionStorage.clear();
    vi.mocked(bodyCompositionService.list).mockResolvedValue([makeEvaluation()]);
    vi.mocked(bodyCompositionService.getActuarSyncStatus).mockResolvedValue(makeSyncStatus());
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

  it("shows the selected protocol requirements as immediate inputs", async () => {
    const evaluation = makeEvaluation();
    evaluation.sex = "male";
    evaluation.age_years = 30;
    evaluation.measurement_protocol = "petroski_1995_male_18_66";
    evaluation.skinfold_subscapular_mm = 14;
    evaluation.skinfold_triceps_mm = 16;
    evaluation.skinfold_suprailiac_mm = 18;
    evaluation.skinfold_calf_mm = 12;
    vi.mocked(bodyCompositionService.list).mockResolvedValue([evaluation]);

    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Editar atual" }));

    expect(await screen.findByText("O que medir neste protocolo")).toBeInTheDocument();
    expect(screen.getByRole("textbox", { name: "Dobra subescapular (mm) para protocolo" })).toHaveValue("14");
    expect(screen.getByRole("textbox", { name: "Dobra tricipital (mm) para protocolo" })).toHaveValue("16");
    expect(screen.getByRole("textbox", { name: "Dobra suprailiaca (mm) para protocolo" })).toHaveValue("18");
    expect(screen.getByRole("textbox", { name: "Dobra panturrilha (mm) para protocolo" })).toHaveValue("12");
  });

  it("locks Petroski women to the required sex and keeps the current age available to the protocol", async () => {
    renderTab();

    const protocolSelect = await screen.findByDisplayValue("Adicionar manualmente (Balanca de Bioimpedancia)");
    fireEvent.change(protocolSelect, { target: { value: "petroski_1995_female_18_51" } });

    await waitFor(() => {
      expect(screen.getByRole("combobox", { name: "Sexo para protocolo" })).toHaveValue("female");
    });
    expect(document.querySelector('select[name="sex"]')).toHaveValue("female");
    expect(screen.getByRole("textbox", { name: "Idade para protocolo" })).toHaveValue("21");
  });

  it("marks height as ready in the protocol checklist when it is filled", async () => {
    const evaluation = makeEvaluation();
    evaluation.measurement_protocol = "petroski_1995_female_18_51";
    evaluation.height_cm = 179;
    evaluation.weight_kg = 84.5;
    evaluation.skinfold_midaxillary_mm = 10;
    evaluation.skinfold_suprailiac_mm = 18;
    evaluation.skinfold_thigh_mm = 20;
    evaluation.skinfold_calf_mm = 12;
    vi.mocked(bodyCompositionService.list).mockResolvedValue([evaluation]);

    renderTab();
    fireEvent.click(await screen.findByRole("button", { name: "Editar atual" }));

    const heightCard = (await screen.findByText("Altura")).closest("div.rounded-xl");
    expect(heightCard).not.toBeNull();
    expect(within(heightCard as HTMLElement).getByText("ok")).toBeInTheDocument();
  });

  it("restores an unfinished body-composition form from the current browser tab", async () => {
    window.sessionStorage.setItem(
      "cordex:body-composition-draft:v1:member-1",
      JSON.stringify({
        saved_at: Date.now(),
        source: "manual",
        reviewed_manually: true,
        values: {
          evaluation_date: "2026-04-14",
          age_years: 31,
          sex: "female",
          weight_kg: 62.5,
          measurement_protocol: "petroski_1995_female_18_51",
        },
      }),
    );

    renderTab();

    expect(await screen.findByRole("textbox", { name: "Idade para protocolo" })).toHaveValue("31");
    expect(screen.getByRole("combobox", { name: "Sexo para protocolo" })).toHaveValue("female");
    expect(screen.getAllByDisplayValue("62.5")).toHaveLength(2);
  });

  it("opens the device camera capture flow next to file upload", async () => {
    const stop = vi.fn();
    const getUserMedia = vi.fn().mockResolvedValue({ getTracks: () => [{ stop }] });
    Object.defineProperty(navigator, "mediaDevices", {
      value: { getUserMedia },
      configurable: true,
    });
    renderTab();

    fireEvent.click(await screen.findByRole("button", { name: "Abrir camera para fotografar a bioimpedancia" }));

    expect(screen.getByRole("dialog", { name: "Fotografar exame" })).toBeInTheDocument();
    await waitFor(() => {
      expect(getUserMedia).toHaveBeenCalledWith({
        audio: false,
        video: { facingMode: { ideal: "environment" } },
      });
    });
    fireEvent.click(screen.getByRole("button", { name: "Fechar camera" }));
    expect(stop).toHaveBeenCalled();
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
});
