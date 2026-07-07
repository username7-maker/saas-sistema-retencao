import { describe, expect, it } from "vitest";

import { calculateAnthropometryPreview } from "../components/assessments/bodyCompositionAnthropometryPreview";

describe("calculateAnthropometryPreview", () => {
  it("uses abdomen before waist for male Navy calculation", () => {
    const withAbdomen = calculateAnthropometryPreview({
      sex: "male",
      heightCm: 178,
      weightKg: 84.5,
      neckCm: 39,
      waistCm: 76,
      abdomenCm: 92,
      preferredSource: "anthropometry",
    });
    const waistOnly = calculateAnthropometryPreview({
      sex: "male",
      heightCm: 178,
      weightKg: 84.5,
      neckCm: 39,
      waistCm: 76,
      preferredSource: "anthropometry",
    });

    expect(withAbdomen.navyPercent).not.toEqual(waistOnly.navyPercent);
    expect(withAbdomen.usedSource).toBe("anthropometry");
    expect(withAbdomen.fatMassKg).toBeGreaterThan(0);
  });

  it("does not use abdomen as automatic waist fallback for female Navy calculation", () => {
    const result = calculateAnthropometryPreview({
      sex: "female",
      heightCm: 168,
      weightKg: 64,
      neckCm: 33,
      abdomenCm: 82,
      hipCm: 96,
      preferredSource: "geneos_composite",
    });

    expect(result.navyPercent).toBeNull();
    expect(result.missingFields).toContain("cintura");
    expect(result.flags).toContain("anthropometry_incomplete");
  });

  it("keeps inconsistent GeneOS estimate under review before using anthropometry as official", () => {
    const result = calculateAnthropometryPreview({
      sex: "male",
      heightCm: 178,
      weightKg: 84.5,
      neckCm: 39,
      abdomenCm: 120,
      waistCm: 75,
      bioimpedancePercent: 22,
      preferredSource: "geneos_composite",
    });

    expect(result.confidence).toBeNull();
    expect(result.status).toBe("needs_review");
    expect(result.usedSource).toBe("bioimpedance");
    expect(result.flags).toContain("anthropometry_inconsistent");
  });
});
