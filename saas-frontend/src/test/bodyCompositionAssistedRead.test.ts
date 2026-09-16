import { beforeEach, describe, expect, it, vi } from "vitest";

import { bodyCompositionService } from "../services/bodyCompositionService";
import type { BodyCompositionOcrResult } from "../services/bodyCompositionOcr";
import { api } from "../services/api";
import { readBodyCompositionFromImage } from "../services/bodyCompositionOcr";

vi.mock("../services/api", () => ({
  api: {
    post: vi.fn(),
    get: vi.fn(),
  },
}));

vi.mock("../services/bodyCompositionOcr", () => ({
  BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE: "tezewa_receipt_v1",
  ensureOcrResultMetadata: vi.fn((result, engine = "local", fallbackUsed = engine !== "local") => ({
    ...result,
    engine: result.engine ?? engine,
    fallback_used: result.fallback_used ?? fallbackUsed,
  })),
  getBodyCompositionAiFallbackReasons: vi.fn((result) => {
    if (
      result.confidence < 0.85
      || result.values.weight_kg == null
      || result.values.body_fat_kg == null
      || result.values.fat_free_mass_kg == null
      || result.values.body_water_kg == null
    ) {
      return ["OCR local veio ambiguo em campos-chave."];
    }
    return [];
  }),
  readBodyCompositionFromImage: vi.fn(),
}));

function makeFile() {
  return new File(["fake-image"], "receipt.jpg", { type: "image/jpeg" });
}

