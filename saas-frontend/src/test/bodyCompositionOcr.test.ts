import { describe, expect, it } from "vitest";

import { extractBodyCompositionFromText, mergeBodyCompositionOcrResults, type BodyCompositionOcrResult } from "../services/bodyCompositionOcr";

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
    expect(result.values.skeletal_muscle_kg).toBe(35.6);
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
    expect(result.values.body_water_kg).toBe(43.3);
    expect(result.values.basal_metabolic_rate_kcal).toBe(1880);
    expect(result.values.health_score).toBe(62);
    expect(result.ranges.body_fat_kg).toEqual({ min: 7.55, max: 14.41 });
    expect(result.ranges.body_fat_percent).toEqual({ min: 11.0, max: 21.0 });
    expect(result.warnings.some((warning) => warning.field === "body_fat_percent" && warning.severity === "critical")).toBe(false);
  });

  it("falls back to the expected receipt order when OCR loses most labels but preserves the section blocks", () => {
    const result = extractBodyCompositionFromText(POSITIONAL_FALLBACK_RECEIPT);

    expect(result.values.weight_kg).toBe(84.5);
    expect(result.values.body_fat_kg).toBe(19.46);
    expect(result.values.body_fat_percent).toBe(23.0);
    expect(result.values.waist_hip_ratio).toBe(0.88);
    expect(result.values.fat_free_mass_kg).toBe(65.0);
    expect(result.values.target_weight_kg).toBe(68.3);
    expect(result.values.health_score).toBe(62);
    expect(result.warnings.some((warning) => warning.message.includes("ordem esperada do recibo"))).toBe(true);
  });

  it("rescues plausible values from a noisy real OCR dump instead of accepting impossible measurements like 14kg for weight", () => {
    const result = extractBodyCompositionFromText(USER_REAL_OCR_DUMP);

    expect(result.values.weight_kg).toBe(84.5);
    expect(result.values.body_fat_kg).toBe(19.46);
    expect(result.values.body_fat_percent).toBe(23.0);
    expect(result.values.waist_hip_ratio).toBe(0.88);
    expect(result.values.health_score).toBe(62);
    expect(result.warnings.some((warning) => warning.message.includes("linha vizinha"))).toBe(true);
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
});
