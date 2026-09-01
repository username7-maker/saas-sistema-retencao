import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../services/api";
import { assessmentService, type AnthropometryAssessmentInput } from "../services/assessmentService";
import { bodyCompositionService } from "../services/bodyCompositionService";
import type { BodyCompositionEvaluation, BodyCompositionEvaluationCreate, CalculationOrigin } from "../types";
import {
  CALCULATION_ORIGIN_LABELS,
  calculationOriginLabel,
  stripReadOnlyCalculationOrigins,
} from "../utils/calculationOrigins";

vi.mock("../services/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

const expectedLabels: Record<CalculationOrigin, string> = {
  reported: "Medido pelo aparelho",
  schofield_hw_1985: "TMB por Schofield",
  mifflin_st_jeor_1990: "TMB por Mifflin",
  lee_2000: "Estimado por Lee",
  poortmans_2005: "Estimado por Poortmans",
  legacy_unknown: "Origem histórica não identificada",
  unavailable: "Indisponível",
};

describe("calculation origins", () => {
  beforeEach(() => vi.clearAllMocks());

  it("maps every backend origin to the required PT-BR label", () => {
    expect(CALCULATION_ORIGIN_LABELS).toEqual(expectedLabels);
    for (const [origin, label] of Object.entries(expectedLabels)) {
      expect(calculationOriginLabel(origin)).toBe(label);
    }
  });

  it("removes read-only origins without mutating the original payload", () => {
    const payload = {
      evaluation_date: "2026-08-31",
      basal_metabolic_rate_origin: "reported",
      muscle_mass_origin: "reported",
    };

    expect(stripReadOnlyCalculationOrigins(payload)).toEqual({ evaluation_date: "2026-08-31" });
    expect(payload).toHaveProperty("basal_metabolic_rate_origin", "reported");
  });

  it("never sends spoofed origins in bioimpedance or anthropometry payloads", async () => {
    vi.mocked(api.post).mockResolvedValue({ data: {} as BodyCompositionEvaluation });
    const bodyPayload = {
      evaluation_date: "2026-08-31",
      basal_metabolic_rate_origin: "reported",
      muscle_mass_origin: "reported",
    } as BodyCompositionEvaluationCreate & Record<string, unknown>;
    const anthropometryPayload = {
      measurement_protocol: "slaughter_1988_boys_black_white_6_17",
      calculate_muscle_mass: false,
      measurements: {},
      basal_metabolic_rate_origin: "reported",
      muscle_mass_origin: "reported",
    } as AnthropometryAssessmentInput & Record<string, unknown>;

    await bodyCompositionService.create("member-1", bodyPayload);
    await assessmentService.previewAnthropometry("member-1", anthropometryPayload);

    expect(api.post).toHaveBeenNthCalledWith(
      1,
      "/api/v1/members/member-1/body-composition",
      { evaluation_date: "2026-08-31" },
      { params: { sync_actuar: true } },
    );
    expect(api.post).toHaveBeenNthCalledWith(
      2,
      "/api/v1/assessments/members/member-1/anthropometry/preview",
      {
        measurement_protocol: "slaughter_1988_boys_black_white_6_17",
        calculate_muscle_mass: false,
        measurements: {},
      },
    );
  });
});
