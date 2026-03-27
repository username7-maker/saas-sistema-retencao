import { parseTezewaReceiptV1 } from "./bodyCompositionOcrProfiles/tezewaReceiptV1";

export type BodyCompositionDeviceProfile = "tezewa_receipt_v1";
export type BodyCompositionOcrWarningSeverity = "warning" | "critical";
export type BodyCompositionOcrEngine = "local" | "ai_assisted" | "ai_fallback" | "hybrid";

export interface BodyCompositionRangeValue {
  min: number | null;
  max: number | null;
}

export interface BodyCompositionOcrWarning {
  field: string | null;
  message: string;
  severity: BodyCompositionOcrWarningSeverity;
}

export interface BodyCompositionOcrValues {
  evaluation_date?: string;
  weight_kg?: number;
  body_fat_kg?: number;
  body_fat_percent?: number;
  waist_hip_ratio?: number;
  fat_free_mass_kg?: number;
  inorganic_salt_kg?: number;
  muscle_mass_kg?: number;
  protein_kg?: number;
  body_water_kg?: number;
  lean_mass_kg?: number;
  body_water_percent?: number;
  visceral_fat_level?: number;
  bmi?: number;
  basal_metabolic_rate_kcal?: number;
  skeletal_muscle_kg?: number;
  target_weight_kg?: number;
  weight_control_kg?: number;
  muscle_control_kg?: number;
  fat_control_kg?: number;
  total_energy_kcal?: number;
  physical_age?: number;
  health_score?: number;
}

export interface BodyCompositionOcrResult {
  device_profile: BodyCompositionDeviceProfile;
  device_model?: string;
  values: BodyCompositionOcrValues;
  ranges: Record<string, BodyCompositionRangeValue>;
  warnings: BodyCompositionOcrWarning[];
  confidence: number;
  raw_text: string;
  needs_review: boolean;
  engine?: BodyCompositionOcrEngine;
  fallback_used?: boolean;
}

type Parser = (rawText: string) => BodyCompositionOcrResult;
type OcrPageSegmentationMode = import("tesseract.js").PSM;
type OcrVariant = { name: string; image: File | HTMLCanvasElement; psm: OcrPageSegmentationMode };

const PARSERS: Record<BodyCompositionDeviceProfile, Parser> = {
  tezewa_receipt_v1: parseTezewaReceiptV1,
};

const OCR_FIELDS: Array<keyof BodyCompositionOcrValues> = [
  "evaluation_date",
  "weight_kg",
  "body_fat_kg",
  "body_fat_percent",
  "waist_hip_ratio",
  "fat_free_mass_kg",
  "inorganic_salt_kg",
  "muscle_mass_kg",
  "protein_kg",
  "body_water_kg",
  "lean_mass_kg",
  "body_water_percent",
  "visceral_fat_level",
  "bmi",
  "basal_metabolic_rate_kcal",
  "skeletal_muscle_kg",
  "target_weight_kg",
  "weight_control_kg",
  "muscle_control_kg",
  "fat_control_kg",
  "total_energy_kcal",
  "physical_age",
  "health_score",
];

const KEY_FIELDS: Array<keyof BodyCompositionOcrValues> = [
  "weight_kg",
  "body_fat_kg",
  "body_fat_percent",
  "waist_hip_ratio",
];

const NUMERIC_BOUNDS: Partial<Record<keyof BodyCompositionOcrValues, { min: number; max: number }>> = {
  weight_kg: { min: 30, max: 300 },
  body_fat_kg: { min: 1, max: 80 },
  body_fat_percent: { min: 2, max: 75 },
  waist_hip_ratio: { min: 0.5, max: 1.5 },
  fat_free_mass_kg: { min: 20, max: 200 },
  inorganic_salt_kg: { min: 1, max: 10 },
  muscle_mass_kg: { min: 10, max: 100 },
  protein_kg: { min: 1, max: 40 },
  body_water_kg: { min: 10, max: 100 },
  visceral_fat_level: { min: 1, max: 30 },
  bmi: { min: 10, max: 80 },
  basal_metabolic_rate_kcal: { min: 500, max: 4000 },
  skeletal_muscle_kg: { min: 5, max: 100 },
  target_weight_kg: { min: 30, max: 300 },
  weight_control_kg: { min: -100, max: 100 },
  muscle_control_kg: { min: -100, max: 100 },
  fat_control_kg: { min: -100, max: 100 },
  total_energy_kcal: { min: 500, max: 7000 },
  physical_age: { min: 1, max: 120 },
  health_score: { min: 1, max: 100 },
};

