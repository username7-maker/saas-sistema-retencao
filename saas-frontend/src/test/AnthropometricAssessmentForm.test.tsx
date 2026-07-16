import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AssessmentRegistrationComposer } from "../components/assessments/AssessmentRegistrationComposer";
import { assessmentService } from "../services/assessmentService";

vi.mock("../services/assessmentService", async () => {
  const actual = await vi.importActual<typeof import("../services/assessmentService")>("../services/assessmentService");
  return {
    ...actual,
    assessmentService: {
      ...actual.assessmentService,
      anthropometryProtocols: vi.fn(),
      previewAnthropometry: vi.fn(),
      createAnthropometry: vi.fn(),
      openAnthropometryPdf: vi.fn(),
    },
  };
});

function renderComposer(onOpenBioimpedance = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    onOpenBioimpedance,
    ...render(
      <QueryClientProvider client={queryClient}>
        <AssessmentRegistrationComposer
          memberId="member-1"
          member={{
            id: "member-1",
            full_name: "Aluno Teste",
            birthdate: "2004-07-16",
            sex_for_clinical_calculation: "male",
            height_cm: 177,
          }}
          onOpenBioimpedance={onOpenBioimpedance}
        />
      </QueryClientProvider>,
    ),
  };
}

describe("AssessmentRegistrationComposer anthropometry mode", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(assessmentService.anthropometryProtocols).mockResolvedValue([
      {
        key: "petroski_1995_male_18_66",
        label: "Petroski (1995), Homens, 18-66 anos",
        sex: "male",
        age_min: 18,
        age_max: 66,
        required_fields: [
          "skinfold_subscapular_mm",
          "skinfold_triceps_mm",
          "skinfold_suprailiac_mm",
          "skinfold_calf_mm",
        ],
        supported: true,
        notes: "Densidade corporal Petroski masculino 4 dobras; convertido por Siri.",
      },
    ]);
    vi.mocked(assessmentService.previewAnthropometry).mockResolvedValue({
      assessment_method: "manual_anthropometry",
      record_origin: "cordex",
      protocol: { key: "petroski_1995_male_18_66", label: "Petroski (1995), Homens, 18-66 anos" },
      formula_version: "anthropometry-v1:petroski_1995_male_18_66",
      calculation_hash: "a".repeat(64),
      results: {
        bmi: 23.49,
        body_fat_pct: 12.49,
        fat_mass_kg: 9.19,
        lean_mass_kg: 64.41,
        waist_hip_ratio: 0.83,
        basal_metabolic_rate: 1737.25,
        muscle_mass_kg: null,
      },
      indicator_origins: {
        body_fat_pct: "anthropometry_calculated",
        muscle_mass_kg: "unavailable",
      },
      snapshot: {},
    });
    vi.mocked(assessmentService.createAnthropometry).mockResolvedValue({
      id: "assessment-1",
      gym_id: "gym-1",
      member_id: "member-1",
      evaluator_id: "user-1",
      assessment_number: 1,
      assessment_date: "2026-07-16T10:00:00Z",
      next_assessment_due: "2026-10-14",
      height_cm: 177,
      weight_kg: 73.6,
      bmi: 23.49,
      body_fat_pct: 12.49,
      lean_mass_kg: 64.41,
      waist_cm: 80,
      hip_cm: 96,
      chest_cm: null,
      arm_cm: null,
      thigh_cm: null,
      resting_hr: null,
      blood_pressure_systolic: null,
      blood_pressure_diastolic: null,
      vo2_estimated: null,
      strength_score: null,
      flexibility_score: null,
      cardio_score: null,
      observations: null,
      ai_analysis: null,
      ai_recommendations: null,
      ai_risk_flags: null,
      extra_data: {},
      assessment_method: "manual_anthropometry",
      record_origin: "cordex",
      created_at: "2026-07-16T10:00:00Z",
      updated_at: "2026-07-16T10:00:00Z",
    });
  });

  it("starts with two modes and opens the legacy bioimpedance tab by callback", () => {
    const { onOpenBioimpedance } = renderComposer();

    fireEvent.click(screen.getByRole("button", { name: /com bioimpedancia/i }));

    expect(onOpenBioimpedance).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: /sem bioimpedancia/i })).toBeInTheDocument();
  });

  it("shows only protocol fields, previews on backend and preserves unavailable muscle mass", async () => {
    renderComposer();

    fireEvent.click(screen.getByRole("button", { name: /sem bioimpedancia/i }));

    expect(await screen.findByLabelText(/protocolo/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/sexo usado na formula/i)).toHaveValue("male");
    expect(screen.getByLabelText(/altura/i)).toHaveValue(177);
    expect(screen.getByLabelText(/peso/i)).toBeInTheDocument();
    expect(await screen.findByLabelText(/dobra tricipital - tentativa 1/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/dobra peitoral/i)).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/peso/i), { target: { value: "73.6" } });
    fireEvent.change(screen.getByLabelText(/ombros/i), { target: { value: "112" } });
    fireEvent.change(screen.getByLabelText(/braco direito relaxado/i), { target: { value: "32" } });
    fireEvent.change(screen.getByLabelText(/dobra tricipital - tentativa 1/i), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText(/dobra tricipital - tentativa 2/i), { target: { value: "9" } });
    fireEvent.click(screen.getByRole("button", { name: /calcular previa/i }));

    expect(await screen.findByText("12.49%")).toBeInTheDocument();
    expect(screen.getByText(/massa muscular: indisponivel nesta modalidade/i)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /confirmar avaliacao/i }));

    await waitFor(() => {
      expect(assessmentService.createAnthropometry).toHaveBeenCalledWith(
        "member-1",
        expect.objectContaining({
          measurement_protocol: "petroski_1995_male_18_66",
          measurements: expect.objectContaining({
            shoulders_cm: expect.objectContaining({ attempts: [112, 112], unit: "cm", side: "right" }),
            right_arm_relaxed_cm: expect.objectContaining({ attempts: [32, 32], unit: "cm", side: "right" }),
          }),
        }),
        expect.any(String),
      );
    });
    await waitFor(() => {
      expect(assessmentService.openAnthropometryPdf).toHaveBeenCalled();
    });
    expect(vi.mocked(assessmentService.openAnthropometryPdf).mock.calls[0]?.slice(0, 2)).toEqual(["member-1", "assessment-1"]);
  });
});
