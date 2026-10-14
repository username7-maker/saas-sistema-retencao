import { describe, expect, it } from "vitest";

import {
  calculateBodyWaterPercent,
  extractBodyCompositionFromText,
  getBodyCompositionAiFallbackReasons,
  mergeBodyCompositionOcrResults,
  type BodyCompositionOcrResult,
} from "../services/bodyCompositionOcr";

describe("calculateBodyWaterPercent", () => {
  it("calculates the percentage from printed body water and weight values", () => {
    expect(calculateBodyWaterPercent(84.5, 43.3)).toBe(51.2);
  });

  it("does not calculate without both valid measurements", () => {
    expect(calculateBodyWaterPercent(null, 43.3)).toBeNull();
    expect(calculateBodyWaterPercent(84.5, null)).toBeNull();
    expect(calculateBodyWaterPercent(0, 43.3)).toBeNull();
  });
});

const CLEAN_RECEIPT = `
Tezewa
Date 17/03/2026
Body composition
Weight 84.5 61.7-75.5
Body fat 19.46 7.55-14.41
Fat free mass 65.0
Inorganic salt 3.2 3.1-3.8
Muscle mass 37.2 28.8-37.0
Protein 17.7 11.0-13.7
Body water 43.3 41.2-48.0
Body fat ratio 23.0 11.0-21.0
Body parameters
Waist hip ratio 0.88 0.80-0.90
Visceral fat 9.1 1.0-5.0
Basal metabolic rate 1880 1395-1782
Body mass index 26.7 18.5-24.0
Skeletal muscle 35.6 21.3-35.7
Comprehensive evaluation
Target weight 68.3
Weight control -16.1
Muscle control -7.8
Fat control -8.3
Total energy 3008.0
Physical age 26
Health score 62
`;

const DIRTY_RECEIPT = `
Tezewa
Date 17/03/2026
Body composition
Wei
ght 84,5 61,7-75,5
Body
fat 19,467,55-14,41
Body fat
ratio 23,0 11,0-21,0
Body parameters
Waist
hip ratio 0,88 0,80-0,90
Visceral fat 9,1 1,0-5,0
Skeletal muscle 35,6 21,3-35,7
`;

const PHOTO_STYLE_RECEIPT = `
Tezewa
Body composition
Project Value Range
Weight (kg) 84.5 61.7~75.5
Body fat (kg) 19.46 7.55~14.41
ratio (%)
Waist hip 0.88 0.8~0.9
Fat free
(kg) 65.0
Inorganic salt 3.2 3.1~3.8
Muscle mass (kg)37.2 28.8~37.0
Protein (kg) 17.7 11.0~13.7
Body moisture 43.3 41.2~48.0
Body parameters
Project Value Range
(%)
Body fat ratio 23.0 11.0~21.0
Visceral fat 9.1 1.0~5.0
Basal metabolism1880 1395~1782
BMI 26.7 18.5~24.0
Skeletal muscle 35.6 21.3~35.7
Comprehensive evaluation
Project Value
Target weight (kg) 68.3kg
Weight control (kg) -16.1kg
Muscle control (kg) -7.8kg
Fat control (kg) -8.3kg
consumption
Total energy 3008.0
Physical age 26
Health score 62
`;

const POSITIONAL_FALLBACK_RECEIPT = `
Tezewa
Body composition
Project Value Range
84.5 61.7-75.5
19.46 7.55-14.41
0.88 0.80-0.90
65.0
3.2 3.1-3.8
37.2 28.8-37.0
17.7 11.0-13.7
43.3 41.2-48.0
Body parameters
Project Value Range
23.0 11.0-21.0
9.1 1.0-5.0
1880 1395-1782
26.7 18.5-24.0
35.6 21.3-35.7
Comprehensive evaluation
68.3kg
-16.1kg
-7.8kg
-8.3kg
3008.0
26
62
`;

const RANGE_ONLY_RECEIPT = `
Tezewa
Body composition
Project Value Range
Weight (kg) 65.1 47.5~58.1
Muscle mass (kg) 18.0~20.6
Body parameters
Project Value Range
Body fat ratio 32.4 18.0~28.0
Basal metabolism 1053~1346
Skeletal muscle 13.2~24.8
Comprehensive evaluation
Project Value
Target weight (kg) 58.1kg
Weight control (kg) -7.0kg
Muscle control (kg) -2.1kg
Fat control (kg) -4.9kg
Total energy 2185.6
Physical age 44
Health score 72
`;