export const BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE: BodyCompositionDeviceProfile = "tezewa_receipt_v1";

export function extractBodyCompositionFromText(
  rawText: string,
  deviceProfile: BodyCompositionDeviceProfile = BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE,
): BodyCompositionOcrResult {
  const parser = PARSERS[deviceProfile];
  return ensureOcrResultMetadata(parser(rawText), "local", false);
}

export async function readBodyCompositionFromImage(
  file: File,
  deviceProfile: BodyCompositionDeviceProfile = BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE,
): Promise<BodyCompositionOcrResult> {
  const { createWorker } = await import("tesseract.js");
  const worker = await createWorker("por+eng");

  try {
    await worker.setParameters({
      preserve_interword_spaces: "1",
      user_defined_dpi: "300",
    });

    const variants = await buildOcrVariants(file);
    const parsedResults: BodyCompositionOcrResult[] = [];

    for (const variant of variants) {
      await worker.setParameters({
        tessedit_pageseg_mode: variant.psm,
      });
      const recognition = await worker.recognize(variant.image);
      const parsed = extractBodyCompositionFromText(recognition.data.text ?? "", deviceProfile);
      parsedResults.push(parsed);
    }

    return mergeBodyCompositionOcrResults(parsedResults);
  } finally {
    await worker.terminate();
  }
}

export function pickBestBodyCompositionOcrResult(results: BodyCompositionOcrResult[]): BodyCompositionOcrResult {
  if (results.length === 0) {
    throw new Error("Nenhum resultado OCR foi gerado");
  }

  return [...results].sort(compareCanonicalOcrResults)[0];
}

export function mergeBodyCompositionOcrResults(results: BodyCompositionOcrResult[]): BodyCompositionOcrResult {
  if (results.length === 0) {
    throw new Error("Nenhum resultado OCR foi gerado");
  }

  const canonical = pickBestBodyCompositionOcrResult(results);
  const values: BodyCompositionOcrValues = {};
  const ranges: Record<string, BodyCompositionRangeValue> = {};
  const warnings: BodyCompositionOcrWarning[] = [];

  for (const field of OCR_FIELDS) {
    const bestResult = pickBestFieldResult(results, field);
    if (!bestResult) continue;

    (values as Record<string, string | number | undefined>)[String(field)] = bestResult.values[field];
    const range = bestResult.ranges[String(field)];
    if (range) {
      ranges[String(field)] = range;
    }
    warnings.push(...bestResult.warnings.filter((warning) => warning.field === String(field)));
  }

  warnings.push(...canonical.warnings.filter((warning) => warning.field == null || warning.field === "evaluation_date"));

  if (values.body_fat_kg == null) {
    warnings.push({
      field: "body_fat_kg",
      message: "Body fat (kg) nao foi identificado com seguranca.",
      severity: "critical",
    });
  }
  if (values.body_fat_percent == null) {
    warnings.push({
      field: "body_fat_percent",
      message: "Body fat ratio (%) nao foi identificado com seguranca.",
      severity: "critical",
    });
  }
  if (!values.evaluation_date) {
    warnings.push({
      field: "evaluation_date",
      message: "Data da avaliacao nao identificada. Revisar antes de salvar.",
      severity: "warning",
    });
  }

  const uniqueWarnings = dedupeWarnings(warnings);
  const confidence = computeMergedConfidence(values, uniqueWarnings);

    return {
      device_profile: canonical.device_profile,
      device_model: canonical.device_model ?? results.find((result) => result.device_model)?.device_model,
      values,
      ranges,
      warnings: uniqueWarnings,
      confidence,
      raw_text: buildMergedRawText(results),
      needs_review: uniqueWarnings.length > 0 || confidence < 0.85,
      engine: "local",
      fallback_used: false,
    };
}

export function ensureOcrResultMetadata(
  result: BodyCompositionOcrResult,
  engine: BodyCompositionOcrEngine = "local",
  fallbackUsed = engine !== "local",
): BodyCompositionOcrResult {
  return {
    ...result,
    engine: result.engine ?? engine,
    fallback_used: result.fallback_used ?? fallbackUsed,
  };
}

