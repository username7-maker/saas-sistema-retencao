import { describe, expect, it } from "vitest";

import type { BodyCompositionEvaluation } from "../types";
import {
  buildBodyCompositionRangeClassifications,
  formatBodyCompositionGoal,
  resolveCoachSummary,
  resolveMemberSummary,
} from "../components/assessments/bodyCompositionInterpretation";

function makeEvaluation(overrides?: Partial<BodyCompositionEvaluation>): BodyCompositionEvaluation {
  return {
    id: "eval-1",
    gym_id: "gym-1",
    member_id: "member-1",
    evaluation_date: "2026-03-30",
    weight_kg: 84.5,
    body_fat_kg: 19.46,
    body_fat_percent: 23,
    waist_hip_ratio: 0.88,
    fat_free_mass_kg: 65,
    inorganic_salt_kg: 3.2,
    protein_kg: 17.7,
    body_water_kg: 43.3,
    lean_mass_kg: null,
    muscle_mass_kg: 37.2,
    skeletal_muscle_kg: 35.6,
    body_water_percent: null,
    visceral_fat_level: 9.1,
    bmi: 26.7,
    basal_metabolic_rate_kcal: 1880,
    target_weight_kg: 68.3,
    weight_control_kg: -16.1,
    muscle_control_kg: -7.8,
    fat_control_kg: -8.3,
    total_energy_kcal: 3008,
    physical_age: 26,
    health_score: 62,
    source: "ocr_receipt",
    notes: null,
    report_file_url: null,
    raw_ocr_text: null,
    ocr_confidence: 0.53,
    ocr_warnings_json: [],
    needs_review: true,
    reviewed_manually: false,
    device_model: null,
    device_profile: "tezewa_receipt_v1",
    parsed_from_image: true,
    ocr_source_file_ref: null,
    measured_ranges_json: {
      weight_kg: { min: 61.7, max: 75.5 },
      body_fat_percent: { min: 11, max: 21 },
      waist_hip_ratio: { min: 0.77, max: 0.92 },
      inorganic_salt_kg: { min: 2.8, max: 3.8 },
      skeletal_muscle_kg: { min: 21.3, max: 35.7 },
      visceral_fat_level: { min: 1, max: 5 },
    },
    ai_coach_summary: null,
    ai_member_friendly_summary: null,
    ai_risk_flags_json: ["Peso acima da faixa recomendada", "Gordura visceral elevada"],
    ai_training_focus_json: {
      primary_goal: "reducao_de_gordura",
      secondary_goal: "preservacao_de_massa_magra",
      suggested_focuses: [],
      cautions: [],
    },
    ai_generated_at: null,
    actuar_sync_status: "saved",
    actuar_sync_mode: "disabled",
    actuar_external_id: null,
    actuar_last_synced_at: null,
    actuar_last_error: null,
    sync_required_for_training: true,
    sync_last_attempt_at: null,
    sync_last_success_at: null,
    sync_last_error_code: null,
    sync_last_error_message: null,
    actuar_sync_job_id: null,
    training_ready: false,
    created_at: "2026-03-30T12:00:00Z",
    updated_at: "2026-03-30T12:00:00Z",
    assistant: null,
    ...overrides,
  };
}

describe("bodyCompositionInterpretation helpers", () => {
  it("formats goal slugs for display", () => {
    expect(formatBodyCompositionGoal("reducao_de_gordura")).toBe("Reducao de gordura");
  });

  it("falls back to a clean coach summary when stored text looks truncated", () => {
    const evaluation = makeEvaluation({
      ai_coach_summary:
        "O aluno Erick apresenta peso corporal acima da faixa recomendada (84,5 kg versus máximo de 75,5 kg). O índice de massa corporal (IMC) su",
    });

    expect(resolveCoachSummary(evaluation)).toContain("foco inicial em reducao de gordura");
  });

  it("falls back to a clean member summary when stored text looks truncated", () => {
    const evaluation = makeEvaluation({
      ai_member_friendly_summary:
        "Seu exame mostra um bom ponto de partida para a gordura corporal e para o acompanhamento geral do plano sem",
    });

    expect(resolveMemberSummary(evaluation)).toContain("ponto de partida");
  });

  it("softens member summary when stored text is too technical", () => {
    const evaluation = makeEvaluation({
      ai_member_friendly_summary:
        "Seu exame mostra relacao cintura-quadril em 0,88, gordura visceral em 9,1 e indice de massa corporal em 26,7.",
    });

    expect(resolveMemberSummary(evaluation)).toContain("bom ponto de partida");
    expect(resolveMemberSummary(evaluation)).toContain("regiao abdominal");
  });

  it("keeps only the most useful range classifications for the professor", () => {
    const evaluation = makeEvaluation();

    const items = buildBodyCompositionRangeClassifications(evaluation);

    expect(items.some((item) => item.label === "Gordura visceral")).toBe(true);
    expect(items.some((item) => item.label === "Relacao cintura-quadril")).toBe(true);
    expect(items.some((item) => item.label === "inorganic_salt_kg")).toBe(false);
  });
});