const SPLIT_SALT_AND_WAIST_HIP_RECEIPT = `
Tezewa
Body composition
Project Value Range
Weight (kg) 65.1 47.5~58.1
Body fat (kg) 21.12 9.5~14.78
Waist hi
0.86
0.75~0.85
Fat free (kg) 44.0
[norganic salt
2.9
2.4~2.9
Muscle mass (kg) 23.4 18.0~20.6
Protein (kg) 10.0 8.4~10.6
Body moisture 35.8 31.7~37.0
Body parameters
Project Value Range
Body fat ratio 32.4 18.0~28.0
Visceral fat 7.0 1.0~5.0
Basal metabolism 1366 1053~1346
BMI 23.1 18.5~24.0
Skeletal muscle 25.7 13.2~24.8
Comprehensive evaluation
Project Value
Target weight (kg) 58.1kg
Weight control (kg) -7.0kg
Muscle control (kg) -2.1kg
Fat control (kg) -4.9kg
Total energy 2185.6
Physical age 44
Health score 72
`;

const USER_REAL_OCR_DUMP = `
/ an
/ dl ny
a
A o Dee
di Lo
/ ail é
O AA i
é í i Lia
% AA fo 7 on
É aa i
Esse canna pe A À é -
Body composition . -
4 Range 7 i wh i
é Project Value = i
: D 84.5 61.1 75.5 ; 0
> ; Weight (kg) 14.41 7
A E. Body fat o 19.46 7.5571 4
E EL 870.9 iy .
CUE sme Waist hip 0.88 0. a À jo
A weight (ka) 5.0 a 1
=. Ee Fat free 65. 5 i
- Ge ko) mic sat 32 3.038 EERE
7 Inorg k)3T.2 28.8.31.0 EE y
: — FARA uscle mass (K13T-2 440-437 i
e aa protein (kg) — 17. SS OR
e GR NS 2748.0 i
Wo is 03 MIE 4
DO Esses :
e Body parameters ; a
E AR EEB o cen vi
Eg Project Value Range 7
Se, (%) 3 2 i
wo Body fat ratio 23.0 11.0721.0 ji j
i] Visceral fat 9.1 1.0°5.0 i al
a, Basal metabolismiBB0 139571782 ih o j
E BML 26.1 18.5724.0 2 ão 7
. Eisistallpscieion 0 21 2150-1 É a
Comprehensive evaluation Í 4 4
Project Value — 7 mm
Target weight (kg) — 68.3ko pe.
Weight control (kg) -16.1kg j oy
Muscle control (kg) -7.8kg pe
‘Fat control (kg) -8.3kg A
! gsm on J wr
Total ener a
hysical FT Edo yp o
alth score 62 j or
4 Vs i i :
il E
Vi A
`;

