import type { BodyFatConfidence, BodyFatMethod, BodyFatUsedSource, PreferredBodyFatSource } from "../../types";
import { getBodyCompositionProtocol } from "./bodyCompositionProtocols";

type Sex = "male" | "female" | null | undefined;

export interface AnthropometryPreviewInput {
  sex?: Sex;
  heightCm?: unknown;
  weightKg?: unknown;
  bioimpedancePercent?: unknown;
  manualOverridePercent?: unknown;
  preferredSource?: PreferredBodyFatSource | null;
  ageYears?: unknown;
  measurementProtocol?: string | null;
  neckCm?: unknown;
  waistCm?: unknown;
  abdomenCm?: unknown;
  hipCm?: unknown;
  skinfoldChestMm?: unknown;
  skinfoldMidaxillaryMm?: unknown;
  skinfoldSubscapularMm?: unknown;
  skinfoldTricepsMm?: unknown;
  skinfoldBicepsMm?: unknown;
  skinfoldAbdominalMm?: unknown;
  skinfoldSuprailiacMm?: unknown;
  skinfoldThighMm?: unknown;
  skinfoldCalfMm?: unknown;
  reviewCompleted?: boolean;
}

export interface AnthropometryPreviewResult {
  status: "ready" | "incomplete" | "needs_review" | "using_bioimpedance" | "manual_override";
  usedPercent: number | null;
  usedSource: BodyFatUsedSource | null;
  method: BodyFatMethod | null;
  confidence: BodyFatConfidence | null;
  rangeMin: number | null;
  rangeMax: number | null;
  navyPercent: number | null;
  rfmPercent: number | null;
  fatMassKg: number | null;
  leanMassKg: number | null;
  differenceBetweenSources: number | null;
  missingFields: string[];
  flags: string[];
}

const CM_TO_INCHES = 1 / 2.54;

export function calculateAnthropometryPreview(input: AnthropometryPreviewInput): AnthropometryPreviewResult {
  const sex = input.sex === "male" || input.sex === "female" ? input.sex : null;
  const heightCm = parseNumber(input.heightCm);
  const weightKg = parseNumber(input.weightKg);
  const ageYears = parseNumber(input.ageYears);
  const bioimpedancePercent = parseNumber(input.bioimpedancePercent);
  const manualOverridePercent = parseNumber(input.manualOverridePercent);
  const neckCm = parseNumber(input.neckCm);
  const waistCm = parseNumber(input.waistCm);
  const abdomenCm = parseNumber(input.abdomenCm);
  const hipCm = parseNumber(input.hipCm);
  const preferredSource = input.preferredSource || "geneos_composite";
  const hasAnthropometryInput = hasAnyAnthropometryInput(input);
  const flags: string[] = [];
  const protocolPreview = calculateProtocolPreview(input, { sex, ageYears });
  const missingFields = protocolPreview.protocolSelected
    ? protocolPreview.missingFields
    : resolveMissingFields({ sex, heightCm, neckCm, waistCm, abdomenCm, hipCm, preferredSource });

  const useProtocolOnly = protocolPreview.protocolSelected;
  const navyPercent = useProtocolOnly ? null : calculateNavy({ sex, heightCm, neckCm, waistCm, abdomenCm, hipCm });
  const rfmPercent = useProtocolOnly ? null : calculateRfm({ sex, heightCm, waistCm, abdomenCm });
  const composite = protocolPreview.percent != null
    ? { percent: protocolPreview.percent, method: "skinfold_protocol" as BodyFatMethod, confidence: protocolPreview.confidence }
    : resolveComposite({ navyPercent, rfmPercent });

  flags.push(...protocolPreview.flags);

  if (hasImpossibleMeasurement({ heightCm, weightKg, neckCm, waistCm, abdomenCm, hipCm })) {
    flags.push("impossible_measurement_value");
  }
  if (composite.confidence === "inconsistent") {
    flags.push("anthropometry_inconsistent");
    flags.push("anthropometry_needs_review");
  }
  if (missingFields.length > 0 && preferredSource !== "manual_override" && (hasAnthropometryInput || bioimpedancePercent == null)) {
    flags.push("anthropometry_incomplete");
  }

  let usedPercent: number | null = null;
  let usedSource: BodyFatUsedSource | null = null;
  let method: BodyFatMethod | null = null;
  let confidence: BodyFatConfidence | null = composite.confidence;
  let status: AnthropometryPreviewResult["status"] = "incomplete";

  if (preferredSource === "manual_override" && manualOverridePercent != null) {
    usedPercent = roundPercent(manualOverridePercent);
    usedSource = "manual_override";
    method = "manual_override";
    confidence = "medium";
    status = "manual_override";
  } else if (composite.percent != null) {
    if (composite.confidence === "inconsistent" && !input.reviewCompleted) {
      status = "needs_review";
    } else {
      usedPercent = composite.percent;
      usedSource = "anthropometry";
      method = preferredSource === "geneos_composite" && navyPercent != null && rfmPercent != null ? "geneos_composite" : composite.method;
      status = "ready";
    }
  }

  if (usedPercent == null && bioimpedancePercent != null && (!hasAnthropometryInput || preferredSource === "bioimpedance")) {
    usedPercent = roundPercent(bioimpedancePercent);
    usedSource = "bioimpedance";
    method = "legacy_bioimpedance";
    confidence = null;
    status = "using_bioimpedance";
  }

  const [rangeMin, rangeMax] = estimatedRange(usedSource === "anthropometry" ? usedPercent : null, confidence);
  const fatMassKg = weightKg != null && usedPercent != null ? roundKg(weightKg * usedPercent / 100) : null;
  const leanMassKg = weightKg != null && fatMassKg != null ? roundKg(weightKg - fatMassKg) : null;
  return {
    status,
    usedPercent,
    usedSource,
    method,
    confidence: usedSource === "anthropometry" ? confidence : null,
    rangeMin,
    rangeMax,
    navyPercent,
    rfmPercent,
    fatMassKg,
    leanMassKg,
    differenceBetweenSources: null,
    missingFields,
    flags: Array.from(new Set(flags)),
  };
}