export function getBodyCompositionAiFallbackReasons(result: BodyCompositionOcrResult): string[] {
  const reasons: string[] = [];
  const normalized = ensureOcrResultMetadata(result);
  const inferredWarnings = normalized.warnings.filter((warning) => warning.message.includes("ordem esperada do recibo")).length;

  if (normalized.warnings.some((warning) => warning.severity === "critical")) {
    reasons.push("OCR local veio ambiguo em campos-chave.");
  }
  if (normalized.confidence < 0.85) {
    reasons.push("OCR local ficou abaixo da confianca minima.");
  }
  if (inferredWarnings > 2) {
    reasons.push("OCR local precisou inferir muitos valores pela ordem do recibo.");
  }
  if (KEY_FIELDS.some((field) => normalized.values[field] == null)) {
    reasons.push("OCR local nao identificou todas as medidas principais.");
  }

  return Array.from(new Set(reasons));
}

function scoreBodyCompositionOcrResult(result: BodyCompositionOcrResult): number {
  const values = result.values;
  const requiredKeys: Array<keyof BodyCompositionOcrValues> = [
    "weight_kg",
    "body_fat_kg",
    "body_fat_percent",
    "waist_hip_ratio",
    "fat_free_mass_kg",
    "visceral_fat_level",
    "bmi",
    "skeletal_muscle_kg",
    "target_weight_kg",
    "total_energy_kcal",
    "health_score",
  ];

  let score = result.confidence * 100;
  score += requiredKeys.filter((key) => values[key] !== undefined).length * 10;
  if (values.body_fat_kg !== undefined && values.body_fat_percent !== undefined) score += 35;
  if (result.ranges.body_fat_kg) score += 10;
  if (result.ranges.body_fat_percent) score += 10;
  score += countSectionCoverage(result.raw_text) * 32;
  score += Math.min(result.raw_text.length / 18, 40);
  score -= result.warnings.filter((warning) => warning.severity === "critical").length * 22;
  score -= result.warnings.filter((warning) => warning.severity === "warning").length * 6;
  score -= result.warnings.filter((warning) => warning.message.includes("ordem esperada do recibo")).length * 26;
  score -= result.warnings.filter((warning) => warning.message.includes("linha vizinha")).length * 10;
  if (!values.evaluation_date) score -= 8;
  return score;
}

function compareCanonicalOcrResults(left: BodyCompositionOcrResult, right: BodyCompositionOcrResult): number {
  const leftCoverage = countSectionCoverage(left.raw_text);
  const rightCoverage = countSectionCoverage(right.raw_text);
  if (leftCoverage !== rightCoverage) {
    return rightCoverage - leftCoverage;
  }

  const leftInferredWarnings = left.warnings.filter((warning) => warning.message.includes("ordem esperada do recibo")).length;
  const rightInferredWarnings = right.warnings.filter((warning) => warning.message.includes("ordem esperada do recibo")).length;
  if (leftInferredWarnings !== rightInferredWarnings) {
    return leftInferredWarnings - rightInferredWarnings;
  }

  const leftCriticalWarnings = left.warnings.filter((warning) => warning.severity === "critical").length;
  const rightCriticalWarnings = right.warnings.filter((warning) => warning.severity === "critical").length;
  if (leftCriticalWarnings !== rightCriticalWarnings) {
    return leftCriticalWarnings - rightCriticalWarnings;
  }

  if (left.raw_text.length !== right.raw_text.length) {
    return right.raw_text.length - left.raw_text.length;
  }

  return scoreBodyCompositionOcrResult(right) - scoreBodyCompositionOcrResult(left);
}

async function buildOcrVariants(file: File): Promise<OcrVariant[]> {
  const { PSM } = await import("tesseract.js");
  const image = await loadImageElement(file);
  const fullEnhanced = createHighContrastCanvas(image);
  const receiptCrop = createReceiptFocusedCanvas(image);
  const receiptThreshold = cloneWithThreshold(receiptCrop);
  const receiptTop = createVerticalSliceCanvas(receiptThreshold, 0, 0.46);
  const receiptMiddle = createVerticalSliceCanvas(receiptThreshold, 0.34, 0.74);
  const receiptBottom = createVerticalSliceCanvas(receiptThreshold, 0.62, 1);

  return [
    { name: "original_block", image: file, psm: PSM.SINGLE_BLOCK },
    { name: "receipt_threshold_column", image: receiptThreshold, psm: PSM.SINGLE_COLUMN },
    { name: "receipt_threshold_sparse", image: receiptThreshold, psm: PSM.SPARSE_TEXT },
    { name: "full_enhanced_auto", image: fullEnhanced, psm: PSM.AUTO },
    { name: "receipt_crop_auto", image: receiptCrop, psm: PSM.AUTO },
    { name: "receipt_top_column", image: receiptTop, psm: PSM.SINGLE_COLUMN },
    { name: "receipt_top_sparse", image: receiptTop, psm: PSM.SPARSE_TEXT },
    { name: "receipt_middle_column", image: receiptMiddle, psm: PSM.SINGLE_COLUMN },
    { name: "receipt_middle_sparse", image: receiptMiddle, psm: PSM.SPARSE_TEXT },
    { name: "receipt_bottom_column", image: receiptBottom, psm: PSM.SINGLE_COLUMN },
    { name: "receipt_bottom_sparse", image: receiptBottom, psm: PSM.SPARSE_TEXT },
  ];
}

