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

    expect(result.status).toBe("needs_review");
    expect(result.confidence).toBeNull();
    expect(result.usedSource).toBeNull();
    expect(result.usedPercent).toBeNull();
    expect(result.method).toBeNull();
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

  it("does not let legacy bioimpedance preference override a selected protocol preview", () => {
    const result = calculateAnthropometryPreview({
      sex: "male",
      ageYears: 22,
      heightCm: 177,
      weightKg: 73.6,
      bioimpedancePercent: 31.2,
      preferredSource: "bioimpedance",
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
  });

  it("falls back to bioimpedance when no anthropometry measurements exist", () => {
    const result = calculateAnthropometryPreview({
      sex: "male",
      ageYears: 22,
      heightCm: 177,
      weightKg: 73.6,
      bioimpedancePercent: 31.2,
      preferredSource: "geneos_composite",
    });

    expect(result.status).toBe("using_bioimpedance");
    expect(result.usedSource).toBe("bioimpedance");
    expect(result.method).toBe("legacy_bioimpedance");
    expect(result.usedPercent).toBe(31.2);
    expect(result.flags).not.toContain("anthropometry_incomplete");
  });

  it("calculates expanded public protocols with stable preview values", () => {
    const cases = [
      {
        protocol: "mcardle_1992_4_male_18_34",
        input: {
          sex: "male" as const,
          ageYears: 25,
          weightKg: 82,
          skinfoldAbdominalMm: 22,
          skinfoldSuprailiacMm: 14,
          skinfoldTricepsMm: 12,
          skinfoldThighMm: 18,
        },
        expected: 15.35,
      },
      {
        protocol: "mcardle_1992_3_female_18_48",
        input: {
          sex: "female" as const,
          ageYears: 30,
          weightKg: 64,
          skinfoldAbdominalMm: 18,
          skinfoldTricepsMm: 20,
          skinfoldSuprailiacMm: 16,
        },
        expected: 24.31,
      },
      {
        protocol: "guedes_1985_3_male_18_30",
        input: {
          sex: "male" as const,
          ageYears: 24,
          weightKg: 82,
          skinfoldTricepsMm: 12,
          skinfoldAbdominalMm: 22,
          skinfoldSuprailiacMm: 14,
        },
        expected: 17.6,
      },
      {
        protocol: "guedes_1985_3_female_18_30",
        input: {
          sex: "female" as const,
          ageYears: 24,
          weightKg: 64,
          skinfoldSubscapularMm: 15,
          skinfoldSuprailiacMm: 16,
          skinfoldThighMm: 24,
        },
        expected: 24.31,
      },
      {
        protocol: "petroski_1995_female_18_51",
        input: {
          sex: "female" as const,
          ageYears: 32,
          heightCm: 165,
          weightKg: 65,
          skinfoldMidaxillaryMm: 12,
          skinfoldSuprailiacMm: 16,
          skinfoldThighMm: 24,
          skinfoldCalfMm: 18,
          // Regression guard: this workflow matches Afig's selected
          // Petroski female fields and does not use subscapular/triceps.
          skinfoldSubscapularMm: 90,
          skinfoldTricepsMm: 80,
        },
        expected: 26.29,
      },
      {
        protocol: "weltman_1988_female_obese_20_60",
        input: {
          sex: "female" as const,
          ageYears: 42,
          heightCm: 165,
          weightKg: 80,
          abdomenCm: 98,
        },
        expected: 44.22,
      },
      {
        protocol: "slaughter_1988_boys",
        input: {
          sex: "male" as const,
          ageYears: 12,
          weightKg: 42,
          skinfoldTricepsMm: 10,
          skinfoldCalfMm: 12,
        },
        expected: 17.17,
      },
      {
        protocol: "slaughter_1988_girls",
        input: {
          sex: "female" as const,
          ageYears: 12,
          weightKg: 44,
          skinfoldTricepsMm: 12,
          skinfoldCalfMm: 14,
        },
        expected: 20.96,
      },
      {
        protocol: "faulkner_1968_male_20_30",
        input: {
          sex: "male" as const,
          ageYears: 25,
          weightKg: 73.6,
          skinfoldTricepsMm: 10,
          skinfoldSubscapularMm: 12,
          skinfoldSuprailiacMm: 14,
          skinfoldAbdominalMm: 16,
        },
        expected: 13.74,
      },
    ];

    for (const item of cases) {
      const result = calculateAnthropometryPreview({
        bioimpedancePercent: 30,
        preferredSource: "geneos_composite",
        measurementProtocol: item.protocol,
        ...item.input,
      });

      expect(result.status).toBe("ready");
      expect(result.usedSource).toBe("anthropometry");
      expect(result.method).toBe("skinfold_protocol");
      expect(result.usedPercent).toBe(item.expected);
    }
  });

  it("does not calculate protocols that still require uncaptured business fields", () => {
    const result = calculateAnthropometryPreview({
      sex: "male",
      ageYears: 25,
      heightCm: 180,
      weightKg: 82,
      bioimpedancePercent: 24,
      preferredSource: "geneos_composite",
      measurementProtocol: "weltman_1988_male_obese_20_60",
      waistCm: 98,
    });

    expect(result.usedSource).toBeNull();
    expect(result.usedPercent).toBeNull();
    expect(result.method).toBeNull();
    expect(result.flags).toContain("anthropometry_protocol_manual_only");
  });
});
