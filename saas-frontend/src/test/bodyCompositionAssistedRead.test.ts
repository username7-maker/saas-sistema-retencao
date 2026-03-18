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
    if (result.confidence < 0.85 || result.values.weight_kg == null || result.values.body_fat_kg == null) {
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
    vi.mocked(readBodyCompositionFromImage).mockResolvedValue(localResult());

    const result = await bodyCompositionService.readWithAssistedFallback("member-1", makeFile());

    expect(api.post).not.toHaveBeenCalled();
    expect(result.assistedAttempted).toBe(false);
    expect(result.assistedUsed).toBe(false);
    expect(result.result.values.weight_kg).toBe(84.5);
    expect(result.result.engine).toBe("local");
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
});