function loadImageElement(file: File): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    const objectUrl = URL.createObjectURL(file);
    image.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Falha ao carregar imagem para OCR"));
    };
    image.src = objectUrl;
  });
}

function createHighContrastCanvas(image: HTMLImageElement): HTMLCanvasElement {
  const scale = image.width < 1400 ? 2 : 1.5;
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(image.width * scale);
  canvas.height = Math.round(image.height * scale);

  const context = canvas.getContext("2d");
  if (!context) return canvas;

  context.filter = "grayscale(1) contrast(1.4) brightness(1.08)";
  context.drawImage(image, 0, 0, canvas.width, canvas.height);

  return cloneWithThreshold(canvas);
}

function createReceiptFocusedCanvas(image: HTMLImageElement): HTMLCanvasElement {
  const baseCanvas = document.createElement("canvas");
  baseCanvas.width = image.width;
  baseCanvas.height = image.height;

  const context = baseCanvas.getContext("2d");
  if (!context) return createHighContrastCanvas(image);
  context.drawImage(image, 0, 0, baseCanvas.width, baseCanvas.height);

  const imageData = context.getImageData(0, 0, baseCanvas.width, baseCanvas.height);
  const bounds = detectReceiptBounds(imageData, baseCanvas.width, baseCanvas.height);
  if (!bounds) {
    return createHighContrastCanvas(image);
  }

  const cropCanvas = document.createElement("canvas");
  cropCanvas.width = bounds.width;
  cropCanvas.height = bounds.height;
  const cropContext = cropCanvas.getContext("2d");
  if (!cropContext) return createHighContrastCanvas(image);
  cropContext.filter = "grayscale(1) contrast(1.45) brightness(1.12)";
  cropContext.drawImage(baseCanvas, bounds.x, bounds.y, bounds.width, bounds.height, 0, 0, bounds.width, bounds.height);
  return cropCanvas;
}

function cloneWithThreshold(source: HTMLCanvasElement): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  canvas.width = source.width;
  canvas.height = source.height;

  const context = canvas.getContext("2d");
  if (!context) return canvas;
  context.drawImage(source, 0, 0);

  const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
  const { data } = imageData;

  for (let index = 0; index < data.length; index += 4) {
    const luminance = data[index] * 0.299 + data[index + 1] * 0.587 + data[index + 2] * 0.114;
    const value = luminance > 170 ? 255 : 0;
    data[index] = value;
    data[index + 1] = value;
    data[index + 2] = value;
  }

  context.putImageData(imageData, 0, 0);
  return canvas;
}

function createVerticalSliceCanvas(
  source: HTMLCanvasElement,
  startRatio: number,
  endRatio: number,
): HTMLCanvasElement {
  const canvas = document.createElement("canvas");
  const safeStart = Math.max(0, Math.min(1, startRatio));
  const safeEnd = Math.max(safeStart + 0.05, Math.min(1, endRatio));
  const startY = Math.max(0, Math.floor(source.height * safeStart));
  const endY = Math.min(source.height, Math.ceil(source.height * safeEnd));
  const height = Math.max(60, endY - startY);

  canvas.width = source.width;
  canvas.height = height;

  const context = canvas.getContext("2d");
  if (!context) return canvas;

  context.drawImage(source, 0, startY, source.width, height, 0, 0, source.width, height);
  return canvas;
}