function resolveMissingFields(input: {
  sex: Sex;
  heightCm: number | null;
  neckCm: number | null;
  waistCm: number | null;
  abdomenCm: number | null;
  hipCm: number | null;
  preferredSource: PreferredBodyFatSource;
}): string[] {
  if (input.preferredSource === "bioimpedance" || input.preferredSource === "manual_override") return [];
  const missing: string[] = [];
  if (!input.sex) missing.push("sexo");
  if (input.heightCm == null) missing.push("altura");
  if (input.neckCm == null) missing.push("pescoco");
  if (input.sex === "female") {
    if (input.waistCm == null) missing.push("cintura");
    if (input.hipCm == null) missing.push("quadril");
  } else if (input.sex === "male" && input.abdomenCm == null && input.waistCm == null) {
    missing.push("abdomen ou cintura");
  }
  return missing;
}

function calculateNavy(input: {
  sex: Sex;
  heightCm: number | null;
  neckCm: number | null;
  waistCm: number | null;
  abdomenCm: number | null;
  hipCm: number | null;
}): number | null {
  if (!input.sex || input.heightCm == null || input.neckCm == null || input.heightCm <= 0 || input.neckCm <= 0) return null;
  const heightIn = input.heightCm * CM_TO_INCHES;
  const neckIn = input.neckCm * CM_TO_INCHES;
  if (input.sex === "male") {
    const torsoCm = input.abdomenCm ?? input.waistCm;
    if (torsoCm == null) return null;
    const torsoIn = torsoCm * CM_TO_INCHES;
    if (torsoIn <= neckIn) return null;
    return roundPercent(86.010 * Math.log10(torsoIn - neckIn) - 70.041 * Math.log10(heightIn) + 36.76);
  }
  if (input.waistCm == null || input.hipCm == null) return null;
  const waistIn = input.waistCm * CM_TO_INCHES;
  const hipIn = input.hipCm * CM_TO_INCHES;
  const sumIn = waistIn + hipIn - neckIn;
  if (sumIn <= 0) return null;
  return roundPercent(163.205 * Math.log10(sumIn) - 97.684 * Math.log10(heightIn) - 78.387);
}

