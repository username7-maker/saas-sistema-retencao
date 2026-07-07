import type { BodyFatConfidence, BodyFatMethod, BodyFatUsedSource, PreferredBodyFatSource } from "../../types";

type Sex = "male" | "female" | null | undefined;

export interface AnthropometryPreviewInput {
  sex?: Sex;
  heightCm?: unknown;
  weightKg?: unknown;
  bioimpedancePercent?: unknown;
  manualOverridePercent?: unknown;
  preferredSource?: PreferredBodyFatSource | null;
  neckCm?: unknown;
  waistCm?: unknown;
  abdomenCm?: unknown;
  hipCm?: unknown;
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
  const bioimpedancePercent = parseNumber(input.bioimpedancePercent);
  const manualOverridePercent = parseNumber(input.manualOverridePercent);
  const neckCm = parseNumber(input.neckCm);
  const waistCm = parseNumber(input.waistCm);
  const abdomenCm = parseNumber(input.abdomenCm);
  const hipCm = parseNumber(input.hipCm);
  const preferredSource = input.preferredSource || "geneos_composite";
  const flags: string[] = [];
  const missingFields = resolveMissingFields({ sex, heightCm, neckCm, waistCm, abdomenCm, hipCm, preferredSource });

  const navyPercent = calculateNavy({ sex, heightCm, neckCm, waistCm, abdomenCm, hipCm });
  const rfmPercent = calculateRfm({ sex, heightCm, waistCm, abdomenCm });
  const composite = resolveComposite({ navyPercent, rfmPercent });

  if (hasImpossibleMeasurement({ heightCm, weightKg, neckCm, waistCm, abdomenCm, hipCm })) {
    flags.push("impossible_measurement_value");
  }
  if (bioimpedancePercent != null && composite.percent != null && Math.abs(bioimpedancePercent - composite.percent) > 6) {
    flags.push("body_fat_source_divergence");
  }
  if (composite.confidence === "inconsistent") {
    flags.push("anthropometry_inconsistent");
    flags.push("anthropometry_needs_review");
  }
  if (missingFields.length > 0 && preferredSource !== "bioimpedance" && preferredSource !== "manual_override") {
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
  } else if (preferredSource === "bioimpedance" && bioimpedancePercent != null) {
    usedPercent = roundPercent(bioimpedancePercent);
    usedSource = "bioimpedance";
    method = "legacy_bioimpedance";
    confidence = null;
    status = "using_bioimpedance";
  } else if (composite.percent != null) {
    if (composite.confidence === "inconsistent" && !input.reviewCompleted) {
      status = "needs_review";
      if (bioimpedancePercent != null) {
        usedPercent = roundPercent(bioimpedancePercent);
        usedSource = "bioimpedance";
        method = "legacy_bioimpedance";
        confidence = null;
      }
    } else {
      usedPercent = composite.percent;
      usedSource = "anthropometry";
      method = preferredSource === "geneos_composite" && navyPercent != null && rfmPercent != null ? "geneos_composite" : composite.method;
      status = "ready";
    }
  } else if (bioimpedancePercent != null) {
    usedPercent = roundPercent(bioimpedancePercent);
    usedSource = "bioimpedance";
    method = "legacy_bioimpedance";
    confidence = null;
    status = "using_bioimpedance";
  }

  const [rangeMin, rangeMax] = estimatedRange(usedSource === "anthropometry" ? usedPercent : null, confidence);
  const fatMassKg = weightKg != null && usedPercent != null ? roundKg(weightKg * usedPercent / 100) : null;
  const leanMassKg = weightKg != null && fatMassKg != null ? roundKg(weightKg - fatMassKg) : null;
  const differenceBetweenSources = bioimpedancePercent != null && composite.percent != null
    ? roundPercent(Math.abs(bioimpedancePercent - composite.percent))
    : null;

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
    differenceBetweenSources,
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