function detectReceiptBounds(
  imageData: ImageData,
  width: number,
  height: number,
): { x: number; y: number; width: number; height: number } | null {
  const { data } = imageData;
  let minX = width;
  let minY = height;
  let maxX = 0;
  let maxY = 0;
  let brightPixels = 0;

  for (let y = 0; y < height; y += 1) {
    for (let x = 0; x < width; x += 1) {
      const index = (y * width + x) * 4;
      const luminance = data[index] * 0.299 + data[index + 1] * 0.587 + data[index + 2] * 0.114;
      if (luminance < 178) continue;

      brightPixels += 1;
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
    }
  }

  if (brightPixels < width * height * 0.03) {
    return null;
  }

  const paddingX = Math.round(width * 0.03);
  const paddingY = Math.round(height * 0.03);
  const croppedWidth = Math.min(width - Math.max(minX - paddingX, 0), maxX - minX + paddingX * 2);
  const croppedHeight = Math.min(height - Math.max(minY - paddingY, 0), maxY - minY + paddingY * 2);

  if (croppedWidth < width * 0.15 || croppedHeight < height * 0.15) {
    return null;
  }

  return {
    x: Math.max(minX - paddingX, 0),
    y: Math.max(minY - paddingY, 0),
    width: croppedWidth,
    height: croppedHeight,
  };
}

function pickBestFieldResult(
  results: BodyCompositionOcrResult[],
  field: keyof BodyCompositionOcrValues,
): BodyCompositionOcrResult | null {
  const candidates = results.filter((result) => result.values[field] !== undefined);
  if (!candidates.length) return null;
  return [...candidates].sort((left, right) => scoreFieldResult(right, field) - scoreFieldResult(left, field))[0];
}

function scoreFieldResult(result: BodyCompositionOcrResult, field: keyof BodyCompositionOcrValues): number {
  const value = result.values[field];
  if (value == null) return Number.NEGATIVE_INFINITY;

  let score = scoreFieldPlausibility(field, value) * 100;
  score += result.confidence * 18;
  score += countSectionCoverage(result.raw_text) * 8;
  if (result.ranges[String(field)]) score += 6;
  if (result.warnings.some((warning) => warning.field === String(field) && warning.severity === "critical")) score -= 40;
  if (result.warnings.some((warning) => warning.field === String(field) && warning.message.includes("ordem esperada do recibo"))) score -= 28;
  if (result.warnings.some((warning) => warning.field === String(field) && warning.message.includes("linha vizinha"))) score -= 10;
  return score;
}

function scoreFieldPlausibility(field: keyof BodyCompositionOcrValues, value: string | number): number {
  if (field === "evaluation_date") {
    return /^\d{4}-\d{2}-\d{2}$/.test(String(value)) ? 1 : 0;
  }
  if (typeof value !== "number") return 0;

  const range = NUMERIC_BOUNDS[field];
  if (!range) return 0.5;
  return value >= range.min && value <= range.max ? 1 : 0;
}

function countSectionCoverage(text: string): number {
  const normalized = text.toLowerCase();
  let count = 0;
  if (normalized.includes("body composition")) count += 1;
  if (normalized.includes("body parameters")) count += 1;
  if (normalized.includes("comprehensive evaluation")) count += 1;
  return count;
}

function dedupeWarnings(warnings: BodyCompositionOcrWarning[]): BodyCompositionOcrWarning[] {
  const seen = new Set<string>();
  return warnings.filter((warning) => {
    const key = `${warning.field ?? "null"}|${warning.severity}|${warning.message}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function computeMergedConfidence(values: BodyCompositionOcrValues, warnings: BodyCompositionOcrWarning[]): number {
  const extractedCount = Object.values(values).filter((value) => value !== undefined).length;
  const criticalWarnings = warnings.filter((warning) => warning.severity === "critical").length;
  const inferredWarnings = warnings.filter((warning) => warning.message.includes("ordem esperada do recibo")).length;
  const rescuedWarnings = warnings.filter((warning) => warning.message.includes("linha vizinha")).length;
  const totalWarnings = warnings.length;

  const baseConfidence = Math.min(0.99, extractedCount / 22);
  const confidence =
    baseConfidence -
    criticalWarnings * 0.08 -
    inferredWarnings * 0.05 -
    rescuedWarnings * 0.025 -
    totalWarnings * 0.01;
  return Math.max(0.2, Number(confidence.toFixed(2)));
}

function buildMergedRawText(results: BodyCompositionOcrResult[]): string {
  const sorted = [...results].sort(compareCanonicalOcrResults);
  const uniqueLines: string[] = [];
  const seen = new Set<string>();

  for (const result of sorted) {
    for (const line of result.raw_text.split("\n").map((value) => value.trim()).filter(Boolean)) {
      const key = line.toLowerCase();
      if (seen.has(key)) continue;
      seen.add(key);
      uniqueLines.push(line);
    }
  }

  return uniqueLines.join("\n");
}