function calculateRfm(input: {
  sex: Sex;
  heightCm: number | null;
  waistCm: number | null;
  abdomenCm: number | null;
}): number | null {
  if (!input.sex || input.heightCm == null || input.heightCm <= 0) return null;
  const circumference = input.waistCm ?? (input.sex === "male" ? input.abdomenCm : null);
  if (circumference == null || circumference <= 0) return null;
  const base = input.sex === "male" ? 64 : 76;
  return roundPercent(base - 20 * (input.heightCm / circumference));
}

function resolveComposite(input: {
  navyPercent: number | null;
  rfmPercent: number | null;
}): { percent: number | null; method: BodyFatMethod | null; confidence: BodyFatConfidence | null } {
  if (input.navyPercent != null && input.rfmPercent != null) {
    const diff = Math.abs(input.navyPercent - input.rfmPercent);
    if (diff <= 2) return { percent: input.navyPercent, method: "geneos_composite", confidence: "high" };
    if (diff <= 3) return { percent: input.navyPercent, method: "geneos_composite", confidence: "medium_high" };
    if (diff <= 6) return { percent: input.navyPercent, method: "geneos_composite", confidence: "medium" };
    return { percent: input.navyPercent, method: "geneos_composite", confidence: "inconsistent" };
  }
  if (input.navyPercent != null) return { percent: input.navyPercent, method: "navy_circumference", confidence: "medium" };
  if (input.rfmPercent != null) return { percent: input.rfmPercent, method: "rfm", confidence: "low" };
  return { percent: null, method: null, confidence: null };
}

function calculateProtocolPreview(
  input: AnthropometryPreviewInput,
  context: { sex: Sex; ageYears: number | null },
): {
  protocolSelected: boolean;
  percent: number | null;
  confidence: BodyFatConfidence | null;
  flags: string[];
  missingFields: string[];
} {
  const protocol = getBodyCompositionProtocol(input.measurementProtocol);
  if (!protocol || protocol.key === "manual_bioimpedance") {
    return { protocolSelected: false, percent: null, confidence: null, flags: [], missingFields: [] };
  }

  const flags: string[] = [];
  const missingFields: string[] = [];
  if (!protocol.supported) {
    flags.push("anthropometry_protocol_manual_only");
    return { protocolSelected: true, percent: null, confidence: null, flags, missingFields };
  }
  if (protocol.sex && context.sex && protocol.sex !== context.sex) {
    flags.push("anthropometry_protocol_mismatch");
  } else if (protocol.sex && !context.sex) {
    missingFields.push("sexo");
  }
  const ageRequired = protocolRequiresAge(protocol.key);
  if (context.ageYears == null && ageRequired) {
    missingFields.push("idade");
  } else if (context.ageYears != null && protocol.ageMin != null && protocol.ageMax != null && (context.ageYears < protocol.ageMin || context.ageYears > protocol.ageMax)) {
    flags.push("anthropometry_protocol_age_outside_range");
  }

  for (const field of protocol.requiredFields) {
    const value = readProtocolValue(input, field);
    if (value == null) {
      missingFields.push(field);
    } else if (!isPlausibleProtocolValue(field, value)) {
      flags.push("impossible_measurement_value");
    }
  }

  if (flags.includes("anthropometry_protocol_mismatch") || flags.includes("impossible_measurement_value") || missingFields.length > 0) {
    if (missingFields.length > 0) flags.push("anthropometry_incomplete");
    return { protocolSelected: true, percent: null, confidence: null, flags: Array.from(new Set(flags)), missingFields };
  }

  const percent = calculateSupportedProtocolPercent(protocol.key, input, context.sex, context.ageYears);
  if (percent == null || percent < 2 || percent > 75) {
    flags.push("impossible_measurement_value");
    return { protocolSelected: true, percent: null, confidence: null, flags: Array.from(new Set(flags)), missingFields };
  }
  return {
    protocolSelected: true,
    percent: roundPercent(percent),
    confidence: flags.includes("anthropometry_protocol_age_outside_range") ? "low" : "medium",
    flags: Array.from(new Set(flags)),
    missingFields,
  };
}

