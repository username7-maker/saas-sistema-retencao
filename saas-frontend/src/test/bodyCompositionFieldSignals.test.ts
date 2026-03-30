import { describe, expect, it } from "vitest";

import type { BodyCompositionOcrResult } from "../services/bodyCompositionOcr";
import { resolveBodyCompositionFieldSignal } from "../components/assessments/bodyCompositionFieldSignals";

function makeOcrResult(overrides?: Partial<BodyCompositionOcrResult>): BodyCompositionOcrResult {
  return {
    device_profile: "tezewa_receipt_v1",
    values: {
      weight_kg: 84.5,
      body_fat_kg: 19.46,
      body_fat_percent: 23.0,
      waist_hip_ratio: 0.88,
    },
    ranges: {},
    warnings: [],
    confidence: 0.92,
    raw_text: "Weight 84.5",
    needs_review: false,
    engine: "local",
    fallback_used: false,
    ...overrides,
  };
}

describe("resolveBodyCompositionFieldSignal", () => {
  it("returns null for manual entries", () => {
    const signal = resolveBodyCompositionFieldSignal({
      fieldKey: "weight_kg",
      currentSource: "manual",
      currentValue: 84.5,
      ocrResult: null,
      localResult: null,
      storedWarnings: [],
    });

    expect(signal).toBeNull();
  });

  it("marks pure AI-assisted fields as reviewed by AI", () => {
    const signal = resolveBodyCompositionFieldSignal({
      fieldKey: "weight_kg",
      currentSource: "ocr_receipt",
      currentValue: 84.5,
      ocrResult: makeOcrResult({ engine: "ai_assisted", fallback_used: false }),
      localResult: makeOcrResult({ values: {} }),
      storedWarnings: [],
    });

    expect(signal).toMatchObject({ label: "IA revisou", tone: "success" });
  });

  it("marks hybrid fields as reviewed by AI when value changed from local OCR", () => {
    const signal = resolveBodyCompositionFieldSignal({
      fieldKey: "muscle_mass_kg",
      currentSource: "ocr_receipt",
      currentValue: 37.2,
      ocrResult: makeOcrResult({
        engine: "hybrid",
        fallback_used: true,
        values: { muscle_mass_kg: 37.2 },
      }),
      localResult: makeOcrResult({
        values: { muscle_mass_kg: 85.0 },
      }),
      storedWarnings: [],
    });

    expect(signal).toMatchObject({ label: "IA revisou", tone: "success" });
  });

  it("marks uncertain fields when warning indicates inference", () => {
    const signal = resolveBodyCompositionFieldSignal({
      fieldKey: "body_water_kg",
      currentSource: "ocr_receipt",
      currentValue: null,
      ocrResult: makeOcrResult({
        engine: "hybrid",
        fallback_used: true,
        values: {},
      }),
      localResult: makeOcrResult({ values: {} }),
      storedWarnings: [
        {
          field: "body_water_kg",
          message: "Valor inferido pela ordem esperada do recibo. Revisar antes de salvar.",
          severity: "warning",
        },
      ],
    });

    expect(signal).toMatchObject({ label: "Incerto", tone: "warning" });
  });

  it("falls back to local OCR signal when value exists without stronger evidence", () => {
    const signal = resolveBodyCompositionFieldSignal({
      fieldKey: "weight_kg",
      currentSource: "ocr_receipt",
      currentValue: 84.5,
      ocrResult: null,
      localResult: null,
      storedWarnings: [],
    });

    expect(signal).toMatchObject({ label: "OCR local", tone: "neutral" });
  });
});
