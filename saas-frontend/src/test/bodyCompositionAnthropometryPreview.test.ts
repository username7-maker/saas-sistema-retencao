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

  it("uses supported skinfold protocol as anthropometry preview", () => {
    const result = calculateAnthropometryPreview({
      sex: "male",
      ageYears: 31,
      heightCm: 180,
      weightKg: 82,
      bioimpedancePercent: 28,
      preferredSource: "geneos_composite",
      measurementProtocol: "jackson_pollock_3_male_18_61",
      skinfoldChestMm: 12,
      skinfoldAbdominalMm: 22,
      skinfoldThighMm: 18,
    });

    expect(result.status).toBe("ready");
    expect(result.usedSource).toBe("anthropometry");
    expect(result.method).toBe("skinfold_protocol");
    expect(result.usedPercent).toBeGreaterThan(0);
  });

  it("matches the Actuar Petroski male reference case", () => {
    const result = calculateAnthropometryPreview({
      sex: "male",
      ageYears: 22,
      heightCm: 177,
      weightKg: 73.6,
      bioimpedancePercent: 31.2,
      preferredSource: "geneos_composite",
      measurementProtocol: "petroski_1995_male_18_66",
      skinfoldTricepsMm: 9,
      skinfoldSubscapularMm: 12,
      skinfoldSuprailiacMm: 7,
      skinfoldCalfMm: 10,
    });

    expect(result.status).toBe("ready");
    expect(result.usedSource).toBe("anthropometry");
    expect(result.method).toBe("skinfold_protocol");
    expect(result.usedPercent).toBe(12.49);
    expect(result.fatMassKg).toBe(9.19);
    expect(result.leanMassKg).toBe(64.41);
  });

  it("does not calculate catalog-only protocols", () => {
    const result = calculateAnthropometryPreview({
      sex: "male",
      ageYears: 25,
      heightCm: 180,
      weightKg: 82,
      bioimpedancePercent: 24,
      preferredSource: "geneos_composite",
      measurementProtocol: "mcardle_1992_4_male_18_34",
      skinfoldChestMm: 12,
      skinfoldAbdominalMm: 22,
      skinfoldThighMm: 18,
      skinfoldSuprailiacMm: 14,
    });

    expect(result.usedSource).toBe("bioimpedance");
    expect(result.method).toBe("legacy_bioimpedance");
    expect(result.flags).toContain("anthropometry_protocol_manual_only");
  });
});
