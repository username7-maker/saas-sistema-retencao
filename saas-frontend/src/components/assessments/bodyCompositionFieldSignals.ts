import type {
  BodyCompositionOcrResult,
  BodyCompositionOcrWarning,
} from "../../services/bodyCompositionOcr";
import type { EvaluationSource } from "../../types";

export interface BodyCompositionFieldSignal {
  label: "IA revisou" | "OCR local" | "Incerto";
  tone: "success" | "neutral" | "warning";
  description: string;
}

interface ResolveBodyCompositionFieldSignalInput {
  fieldKey: string;
  currentSource: EvaluationSource;
  currentValue?: string | number | null;
  ocrResult: BodyCompositionOcrResult | null;
  localResult: BodyCompositionOcrResult | null;
  storedWarnings: BodyCompositionOcrWarning[] | null | undefined;
}

const AI_REVIEW_PATTERNS = ["substituido pela leitura assistida da imagem", "confirmado pela leitura assistida"];
const UNCERTAIN_PATTERNS = [
  "ordem esperada do recibo",
  "linha vizinha",
  "nao foi identificado",
  "revisar antes de salvar",
  "ocr ruidoso",
  "ambigu",
];

function hasVisibleValue(value: string | number | null | undefined): boolean {
  if (value == null) return false;
  if (typeof value === "string") return value.trim().length > 0;
  return Number.isFinite(value);
}

function signalValue(value: unknown): string | number | null | undefined {
  if (value == null || typeof value === "string" || typeof value === "number") return value;
  return undefined;
}

function sameNumericValue(left: unknown, right: unknown): boolean {
  if (typeof left !== "number" || typeof right !== "number") return left === right;
  return Math.abs(left - right) < 0.0001;
}

function warningsForField(fieldKey: string, warnings: BodyCompositionOcrWarning[] | null | undefined) {
  return (warnings ?? []).filter((warning) => warning.field === fieldKey);
}

function isAiReviewedWarning(warning: BodyCompositionOcrWarning): boolean {
  const message = warning.message.toLowerCase();
  return AI_REVIEW_PATTERNS.some((pattern) => message.includes(pattern));
}

function isUncertainWarning(warning: BodyCompositionOcrWarning): boolean {
  const message = warning.message.toLowerCase();
  return warning.severity === "critical" || UNCERTAIN_PATTERNS.some((pattern) => message.includes(pattern));
}

export function resolveBodyCompositionFieldSignal({
  fieldKey,
  currentSource,
  currentValue,
  ocrResult,
  localResult,
  storedWarnings,
}: ResolveBodyCompositionFieldSignalInput): BodyCompositionFieldSignal | null {
  if (currentSource !== "ocr_receipt") return null;

  const fieldWarnings = warningsForField(fieldKey, storedWarnings);
  const uncertainWarning = fieldWarnings.find(isUncertainWarning);
  if (uncertainWarning) {
    return {
      label: "Incerto",
      tone: "warning",
      description: uncertainWarning.message,
    };
  }

  const aiReviewedWarning = fieldWarnings.find(isAiReviewedWarning);
  if (aiReviewedWarning) {
    return {
      label: "IA revisou",
      tone: "success",
      description: "A leitura assistida confirmou ou corrigiu este campo antes do salvamento.",
    };
  }

  const finalValue = signalValue((ocrResult?.values as Record<string, unknown> | undefined)?.[fieldKey]);
  const localValue = signalValue((localResult?.values as Record<string, unknown> | undefined)?.[fieldKey]);

  if (ocrResult?.engine === "ai_assisted" && hasVisibleValue(finalValue)) {
    return {
      label: "IA revisou",
      tone: "success",
      description: "Este valor veio diretamente da leitura assistida por IA.",
    };
  }

  if ((ocrResult?.engine === "hybrid" || ocrResult?.engine === "ai_fallback") && hasVisibleValue(finalValue)) {
    if (!hasVisibleValue(localValue) || !sameNumericValue(localValue, finalValue)) {
      return {
        label: "IA revisou",
        tone: "success",
        description: "A IA assistida revisou este campo porque o OCR local estava incompleto ou divergente.",
      };
    }
  }

  if (hasVisibleValue(currentValue) || hasVisibleValue(finalValue) || hasVisibleValue(localValue)) {
    return {
      label: "OCR local",
      tone: "neutral",
      description: "Este valor foi mantido a partir do OCR local e continua elegivel para revisao manual.",
    };
  }

  return null;
}