function protocolRequiresAge(protocolKey: string): boolean {
  return protocolKey !== "petroski_1995_female_18_51";
}

function calculateSupportedProtocolPercent(
  key: string,
  input: AnthropometryPreviewInput,
  sex: Sex,
  ageYears: number | null,
): number | null {
  if (key.includes("jackson_pollock_3")) return calculateJacksonPollock3(input, sex, ageYears);
  if (key.includes("jackson_pollock_7") || key.includes("pollock_1980_7")) return calculateJacksonPollock7(input, sex, ageYears);
  if (key.includes("durnin_womersley")) return calculateDurninWomersley(input, sex, ageYears);
  if (key === "petroski_1995_male_18_66") return calculatePetroski1995Male4(input, sex, ageYears);
  if (key === "petroski_1995_female_18_51") return calculatePetroski1995Female4(input, sex, ageYears);
  if (key.includes("guedes_1985_3")) return calculateGuedes1985(input, sex);
  if (key === "mcardle_1992_4_male_18_34") return calculateYmca4(input, sex, ageYears);
  if (key === "mcardle_1992_3_female_18_48") return calculateYmca3(input, sex, ageYears);
  if (key === "weltman_1988_female_obese_20_60") return calculateWeltmanFemale(input, sex);
  if (key === "slaughter_1988_boys" || key === "slaughter_1988_girls") return calculateSlaughterSimple(input, sex);
  if (key === "faulkner_1968_male_20_30") return calculateFaulkner1968(input);
  return null;
}

function calculateJacksonPollock3(input: AnthropometryPreviewInput, sex: Sex, ageYears: number | null): number | null {
  if (sex === "male") {
    const total = sumProtocolFields(input, ["skinfold_chest_mm", "skinfold_abdominal_mm", "skinfold_thigh_mm"]);
    if (total == null || ageYears == null) return null;
    return siri(1.10938 - 0.0008267 * total + 0.0000016 * total ** 2 - 0.0002574 * ageYears);
  }
  if (sex === "female") {
    const total = sumProtocolFields(input, ["skinfold_triceps_mm", "skinfold_suprailiac_mm", "skinfold_thigh_mm"]);
    if (total == null || ageYears == null) return null;
    return siri(1.0994921 - 0.0009929 * total + 0.0000023 * total ** 2 - 0.0001392 * ageYears);
  }
  return null;
}

function calculateJacksonPollock7(input: AnthropometryPreviewInput, sex: Sex, ageYears: number | null): number | null {
  const total = sumProtocolFields(input, [
    "skinfold_chest_mm",
    "skinfold_midaxillary_mm",
    "skinfold_subscapular_mm",
    "skinfold_triceps_mm",
    "skinfold_abdominal_mm",
    "skinfold_suprailiac_mm",
    "skinfold_thigh_mm",
  ]);
  if (total == null || ageYears == null) return null;
  if (sex === "male") return siri(1.112 - 0.00043499 * total + 0.00000055 * total ** 2 - 0.00028826 * ageYears);
  if (sex === "female") return siri(1.097 - 0.00046971 * total + 0.00000056 * total ** 2 - 0.00012828 * ageYears);
  return null;
}

function calculateDurninWomersley(input: AnthropometryPreviewInput, sex: Sex, ageYears: number | null): number | null {
  const total = sumProtocolFields(input, ["skinfold_triceps_mm", "skinfold_biceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm"]);
  if (total == null || total <= 0 || ageYears == null || !sex) return null;
  const [constant, multiplier] = durninCoefficients(sex, ageYears);
  return siri(constant - multiplier * Math.log10(total));
}

function calculatePetroski1995Male4(input: AnthropometryPreviewInput, sex: Sex, ageYears: number | null): number | null {
  if (sex !== "male" || ageYears == null) return null;
  const total = sumProtocolFields(input, [
    "skinfold_subscapular_mm",
    "skinfold_triceps_mm",
    "skinfold_suprailiac_mm",
    "skinfold_calf_mm",
  ]);
  if (total == null) return null;
  return siri(1.10726863 - 0.00081201 * total + 0.00000212 * total ** 2 - 0.00041761 * ageYears);
}