function localResult(overrides?: Partial<BodyCompositionOcrResult>): BodyCompositionOcrResult {
  return {
    device_profile: "tezewa_receipt_v1",
    device_model: "Tezewa",
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

describe("bodyCompositionService.readWithAssistedFallback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls parse-image when local OCR is weak", async () => {
    vi.mocked(readBodyCompositionFromImage).mockResolvedValue(
      localResult({
        values: {
          weight_kg: 14.41,
          body_fat_kg: 19.46,
          body_fat_percent: 23.0,
          waist_hip_ratio: 0.88,
        },
        confidence: 0.54,
        needs_review: true,
        warnings: [{ field: "weight_kg", message: "OCR local veio ambiguo em campos-chave.", severity: "critical" }],
      }),
    );
    vi.mocked(api.post).mockResolvedValue({
      data: localResult({
        values: {
          weight_kg: 84.5,
          body_fat_kg: 19.46,
          body_fat_percent: 23.0,
          waist_hip_ratio: 0.88,
        },
        confidence: 0.93,
        engine: "hybrid",
        fallback_used: true,
      }),
    });

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile());

    expect(api.post).toHaveBeenCalledTimes(1);
    expect(result.assistedAttempted).toBe(true);
    expect(result.assistedUsed).toBe(true);
    expect(result.result.values.weight_kg).toBe(84.5);
    expect(result.result.engine).toBe("hybrid");
  });

  it("keeps local OCR only when the local result is already strong", async () => {
    vi.mocked(readBodyCompositionFromImage).mockResolvedValue(
      localResult({
        values: {
          weight_kg: 84.5,
          body_fat_kg: 19.46,
          body_fat_percent: 23.0,
          waist_hip_ratio: 0.88,
          fat_free_mass_kg: 65,
          body_water_kg: 43.3,
        },
      }),
    );

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile());

    expect(api.post).not.toHaveBeenCalled();
    expect(result.assistedAttempted).toBe(false);
    expect(result.assistedUsed).toBe(false);
    expect(result.result.values.weight_kg).toBe(84.5);
    expect(result.result.engine).toBe("local");
  });

  it("calls parse-image when local OCR misses body water and fat-free mass even with strong primary fields", async () => {
    vi.mocked(readBodyCompositionFromImage).mockResolvedValue(localResult());
    vi.mocked(api.post).mockResolvedValue({
      data: localResult({
        values: {
          weight_kg: 84.5,
          body_fat_kg: 19.46,
          body_fat_percent: 23.0,
          waist_hip_ratio: 0.88,
          fat_free_mass_kg: 65,
          body_water_kg: 43.3,
        },
        confidence: 0.94,
        engine: "hybrid",
        fallback_used: true,
      }),
    });

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile());

    expect(api.post).toHaveBeenCalledTimes(1);
    expect(result.assistedAttempted).toBe(true);
    expect(result.result.values.fat_free_mass_kg).toBe(65);
    expect(result.result.values.body_water_kg).toBe(43.3);
  });

  it("falls back to local OCR when assisted read request fails", async () => {
    vi.mocked(readBodyCompositionFromImage).mockResolvedValue(
      localResult({
        values: {
          weight_kg: 14.41,
          body_fat_kg: 19.46,
          body_fat_percent: 23.0,
          waist_hip_ratio: 0.88,
        },
        confidence: 0.52,
        warnings: [{ field: "weight_kg", message: "OCR local veio ambiguo em campos-chave.", severity: "critical" }],
        needs_review: true,
      }),
    );
    vi.mocked(api.post).mockRejectedValue(new Error("Assistive endpoint offline"));

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile());

    expect(result.assistedAttempted).toBe(true);
    expect(result.assistedUsed).toBe(false);
    expect(result.assistedError).toBe("Assistive endpoint offline");
    expect(result.result.values.weight_kg).toBe(14.41);
    expect(result.result.engine).toBe("local");
  });

  it("propagates an assisted provider warning returned with a local fallback", async () => {
    const quotaMessage = "Leitura assistida indisponivel: a cota do provedor de IA foi esgotada.";
    vi.mocked(readBodyCompositionFromImage).mockResolvedValue(
      localResult({ confidence: 0.42, needs_review: true }),
    );
    vi.mocked(api.post).mockResolvedValue({
      data: localResult({
        confidence: 0.2,
        needs_review: true,
        engine: "local",
        warnings: [{ field: null, message: quotaMessage, severity: "critical" }],
      }),
    });

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile());

    expect(result.assistedAttempted).toBe(true);
    expect(result.assistedUsed).toBe(false);
    expect(result.assistedError).toBe(quotaMessage);
  });

  it("calls parse-image immediately for an assisted read without starting local OCR", async () => {
    vi.mocked(api.post).mockResolvedValue({
      data: localResult({
        values: {
          weight_kg: 84.5,
          body_fat_kg: 19.46,
          body_fat_percent: 23.0,
          waist_hip_ratio: 0.88,
        },
        confidence: 0.95,
        engine: "ai_assisted",
        fallback_used: true,
      }),
    });
    const stages: string[] = [];

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile(), {
      forceAssisted: true,
      evaluationDate: "2026-09-03",
      onStage: (stage) => stages.push(stage),
    });

    expect(api.post).toHaveBeenCalledTimes(1);
    expect(readBodyCompositionFromImage).not.toHaveBeenCalled();
    const body = vi.mocked(api.post).mock.calls[0][1] as FormData;
    const requestConfig = vi.mocked(api.post).mock.calls[0][2] as { timeout?: number };
    expect(body.get("evaluation_date")).toBe("2026-09-03");
    expect(body.get("local_ocr_result")).toBeNull();
    expect(requestConfig.timeout).toBe(90_000);
    expect(stages).toEqual(expect.arrayContaining(["uploading", "reading_ai", "validating"]));
    expect(result.localResult).toBeNull();
    expect(result.assistedAttempted).toBe(true);
    expect(result.assistedUsed).toBe(true);
    expect(result.result.engine).toBe("ai_assisted");
    expect(result.result.values.weight_kg).toBe(84.5);
  });

  it("uses local OCR only after assisted reading fails and drops position-inferred values", async () => {
    vi.mocked(api.post)
      .mockRejectedValueOnce(new Error("Assistive endpoint offline"))
      .mockResolvedValueOnce({
        data: localResult({
          values: {
            weight_kg: 14.41,
            body_fat_kg: 19.46,
            body_fat_percent: 23,
          },
          warnings: [{
            field: "weight_kg",
            message: "Peso foi inferido pela ordem esperada do recibo. Revisar manualmente.",
            severity: "warning",
          }],
          engine: "local",
          fallback_used: false,
        }),
      });
    vi.mocked(readBodyCompositionFromImage).mockResolvedValue(localResult({
      values: {
        weight_kg: 14.41,
        body_fat_kg: 19.46,
        body_fat_percent: 23,
      },
      warnings: [{
        field: "weight_kg",
        message: "Peso foi inferido pela ordem esperada do recibo. Revisar manualmente.",
        severity: "warning",
      }],
    }));
    const stages: string[] = [];

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile(), {
      forceAssisted: true,
      onStage: (stage) => stages.push(stage),
    });

    expect(api.post).toHaveBeenCalledTimes(2);
    expect(readBodyCompositionFromImage).toHaveBeenCalledTimes(1);
    expect(result.result.values.weight_kg).toBeUndefined();
    expect(result.result.field_metadata?.weight_kg).toMatchObject({
      origin: "local_ocr",
      state: "unavailable",
    });
    expect(result.assistedError).toBe("Assistive endpoint offline");
    expect(stages).toContain("reading_local");
    const fallbackBody = vi.mocked(api.post).mock.calls[1][1] as FormData;
    const transportedLocal = JSON.parse(String(fallbackBody.get("local_ocr_result")));
    expect(transportedLocal.values.weight_kg).toBeUndefined();
  });

  it("does not run local OCR after an authentication failure", async () => {
    const authenticationError = Object.assign(new Error("Unauthorized"), {
      isAxiosError: true,
      response: { status: 401 },
    });
    vi.mocked(api.post).mockRejectedValue(authenticationError);

    await expect(bodyCompositionService.readWithAssistedFallback("member-1", makeFile(), {
      forceAssisted: true,
      evaluationDate: "2026-09-03",
    })).rejects.toThrow("Unauthorized");

    expect(api.post).toHaveBeenCalledTimes(1);
    expect(readBodyCompositionFromImage).not.toHaveBeenCalled();
  });
});

describe("bodyCompositionService.prepareImage", () => {
  beforeEach(() => vi.clearAllMocks());

  it("returns the corrected image and transient preparation metadata", async () => {
    const corrected = new Blob(["corrected"], { type: "image/jpeg" });
    vi.mocked(api.post).mockResolvedValue({
      data: corrected,
      headers: {
        "x-cordex-scan-metadata": JSON.stringify({
          method: "receipt_perspective+clahe",
          confidence: 0.92,
          corners: [{ x: 0.1, y: 0.02 }, { x: 0.9, y: 0.03 }, { x: 0.88, y: 0.98 }, { x: 0.12, y: 0.97 }],
          quality_codes: [],
          quality_metrics: { sharpness_top: 55, sharpness_middle: 61, sharpness_bottom: 52 },
          source_width: 1200,
          source_height: 2200,
          output_width: 1000,
          output_height: 2100,
        }),
      },
    });

    const result = await bodyCompositionService.prepareImage("member-1", makeFile());

    expect(result.blob).toBe(corrected);
    expect(result.metadata.confidence).toBe(0.92);
    expect(result.metadata.corners).toHaveLength(4);
    expect(api.post).toHaveBeenCalledWith(
      "/api/v1/members/member-1/body-composition/prepare-image",
      expect.any(FormData),
      expect.objectContaining({ responseType: "blob" }),
    );
  });
});