describe("bodyCompositionOcr", () => {
  it("extracts the main Tezewa receipt values and ranges without confusing fat kg and fat percent", () => {
    const result = extractBodyCompositionFromText(CLEAN_RECEIPT);

    expect(result.device_profile).toBe("tezewa_receipt_v1");
    expect(result.device_model).toBe("Tezewa");
    expect(result.values.evaluation_date).toBe("2026-03-17");
    expect(result.values.weight_kg).toBe(84.5);
    expect(result.values.body_fat_kg).toBe(19.46);
    expect(result.values.body_fat_percent).toBe(23.0);
    expect(result.values.waist_hip_ratio).toBe(0.88);
    expect(result.values.skeletal_muscle_percent).toBe(35.6);
    expect(result.values.skeletal_muscle_kg).toBeUndefined();
    expect(result.ranges.skeletal_muscle_percent).toEqual({ min: 21.3, max: 35.7 });
    expect(result.values.target_weight_kg).toBe(68.3);
    expect(result.values.weight_control_kg).toBe(-16.1);
    expect(result.values.health_score).toBe(62);
    expect(result.ranges.body_fat_kg).toEqual({ min: 7.55, max: 14.41 });
    expect(result.ranges.body_fat_percent).toEqual({ min: 11.0, max: 21.0 });
    expect(result.needs_review).toBe(false);
  });

  it("handles dirty OCR with broken labels and collapsed principal value plus range", () => {
    const result = extractBodyCompositionFromText(DIRTY_RECEIPT);

    expect(result.values.weight_kg).toBe(84.5);
    expect(result.values.body_fat_kg).toBe(19.46);
    expect(result.values.body_fat_percent).toBe(23.0);
    expect(result.values.waist_hip_ratio).toBe(0.88);
    expect(result.ranges.body_fat_kg).toEqual({ min: 7.55, max: 14.41 });
    expect(result.ranges.body_fat_percent).toEqual({ min: 11.0, max: 21.0 });
  });

  it("handles a realistic photo-style OCR dump without swapping body fat kg and body fat ratio", () => {
    const result = extractBodyCompositionFromText(PHOTO_STYLE_RECEIPT);

    expect(result.values.weight_kg).toBe(84.5);
    expect(result.values.body_fat_kg).toBe(19.46);
    expect(result.values.body_fat_percent).toBe(23.0);
    expect(result.values.waist_hip_ratio).toBe(0.88);
    expect(result.values.fat_free_mass_kg).toBe(65.0);
    expect(result.values.lean_mass_kg).toBe(65.0);
    expect(result.values.body_water_kg).toBe(43.3);
    expect(result.values.basal_metabolic_rate_kcal).toBe(1880);
    expect(result.values.health_score).toBe(62);
    expect(result.ranges.body_fat_kg).toEqual({ min: 7.55, max: 14.41 });
    expect(result.ranges.body_fat_percent).toEqual({ min: 11.0, max: 21.0 });
    expect(result.warnings.some((warning) => warning.field === "body_fat_percent" && warning.severity === "critical")).toBe(false);
  });

  it("keeps a surviving printed range out of the principal measurement when OCR loses the value column", () => {
    const result = extractBodyCompositionFromText(RANGE_ONLY_RECEIPT);

    expect(result.values.muscle_mass_kg).toBeUndefined();
    expect(result.values.basal_metabolic_rate_kcal).toBeUndefined();
    expect(result.values.skeletal_muscle_percent).toBeUndefined();
    expect(result.ranges.muscle_mass_kg).toEqual({ min: 18.0, max: 20.6 });
    expect(result.ranges.basal_metabolic_rate_kcal).toEqual({ min: 1053, max: 1346 });
    expect(result.ranges.skeletal_muscle_percent).toEqual({ min: 13.2, max: 24.8 });
    expect(result.needs_review).toBe(true);
  });

  it("reads split waist-hip and inorganic-salt rows with common thermal-printer OCR damage", () => {
    const result = extractBodyCompositionFromText(SPLIT_SALT_AND_WAIST_HIP_RECEIPT);

    expect(result.values.waist_hip_ratio).toBe(0.86);
    expect(result.values.inorganic_salt_kg).toBe(2.9);
  });

  it("leaves unlabeled receipt numbers blank instead of assigning them by position", () => {
    const result = extractBodyCompositionFromText(POSITIONAL_FALLBACK_RECEIPT);

    expect(result.values.weight_kg).toBeUndefined();
    expect(result.values.body_fat_kg).toBeUndefined();
    expect(result.values.body_fat_percent).toBeUndefined();
    expect(result.values.waist_hip_ratio).toBeUndefined();
    expect(result.values.target_weight_kg).toBeUndefined();
    expect(result.needs_review).toBe(true);
  });

  it("refuses to borrow values from neighboring rows in a noisy OCR dump", () => {
    const result = extractBodyCompositionFromText(USER_REAL_OCR_DUMP);

    expect(result.values.weight_kg).toBeUndefined();
    expect(result.needs_review).toBe(true);
    expect(result.warnings.some((warning) => warning.message.includes("linha vizinha"))).toBe(false);
  });

  it("does not copy the next labeled row when the current value is missing", () => {
    const result = extractBodyCompositionFromText(`
      Tezewa
      Body composition
      Inorganic salt
      Muscle mass (kg) 23.4 18.0~20.6
      Protein (kg) 10.0 8.4~10.6
      Body parameters
      Body fat ratio 32.4 18.0~28.0
    `);

    expect(result.values.inorganic_salt_kg).toBeUndefined();
    expect(result.values.muscle_mass_kg).toBe(23.4);
    expect(result.values.protein_kg).toBe(10.0);
  });

  it("marks needs_review when body fat percent is ambiguous or missing", () => {
    const result = extractBodyCompositionFromText(`
      Tezewa
      Body composition
      Weight 84.5 61.7-75.5
      Body fat ratio 23.0
    `);

    expect(result.values.body_fat_kg).toBeUndefined();
    expect(result.values.body_fat_percent).toBe(23.0);
    expect(result.needs_review).toBe(true);
    expect(result.warnings.some((warning) => warning.field === "body_fat_kg")).toBe(true);
  });

  it("rejects impossible values and requires assisted reading for a non-Tezewa layout", () => {
    const result = extractBodyCompositionFromText(`
      InBody
      Body Composition Analysis
      Weight 274335
      Body Fat Mass 17.9
      Muscle-Fat Analysis
    `);

    expect(result.device_model).toBe("InBody");
    expect(result.values.weight_kg).toBeUndefined();
    expect(result.needs_review).toBe(true);
    expect(result.warnings).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ field: "weight_kg", severity: "critical" }),
        expect.objectContaining({ field: null, message: expect.stringContaining("Layout diferente do recibo de bioimpedância") }),
      ]),
    );
  });

  it("merges OCR variants by field and prefers plausible explicit values over truncated high-confidence results", () => {
    const truncatedBottom: BodyCompositionOcrResult = {
      device_profile: "tezewa_receipt_v1",
      device_model: "Tezewa",
      confidence: 0.95,
      needs_review: true,
      raw_text: "Comprehensive evaluation\nTarget weight 68.3\nWeight control -16.1\nHealth score 62",
      values: {
        weight_kg: 14.41,
        body_fat_kg: 19.46,
        body_fat_percent: 23.0,
        target_weight_kg: 68.3,
        weight_control_kg: -16.1,
        health_score: 62,
      },
      ranges: {},
      warnings: [
        { field: "weight_kg", message: "weight kg foi inferido pela ordem esperada do recibo. Revisar manualmente.", severity: "warning" },
      ],
    };

    const fullerTop: BodyCompositionOcrResult = {
      device_profile: "tezewa_receipt_v1",
      device_model: "Tezewa",
      confidence: 0.68,
      needs_review: true,
      raw_text: "Body composition\nWeight 84.5 61.7-75.5\nBody fat 19.46 7.55-14.41\nBody fat ratio 23.0 11.0-21.0",
      values: {
        weight_kg: 84.5,
        body_fat_kg: 19.46,
        body_fat_percent: 23.0,
      },
      ranges: {
        weight_kg: { min: 61.7, max: 75.5 },
        body_fat_kg: { min: 7.55, max: 14.41 },
        body_fat_percent: { min: 11.0, max: 21.0 },
      },
      warnings: [],
    };

    const merged = mergeBodyCompositionOcrResults([truncatedBottom, fullerTop]);

    expect(merged.values.weight_kg).toBe(84.5);
    expect(merged.values.body_fat_kg).toBe(19.46);
    expect(merged.values.body_fat_percent).toBe(23.0);
    expect(merged.raw_text).toContain("Body composition");
  });

  it("escalates to assisted OCR when core composition fields are still missing", () => {
    const result = getBodyCompositionAiFallbackReasons(
      localResult({
        values: {
          weight_kg: 84.5,
          body_fat_kg: 19.46,
          body_fat_percent: 23.0,
          waist_hip_ratio: 0.88,
        },
      }),
    );

    expect(result).toContain("OCR local nao cobriu toda a composicao corporal principal.");
  });

  it("escalates to assisted OCR when only inorganic salt is missing", () => {
    const reasons = getBodyCompositionAiFallbackReasons(localResult({
      values: {
        weight_kg: 65.1,
        body_fat_kg: 21.12,
        body_fat_percent: 32.4,
        waist_hip_ratio: 0.86,
        fat_free_mass_kg: 44,
        body_water_kg: 35.8,
        muscle_mass_kg: 23.4,
      },
    }));

    expect(reasons).toContain("OCR local nao identificou todas as medidas do recibo.");
  });
});

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