function calculatePetroski1995Female4(input: AnthropometryPreviewInput, sex: Sex, _ageYears: number | null): number | null {
  if (sex !== "female") return null;
  const total = sumProtocolFields(input, [
    "skinfold_midaxillary_mm",
    "skinfold_suprailiac_mm",
    "skinfold_thigh_mm",
    "skinfold_calf_mm",
  ]);
  if (total == null || total <= 0) return null;
  return siri(1.1954713 - 0.07513507 * Math.log10(total));
}

function calculateGuedes1985(input: AnthropometryPreviewInput, sex: Sex): number | null {
  if (sex === "male") {
    const total = sumProtocolFields(input, ["skinfold_triceps_mm", "skinfold_abdominal_mm", "skinfold_suprailiac_mm"]);
    if (total == null || total <= 0) return null;
    return siri(1.1714 - 0.0671 * Math.log10(total));
  }
  if (sex === "female") {
    const total = sumProtocolFields(input, ["skinfold_suprailiac_mm", "skinfold_thigh_mm", "skinfold_subscapular_mm"]);
    if (total == null || total <= 0) return null;
    return siri(1.1665 - 0.0706 * Math.log10(total));
  }
  return null;
}

function calculateYmca4(input: AnthropometryPreviewInput, sex: Sex, ageYears: number | null): number | null {
  const total = sumProtocolFields(input, ["skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_triceps_mm", "skinfold_thigh_mm"]);
  if (total == null || ageYears == null) return null;
  if (sex === "male") return 0.29288 * total - 0.0005 * total ** 2 + 0.15845 * ageYears - 5.76377;
  if (sex === "female") return 0.29669 * total - 0.00043 * total ** 2 + 0.02963 * ageYears + 1.4072;
  return null;
}

function calculateYmca3(input: AnthropometryPreviewInput, sex: Sex, ageYears: number | null): number | null {
  const total = sumProtocolFields(input, ["skinfold_abdominal_mm", "skinfold_suprailiac_mm", "skinfold_triceps_mm"]);
  if (total == null || ageYears == null) return null;
  if (sex === "male") return 0.39287 * total - 0.00105 * total ** 2 + 0.15772 * ageYears - 5.18845;
  if (sex === "female") return 0.41563 * total - 0.00112 * total ** 2 + 0.03661 * ageYears + 4.03653;
  return null;
}

function calculateWeltmanFemale(input: AnthropometryPreviewInput, sex: Sex): number | null {
  if (sex !== "female") return null;
  const abdomenCm = readProtocolValue(input, "abdomen_cm");
  const weightKg = readProtocolValue(input, "weight_kg");
  const heightCm = readProtocolValue(input, "height_cm");
  if (abdomenCm == null || weightKg == null || heightCm == null) return null;
  return 0.11077 * abdomenCm - 0.17666 * heightCm + 0.14354 * weightKg + 51.03301;
}

function calculateSlaughterSimple(input: AnthropometryPreviewInput, sex: Sex): number | null {
  const total = sumProtocolFields(input, ["skinfold_triceps_mm", "skinfold_calf_mm"]);
  if (total == null) return null;
  if (sex === "male") return 0.735 * total + 1;
  if (sex === "female") return 0.610 * total + 5.1;
  return null;
}

function calculateFaulkner1968(input: AnthropometryPreviewInput): number | null {
  const total = sumProtocolFields(input, ["skinfold_triceps_mm", "skinfold_subscapular_mm", "skinfold_suprailiac_mm", "skinfold_abdominal_mm"]);
  if (total == null) return null;
  return 5.783 + 0.153 * total;
}

function durninCoefficients(sex: Exclude<Sex, null | undefined>, ageYears: number): [number, number] {
  if (ageYears < 17) return sex === "male" ? [1.1533, 0.0643] : [1.1369, 0.0598];
  if (ageYears <= 19) return sex === "male" ? [1.162, 0.063] : [1.1549, 0.0678];
  if (ageYears <= 29) return sex === "male" ? [1.1631, 0.0632] : [1.1599, 0.0717];
  if (ageYears <= 39) return sex === "male" ? [1.1422, 0.0544] : [1.1423, 0.0632];
  if (ageYears <= 49) return sex === "male" ? [1.162, 0.07] : [1.1333, 0.0612];
  return sex === "male" ? [1.1715, 0.0779] : [1.1339, 0.0645];
}

function sumProtocolFields(input: AnthropometryPreviewInput, fields: string[]): number | null {
  let total = 0;
  for (const field of fields) {
    const value = readProtocolValue(input, field);
    if (value == null) return null;
    total += value;
  }
  return total;
}

function readProtocolValue(input: AnthropometryPreviewInput, field: string): number | null {
  const map: Record<string, unknown> = {
    skinfold_chest_mm: input.skinfoldChestMm,
    skinfold_midaxillary_mm: input.skinfoldMidaxillaryMm,
    skinfold_subscapular_mm: input.skinfoldSubscapularMm,
    skinfold_triceps_mm: input.skinfoldTricepsMm,
    skinfold_biceps_mm: input.skinfoldBicepsMm,
    skinfold_abdominal_mm: input.skinfoldAbdominalMm,
    skinfold_suprailiac_mm: input.skinfoldSuprailiacMm,
    skinfold_thigh_mm: input.skinfoldThighMm,
    skinfold_calf_mm: input.skinfoldCalfMm,
    waist_cm: input.waistCm,
    abdomen_cm: input.abdomenCm,
    height_cm: input.heightCm,
    hip_cm: input.hipCm,
    weight_kg: input.weightKg,
  };
  return parseNumber(map[field]);
}

function isPlausibleProtocolValue(field: string, value: number): boolean {
  const ranges: Record<string, [number, number]> = {
    height_cm: [90, 250],
    weight_kg: [20, 300],
    abdomen_cm: [30, 250],
    waist_cm: [30, 250],
    hip_cm: [35, 260],
  };
  const [min, max] = ranges[field] ?? [2, 120];
  return value >= min && value <= max;
}

function siri(density: number | null): number | null {
  if (density == null || density <= 0) return null;
  return 495 / density - 450;
}

function estimatedRange(value: number | null, confidence: BodyFatConfidence | null): [number | null, number | null] {
  if (value == null || confidence == null || confidence === "inconsistent") return [null, null];
  const margin = {
    high: 1.5,
    medium_high: 2,
    medium: 3,
    low: 4,
  }[confidence];
  return [roundPercent(Math.max(0, value - margin)), roundPercent(Math.min(75, value + margin))];
}

function hasImpossibleMeasurement(values: Record<string, number | null>): boolean {
  const ranges: Record<string, [number, number]> = {
    heightCm: [90, 250],
    weightKg: [20, 250],
    neckCm: [15, 80],
    waistCm: [30, 250],
    abdomenCm: [30, 250],
    hipCm: [35, 260],
  };
  return Object.entries(ranges).some(([key, [min, max]]) => {
    const value = values[key];
    return value != null && (value < min || value > max);
  });
}

function hasAnyAnthropometryInput(input: AnthropometryPreviewInput): boolean {
  return [
    input.neckCm,
    input.waistCm,
    input.abdomenCm,
    input.hipCm,
    input.skinfoldChestMm,
    input.skinfoldMidaxillaryMm,
    input.skinfoldSubscapularMm,
    input.skinfoldTricepsMm,
    input.skinfoldBicepsMm,
    input.skinfoldAbdominalMm,
    input.skinfoldSuprailiacMm,
    input.skinfoldThighMm,
    input.skinfoldCalfMm,
    input.manualOverridePercent,
  ].some((value) => parseNumber(value) != null);
}

function parseNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (typeof value !== "string") return null;
  const normalized = value.trim().replace(/\s+/g, "").replace(",", ".");
  if (!normalized || !/^-?\d+(\.\d+)?$/.test(normalized)) return null;
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : null;
}

function roundPercent(value: number): number {
  return Math.round(value * 100) / 100;
}

function roundKg(value: number): number {
  return Math.round(value * 100) / 100;
}
