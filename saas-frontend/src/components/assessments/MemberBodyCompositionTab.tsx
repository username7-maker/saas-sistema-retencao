import { AxiosError } from "axios";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowUpRight,
  Copy,
  Download,
  FilePlus2,
  ImageUp,
  Link2,
  MessageCircle,
  Pencil,
  RefreshCcw,
  Save,
  ScanText,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { Link } from "react-router-dom";
import { z } from "zod";

import { AIAssistantPanel } from "../common/AIAssistantPanel";
import {
  BODY_COMPOSITION_PROTOCOLS,
  SKINFOLD_FIELD_LABELS,
  getBodyCompositionProtocol,
} from "./bodyCompositionProtocols";
import { actuarSettingsService } from "../../services/actuarSettingsService";
import { bodyCompositionService } from "../../services/bodyCompositionService";
import {
  calculateBodyWaterPercent,
  type BodyCompositionOcrEngine,
  type BodyCompositionOcrResult,
} from "../../services/bodyCompositionOcr";
import type {
  BodyCompositionEvaluation,
  BodyCompositionEvaluationCreate,
  BodyCompositionManualSyncSummary,
  BodyCompositionOcrWarning,
  EvaluationSource,
} from "../../types";
import { useAuth } from "../../hooks/useAuth";
import { PRODUCT_NAME } from "../../config/brand";
import { getPermissionAwareMessage } from "../../utils/httpErrors";
import { canManageActuarSync } from "../../utils/roleAccess";
import { Button } from "../ui2/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui2/Card";
import { FormField } from "../ui2/FormField";
import { Input } from "../ui2/Input";
import { Select } from "../ui2/Select";
import { Skeleton } from "../ui2/Skeleton";
import { Textarea } from "../ui2/Textarea";
import {
  buildUnsupportedFieldsMessage,
  resolveActuarCapability,
  resolveReadCapability,
  statusPillToneForEngine,
  statusPillToneForSync,
  syncModeLabel,
} from "./bodyCompositionCapability";
import { resolveBodyCompositionFieldSignal } from "./bodyCompositionFieldSignals";
import {
  buildBodyCompositionRangeClassifications,
  formatBodyCompositionGoal,
  resolveCoachSummary,
  resolveMemberSummary,
} from "./bodyCompositionInterpretation";
import { calculateAnthropometryPreview } from "./bodyCompositionAnthropometryPreview";
import { invalidateAssessmentQueries } from "./queryUtils";

function normalizeNullableNumberInput(value: unknown): number | null | unknown {
  if (value == null || value === "") return null;
  if (typeof value === "number") return Number.isFinite(value) ? value : value;
  if (typeof value !== "string") return value;

  const cleaned = value
    .trim()
    .replace(/\s+/g, "")
    .replace(/[kK][gG]|[kK][cC][aA][lL]|%/g, "")
    .replace(",", ".");

  if (!cleaned) return null;
  if (!/^-?\d+(\.\d+)?$/.test(cleaned)) return value;
  return Number(cleaned);
}

function normalizeNullableIntegerInput(value: unknown): number | null | unknown {
  const normalized = normalizeNullableNumberInput(value);
  if (normalized == null || typeof normalized !== "number") return normalized;
  return Number.isInteger(normalized) ? normalized : normalized;
}

const nullableNumberField = z.preprocess(normalizeNullableNumberInput, z.number().nullable().optional());
const nullableIntegerField = z.preprocess(normalizeNullableIntegerInput, z.number().int().nonnegative().nullable().optional());
const nullableSexField = z.preprocess(
  (value) => (value == null || value === "" ? null : value),
  z.enum(["male", "female"]).nullable().optional(),
);
const preferredBodyFatSourceField = z.preprocess(
  (value) => (value == null || value === "" ? null : value),
  z.enum(["bioimpedance", "anthropometry", "geneos_composite", "manual_override"]).nullable().optional(),
);

const schema = z.object({
  evaluation_date: z.string().min(1, "Data obrigatoria"),
  age_years: nullableIntegerField,
  sex: nullableSexField,
  height_cm: nullableNumberField,
  weight_kg: nullableNumberField,
  body_fat_kg: nullableNumberField,
  body_fat_percent: nullableNumberField,
  body_fat_manual_override_percent: nullableNumberField,
  preferred_body_fat_source: preferredBodyFatSourceField,
  waist_hip_ratio: nullableNumberField,
  fat_free_mass_kg: nullableNumberField,
  inorganic_salt_kg: nullableNumberField,
  protein_kg: nullableNumberField,
  body_water_kg: nullableNumberField,
  lean_mass_kg: nullableNumberField,
  muscle_mass_kg: nullableNumberField,
  skeletal_muscle_kg: nullableNumberField,
  body_water_percent: nullableNumberField,
  visceral_fat_level: nullableNumberField,
  bmi: nullableNumberField,
  basal_metabolic_rate_kcal: nullableNumberField,
  neck_cm: nullableNumberField,
  shoulders_cm: nullableNumberField,
  chest_cm: nullableNumberField,
  waist_cm: nullableNumberField,
  abdomen_cm: nullableNumberField,
  hip_cm: nullableNumberField,
  right_arm_relaxed_cm: nullableNumberField,
  left_arm_relaxed_cm: nullableNumberField,
  right_arm_flexed_cm: nullableNumberField,
  left_arm_flexed_cm: nullableNumberField,
  right_thigh_cm: nullableNumberField,
  left_thigh_cm: nullableNumberField,
  right_calf_cm: nullableNumberField,
  left_calf_cm: nullableNumberField,
  skinfold_chest_mm: nullableNumberField,
  skinfold_midaxillary_mm: nullableNumberField,
  skinfold_subscapular_mm: nullableNumberField,
  skinfold_triceps_mm: nullableNumberField,
  skinfold_biceps_mm: nullableNumberField,
  skinfold_abdominal_mm: nullableNumberField,
  skinfold_suprailiac_mm: nullableNumberField,
  skinfold_thigh_mm: nullableNumberField,
  skinfold_calf_mm: nullableNumberField,
  anthropometry_notes: z.string().optional().nullable(),
  body_fat_manual_review_completed: z.boolean().optional(),
  anthropometry_review_completed: z.boolean().optional(),
  measurement_protocol: z.string().optional().nullable(),
  target_weight_kg: nullableNumberField,
  weight_control_kg: nullableNumberField,
  muscle_control_kg: nullableNumberField,
  fat_control_kg: nullableNumberField,
  total_energy_kcal: nullableNumberField,
  physical_age: nullableIntegerField,
  health_score: nullableIntegerField,
  notes: z.string().optional().nullable(),
  report_file_url: z.string().optional().nullable(),
  ocr_source_file_ref: z.string().optional().nullable(),
});

type FormData = z.infer<typeof schema>;

type NumericFieldKey =
  | "age_years"
  | "height_cm"
  | "weight_kg"
  | "body_fat_kg"
  | "body_fat_percent"
  | "body_fat_manual_override_percent"
  | "waist_hip_ratio"
  | "fat_free_mass_kg"
  | "inorganic_salt_kg"
  | "protein_kg"
  | "body_water_kg"
  | "lean_mass_kg"
  | "muscle_mass_kg"
  | "skeletal_muscle_kg"
  | "body_water_percent"
  | "visceral_fat_level"
  | "bmi"
  | "basal_metabolic_rate_kcal"
  | "neck_cm"
  | "shoulders_cm"
  | "chest_cm"
  | "waist_cm"
  | "abdomen_cm"
  | "hip_cm"
  | "right_arm_relaxed_cm"
  | "left_arm_relaxed_cm"
  | "right_arm_flexed_cm"
  | "left_arm_flexed_cm"
  | "right_thigh_cm"
  | "left_thigh_cm"
  | "right_calf_cm"
  | "left_calf_cm"
  | "skinfold_chest_mm"
  | "skinfold_midaxillary_mm"
  | "skinfold_subscapular_mm"
  | "skinfold_triceps_mm"
  | "skinfold_biceps_mm"
  | "skinfold_abdominal_mm"
  | "skinfold_suprailiac_mm"
  | "skinfold_thigh_mm"
  | "skinfold_calf_mm"
  | "target_weight_kg"
  | "weight_control_kg"
  | "muscle_control_kg"
  | "fat_control_kg"
  | "total_energy_kcal"
  | "physical_age"
  | "health_score";

interface FieldDef {
  key: NumericFieldKey;
  label: string;
  placeholder: string;
  step: string;
  calculated?: boolean;
  description?: string;
}

interface ProtocolItem {
  label: string;
  ready: boolean;
  description: string;
}

interface BalanceItem {
  label: string;
  right: number;
  left: number;
  delta: number;
}

interface OcrMetadataState {
  raw_ocr_text: string | null;
  ocr_confidence: number | null;
  ocr_warnings_json: BodyCompositionOcrWarning[];
  needs_review: boolean;
  device_model: string | null;
  device_profile: string | null;
  parsed_from_image: boolean;
  measured_ranges_json: BodyCompositionEvaluation["measured_ranges_json"];
  ocr_source_file_ref: string | null;
}

interface OcrReadSessionState {
  localResult: BodyCompositionOcrResult | null;
  fallbackReasons: string[];
  assistedAttempted: boolean;
  assistedError: string | null;
}

interface Props {
  memberId: string;
  memberName?: string;
  memberPhone?: string | null;
}

const EMPTY_OCR_METADATA: OcrMetadataState = {
  raw_ocr_text: null,
  ocr_confidence: null,
  ocr_warnings_json: [],
  needs_review: false,
  device_model: null,
  device_profile: null,
  parsed_from_image: false,
  measured_ranges_json: null,
  ocr_source_file_ref: null,
};

const EMPTY_OCR_READ_SESSION: OcrReadSessionState = {
  localResult: null,
  fallbackReasons: [],
  assistedAttempted: false,
  assistedError: null,
};

const FORM_SECTIONS: Array<{ title: string; description: string; fields: FieldDef[] }> = [
  {
    title: "Dados basicos do exame",
    description: "Contexto do exame capturado na Tezewa ou revisado pelo professor.",
    fields: [
      { key: "age_years", label: "Idade (anos)", placeholder: "29", step: "1" },
      { key: "height_cm", label: "Altura (cm)", placeholder: "178", step: "0.1" },
    ],
  },
  {
    title: "Composicao corporal",
    description: "Medidas principais do exame e leitura corporal central.",
    fields: [
      { key: "weight_kg", label: "Peso (kg)", placeholder: "84.5", step: "0.1" },
      { key: "body_fat_kg", label: "Gordura corporal (kg)", placeholder: "19.46", step: "0.01" },
      { key: "body_fat_percent", label: "Gordura corporal bruta da bioimpedancia (%)", placeholder: "23.0", step: "0.1" },
      { key: "waist_hip_ratio", label: "Relacao cintura-quadril", placeholder: "0.88", step: "0.01" },
      { key: "fat_free_mass_kg", label: "Massa livre de gordura (kg)", placeholder: "65.0", step: "0.1" },
      { key: "lean_mass_kg", label: "Massa magra (legado)", placeholder: "63.0", step: "0.1" },
      { key: "muscle_mass_kg", label: "Massa muscular (kg)", placeholder: "37.2", step: "0.1" },
      { key: "skeletal_muscle_kg", label: "Musculo esqueletico (kg)", placeholder: "35.6", step: "0.1" },
      { key: "body_water_kg", label: "Agua corporal (kg)", placeholder: "43.3", step: "0.1" },
      {
        key: "body_water_percent",
        label: "Agua corporal calculada (%)",
        placeholder: "Calculada automaticamente",
        step: "0.1",
        calculated: true,
        description: "Calculada por agua corporal (kg) / peso (kg) x 100. Este percentual nao vem impresso na folha.",
      },
      { key: "protein_kg", label: "Proteina (kg)", placeholder: "17.7", step: "0.1" },
      { key: "inorganic_salt_kg", label: "Sal inorganico (kg)", placeholder: "3.2", step: "0.1" },
    ],
  },
  {
    title: "Medidas manuais / Antropometria",
    description: "Medidas usadas para estimar gordura corporal. Abdomen deve ser medido preferencialmente na linha do umbigo.",
    fields: [
      { key: "neck_cm", label: "Pescoco (cm)", placeholder: "38.0", step: "0.1" },
      { key: "waist_cm", label: "Cintura (cm)", placeholder: "82.0", step: "0.1" },
      {
        key: "abdomen_cm",
        label: "Abdomen (cm)",
        placeholder: "86.0",
        step: "0.1",
        description: "Preferencialmente medido na linha do umbigo. Em homens, e a fonte primaria do calculo Navy.",
      },
      { key: "hip_cm", label: "Quadril (cm)", placeholder: "96.0", step: "0.1" },
      { key: "body_fat_manual_override_percent", label: "Override manual de gordura (%)", placeholder: "23.8", step: "0.1" },
    ],
  },
  {
    title: "Perimetria para evolucao",
    description: "Medidas usadas para acompanhar evolucao. Elas nao entram diretamente no calculo de gordura corporal.",
    fields: [
      { key: "shoulders_cm", label: "Ombros (cm)", placeholder: "112.0", step: "0.1" },
      { key: "chest_cm", label: "Torax (cm)", placeholder: "98.0", step: "0.1" },
      { key: "right_arm_relaxed_cm", label: "Braco direito relaxado (cm)", placeholder: "32.0", step: "0.1" },
      { key: "left_arm_relaxed_cm", label: "Braco esquerdo relaxado (cm)", placeholder: "31.8", step: "0.1" },
      { key: "right_arm_flexed_cm", label: "Braco direito contraido (cm)", placeholder: "35.0", step: "0.1" },
      { key: "left_arm_flexed_cm", label: "Braco esquerdo contraido (cm)", placeholder: "34.8", step: "0.1" },
      { key: "right_thigh_cm", label: "Coxa direita (cm)", placeholder: "58.0", step: "0.1" },
      { key: "left_thigh_cm", label: "Coxa esquerda (cm)", placeholder: "57.5", step: "0.1" },
      { key: "right_calf_cm", label: "Panturrilha direita (cm)", placeholder: "38.0", step: "0.1" },
      { key: "left_calf_cm", label: "Panturrilha esquerda (cm)", placeholder: "37.8", step: "0.1" },
    ],
  },
  {
    title: "Dobras cutaneas",
    description: "Campos usados apenas por protocolos de dobras. Se o protocolo selecionado nao for calculavel, ficam como registro para revisao.",
    fields: [
      { key: "skinfold_chest_mm", label: "Peitoral (mm)", placeholder: "12", step: "0.1" },
      { key: "skinfold_midaxillary_mm", label: "Axilar media (mm)", placeholder: "10", step: "0.1" },
      { key: "skinfold_subscapular_mm", label: "Subescapular (mm)", placeholder: "14", step: "0.1" },
      { key: "skinfold_triceps_mm", label: "Tricipital (mm)", placeholder: "16", step: "0.1" },
      { key: "skinfold_biceps_mm", label: "Bicipital (mm)", placeholder: "8", step: "0.1" },
      { key: "skinfold_abdominal_mm", label: "Abdominal (mm)", placeholder: "22", step: "0.1" },
      { key: "skinfold_suprailiac_mm", label: "Suprailiaca (mm)", placeholder: "18", step: "0.1" },
      { key: "skinfold_thigh_mm", label: "Coxa (mm)", placeholder: "20", step: "0.1" },
      { key: "skinfold_calf_mm", label: "Panturrilha (mm)", placeholder: "12", step: "0.1" },
    ],
  },
  {
    title: "Parametros e metabolismo",
    description: "Indicadores metabolicos e de composicao complementar.",
    fields: [
      { key: "visceral_fat_level", label: "Gordura visceral", placeholder: "9.1", step: "0.1" },
      { key: "bmi", label: "IMC", placeholder: "26.7", step: "0.1" },
      { key: "basal_metabolic_rate_kcal", label: "TMB (kcal)", placeholder: "1880", step: "1" },
      { key: "total_energy_kcal", label: "Energia total (kcal)", placeholder: "3008", step: "1" },
      { key: "physical_age", label: "Idade fisica", placeholder: "26", step: "1" },
      { key: "health_score", label: "Health score", placeholder: "62", step: "1" },
    ],
  },
  {
    title: "Controles sugeridos pelo exame",
    description: "Alvos e ajustes sugeridos pela folha do aparelho.",
    fields: [
      { key: "target_weight_kg", label: "Peso alvo (kg)", placeholder: "68.3", step: "0.1" },
      { key: "weight_control_kg", label: "Controle de peso (kg)", placeholder: "-16.1", step: "0.1" },
      { key: "muscle_control_kg", label: "Controle de musculo (kg)", placeholder: "-7.8", step: "0.1" },
      { key: "fat_control_kg", label: "Controle de gordura (kg)", placeholder: "-8.3", step: "0.1" },
    ],
  },
];

const SAVE_VALIDATION_FIELDS: NumericFieldKey[] = [
  "weight_kg",
  "body_fat_kg",
  "body_fat_percent",
  "body_fat_manual_override_percent",
  "neck_cm",
  "waist_cm",
  "abdomen_cm",
  "hip_cm",
  "shoulders_cm",
  "chest_cm",
  "right_arm_relaxed_cm",
  "left_arm_relaxed_cm",
  "right_arm_flexed_cm",
  "left_arm_flexed_cm",
  "right_thigh_cm",
  "left_thigh_cm",
  "right_calf_cm",
  "left_calf_cm",
  "skinfold_chest_mm",
  "skinfold_midaxillary_mm",
  "skinfold_subscapular_mm",
  "skinfold_triceps_mm",
  "skinfold_biceps_mm",
  "skinfold_abdominal_mm",
  "skinfold_suprailiac_mm",
  "skinfold_thigh_mm",
  "skinfold_calf_mm",
  "waist_hip_ratio",
  "fat_free_mass_kg",
  "inorganic_salt_kg",
  "protein_kg",
  "body_water_kg",
  "lean_mass_kg",
  "muscle_mass_kg",
  "skeletal_muscle_kg",
  "body_water_percent",
  "visceral_fat_level",
  "bmi",
  "basal_metabolic_rate_kcal",
  "target_weight_kg",
  "weight_control_kg",
  "muscle_control_kg",
  "fat_control_kg",
  "total_energy_kcal",
];

const HISTORY_METRICS: Array<{ label: string; field: keyof BodyCompositionEvaluation; unit?: string }> = [
  { label: "Peso", field: "weight_kg", unit: " kg" },
  { label: "Gordura kg", field: "body_fat_kg", unit: " kg" },
  { label: "Gordura estimada %", field: "body_fat_used_percent", unit: "%" },
  { label: "Musc. esqueletico", field: "skeletal_muscle_kg", unit: " kg" },
  { label: "IMC", field: "bmi" },
  { label: "Health score", field: "health_score" },
];

const SUPPORTED_OCR_IMAGE_TYPES = new Set(["image/jpeg", "image/png", "image/webp"]);
const SUPPORTED_OCR_IMAGE_ACCEPT = ".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp";

function isSupportedOcrImageFile(file: File): boolean {
  const normalizedType = (file.type || "").trim().toLowerCase();
  if (normalizedType) {
    return SUPPORTED_OCR_IMAGE_TYPES.has(normalizedType);
  }

  const normalizedName = file.name.trim().toLowerCase();
  return normalizedName.endsWith(".jpg")
    || normalizedName.endsWith(".jpeg")
    || normalizedName.endsWith(".png")
    || normalizedName.endsWith(".webp");
}

function buildDefaultValues(evaluation?: BodyCompositionEvaluation | null): FormData {
  const calculatedBodyWaterPercent = calculateBodyWaterPercent(
    evaluation?.weight_kg,
    evaluation?.body_water_kg,
  );
  return {
    evaluation_date: evaluation?.evaluation_date ?? new Date().toISOString().split("T")[0],
    age_years: evaluation?.age_years ?? null,
    sex: evaluation?.sex ?? null,
    height_cm: evaluation?.height_cm ?? null,
    weight_kg: evaluation?.weight_kg ?? null,
    body_fat_kg: evaluation?.body_fat_kg ?? null,
    body_fat_percent: evaluation?.body_fat_percent ?? null,
    body_fat_manual_override_percent: evaluation?.body_fat_manual_override_percent ?? null,
    preferred_body_fat_source: evaluation?.preferred_body_fat_source ?? "geneos_composite",
    waist_hip_ratio: evaluation?.waist_hip_ratio ?? null,
    fat_free_mass_kg: evaluation?.fat_free_mass_kg ?? null,
    inorganic_salt_kg: evaluation?.inorganic_salt_kg ?? null,
    protein_kg: evaluation?.protein_kg ?? null,
    body_water_kg: evaluation?.body_water_kg ?? null,
    lean_mass_kg: evaluation?.lean_mass_kg ?? null,
    muscle_mass_kg: evaluation?.muscle_mass_kg ?? null,
    skeletal_muscle_kg: evaluation?.skeletal_muscle_kg ?? null,
    body_water_percent: calculatedBodyWaterPercent ?? evaluation?.body_water_percent ?? null,
    visceral_fat_level: evaluation?.visceral_fat_level ?? null,
    bmi: evaluation?.bmi ?? null,
    basal_metabolic_rate_kcal: evaluation?.basal_metabolic_rate_kcal ?? null,
    neck_cm: evaluation?.neck_cm ?? null,
    shoulders_cm: evaluation?.shoulders_cm ?? null,
    chest_cm: evaluation?.chest_cm ?? null,
    waist_cm: evaluation?.waist_cm ?? null,
    abdomen_cm: evaluation?.abdomen_cm ?? null,
    hip_cm: evaluation?.hip_cm ?? null,
    right_arm_relaxed_cm: evaluation?.right_arm_relaxed_cm ?? null,
    left_arm_relaxed_cm: evaluation?.left_arm_relaxed_cm ?? null,
    right_arm_flexed_cm: evaluation?.right_arm_flexed_cm ?? null,
    left_arm_flexed_cm: evaluation?.left_arm_flexed_cm ?? null,
    right_thigh_cm: evaluation?.right_thigh_cm ?? null,
    left_thigh_cm: evaluation?.left_thigh_cm ?? null,
    right_calf_cm: evaluation?.right_calf_cm ?? null,
    left_calf_cm: evaluation?.left_calf_cm ?? null,
    skinfold_chest_mm: evaluation?.skinfold_chest_mm ?? null,
    skinfold_midaxillary_mm: evaluation?.skinfold_midaxillary_mm ?? null,
    skinfold_subscapular_mm: evaluation?.skinfold_subscapular_mm ?? null,
    skinfold_triceps_mm: evaluation?.skinfold_triceps_mm ?? null,
    skinfold_biceps_mm: evaluation?.skinfold_biceps_mm ?? null,
    skinfold_abdominal_mm: evaluation?.skinfold_abdominal_mm ?? null,
    skinfold_suprailiac_mm: evaluation?.skinfold_suprailiac_mm ?? null,
    skinfold_thigh_mm: evaluation?.skinfold_thigh_mm ?? null,
    skinfold_calf_mm: evaluation?.skinfold_calf_mm ?? null,
    anthropometry_notes: evaluation?.anthropometry_notes ?? "",
    body_fat_manual_review_completed: evaluation?.body_fat_manual_review_completed ?? false,
    anthropometry_review_completed: evaluation?.anthropometry_review_completed ?? false,
    measurement_protocol: evaluation?.measurement_protocol ?? "manual_bioimpedance",
    target_weight_kg: evaluation?.target_weight_kg ?? null,
    weight_control_kg: evaluation?.weight_control_kg ?? null,
    muscle_control_kg: evaluation?.muscle_control_kg ?? null,
    fat_control_kg: evaluation?.fat_control_kg ?? null,
    total_energy_kcal: evaluation?.total_energy_kcal ?? null,
    physical_age: evaluation?.physical_age ?? null,
    health_score: evaluation?.health_score ?? null,
    notes: evaluation?.notes ?? "",
    report_file_url: evaluation?.report_file_url ?? "",
    ocr_source_file_ref: evaluation?.ocr_source_file_ref ?? "",
  };
}

function buildOcrMetadata(evaluation?: BodyCompositionEvaluation | null): OcrMetadataState {
  if (!evaluation) return EMPTY_OCR_METADATA;
  return {
    raw_ocr_text: evaluation.raw_ocr_text,
    ocr_confidence: evaluation.ocr_confidence,
    ocr_warnings_json: evaluation.ocr_warnings_json ?? [],
    needs_review: evaluation.needs_review,
    device_model: evaluation.device_model,
    device_profile: evaluation.device_profile,
    parsed_from_image: evaluation.parsed_from_image,
    measured_ranges_json: evaluation.measured_ranges_json,
    ocr_source_file_ref: evaluation.ocr_source_file_ref,
  };
}

function fmt(value: number | null | undefined, unit = ""): string {
  if (value == null) return "-";
  return `${value}${unit}`;
}

function fmtDate(value: string): string {
  try {
    return new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR");
  } catch {
    return value;
  }
}

function sourceLabel(source: EvaluationSource | string | null | undefined): string {
  if (source === "manual") return "Manual";
  if (source === "ocr_receipt") return "OCR da foto";
  if (source === "device_import") return "Importado";
  if (source === "actuar_sync") return "Actuar / sincronizado";
  return "Tezewa (legado)";
}

function bodyFatSourceLabel(source: string | null | undefined): string {
  if (source === "anthropometry") return "Medidas manuais";
  if (source === "manual_override") return "Override manual";
  if (source === "bioimpedance") return "Bioimpedancia bruta";
  return "Fonte pendente";
}

function preferredBodyFatSourceLabel(source: string | null | undefined): string {
  if (source === "geneos_composite") return "Metodo composto GeneOS";
  if (source === "anthropometry") return "Medidas manuais";
  if (source === "manual_override") return "Informar manualmente";
  return "Bioimpedancia";
}

function bodyFatConfidenceLabel(confidence: string | null | undefined): string {
  if (confidence === "high") return "alta";
  if (confidence === "medium_high") return "media-alta";
  if (confidence === "medium") return "media";
  if (confidence === "low") return "baixa";
  if (confidence === "inconsistent") return "inconsistente";
  return "nao calculada";
}

function bodyFatMethodLabel(method: string | null | undefined): string {
  if (method === "geneos_composite") return "Navy + RFM";
  if (method === "navy_circumference") return "Navy por circunferencias";
  if (method === "rfm") return "RFM";
  if (method === "skinfold_protocol") return "Protocolo de dobras";
  if (method === "manual_override") return "Override manual";
  if (method === "legacy_bioimpedance") return "Bioimpedancia bruta";
  return "Metodo pendente";
}

function anthropometryStatusLabel(status: string): string {
  if (status === "ready") return "pronto para relatorio";
  if (status === "needs_review") return "precisa revisao";
  if (status === "manual_override") return "override manual";
  if (status === "using_bioimpedance") return "usando bioimpedancia";
  return "medidas incompletas";
}

function qualityFlagLabel(flag: string): string {
  if (flag === "anthropometry_incomplete") return "medidas incompletas";
  if (flag === "body_fat_source_divergence") return "divergencia entre fontes";
  if (flag === "anthropometry_needs_review") return "revisao obrigatoria";
  if (flag === "anthropometry_inconsistent") return "Navy/RFM inconsistentes";
  if (flag === "impossible_measurement_value") return "medida fora do intervalo esperado";
  if (flag === "abnormal_measurement_variation") return "variacao incomum contra avaliacao anterior";
  if (flag === "anthropometry_protocol_manual_only") return "protocolo exige revisao/manual";
  if (flag === "anthropometry_protocol_mismatch") return "protocolo nao corresponde ao sexo informado";
  if (flag === "anthropometry_protocol_age_outside_range") return "idade fora da faixa do protocolo";
  return flag;
}

function hasNumericValue(value: unknown): boolean {
  return value !== null && value !== undefined && value !== "";
}

function buildAnthropometryProtocolItems(input: {
  sex: FormData["sex"];
  ageYears: unknown;
  heightCm: unknown;
  weightKg: unknown;
  neckCm: unknown;
  waistCm: unknown;
  abdomenCm: unknown;
  hipCm: unknown;
  measurementProtocol?: string | null;
  values?: Partial<Record<NumericFieldKey, unknown>>;
}): ProtocolItem[] {
  const selectedProtocol = getBodyCompositionProtocol(input.measurementProtocol);
  if (selectedProtocol && selectedProtocol.key !== "manual_bioimpedance") {
    const protocolItems: ProtocolItem[] = [
      {
        label: "Protocolo",
        ready: selectedProtocol.supported,
        description: selectedProtocol.supported
          ? "Calculavel automaticamente quando os campos obrigatorios forem preenchidos."
          : "Catalogado para registro. Em V1 exige revisao/manual override para virar fonte oficial.",
      },
      {
        label: "Sexo",
        ready: !selectedProtocol.sex || input.sex === selectedProtocol.sex,
        description: selectedProtocol.sex ? `Esperado: ${selectedProtocol.sex === "male" ? "masculino" : "feminino"}.` : "Protocolo sem restricao de sexo.",
      },
      {
        label: "Idade",
        ready: hasNumericValue(input.ageYears),
        description:
          selectedProtocol.ageMin != null && selectedProtocol.ageMax != null
            ? `Faixa do protocolo: ${selectedProtocol.ageMin}-${selectedProtocol.ageMax} anos. Fora da faixa gera alerta.`
            : "Sem faixa etaria especifica.",
      },
    ];
    for (const field of selectedProtocol.requiredFields) {
      protocolItems.push({
        label: SKINFOLD_FIELD_LABELS[field] ?? field,
        ready: hasNumericValue(input.values?.[field as NumericFieldKey]),
        description: field.startsWith("skinfold_") ? "Dobra cutanea em milimetros." : "Campo operacional requerido por este protocolo.",
      });
    }
    return protocolItems;
  }

  const items: ProtocolItem[] = [
    {
      label: "Sexo e altura",
      ready: Boolean(input.sex) && hasNumericValue(input.heightCm),
      description: "Define a formula correta e converte circunferencias com seguranca.",
    },
    {
      label: "Peso",
      ready: hasNumericValue(input.weightKg),
      description: "Necessario para calcular massa gorda e massa livre estimadas.",
    },
    {
      label: "Pescoco",
      ready: hasNumericValue(input.neckCm),
      description: "Medida obrigatoria do calculo por circunferencias.",
    },
  ];

  if (input.sex === "female") {
    items.push(
      {
        label: "Cintura",
        ready: hasNumericValue(input.waistCm),
        description: "Obrigatoria para mulheres; abdomen nao substitui automaticamente.",
      },
      {
        label: "Quadril",
        ready: hasNumericValue(input.hipCm),
        description: "Obrigatorio no protocolo feminino Navy.",
      },
    );
    return items;
  }

  items.push({
    label: "Abdomen ou cintura",
    ready: hasNumericValue(input.abdomenCm) || hasNumericValue(input.waistCm),
    description: "Para homens, abdomen na linha do umbigo e preferencial; cintura e fallback.",
  });
  return items;
}

function buildPerimetryBalanceItems(input: {
  rightArmFlexed: unknown;
  leftArmFlexed: unknown;
  rightThigh: unknown;
  leftThigh: unknown;
  rightCalf: unknown;
  leftCalf: unknown;
}): BalanceItem[] {
  const pairs = [
    ["Braco contraido", input.rightArmFlexed, input.leftArmFlexed],
    ["Coxa", input.rightThigh, input.leftThigh],
    ["Panturrilha", input.rightCalf, input.leftCalf],
  ] as const;

  return pairs.flatMap(([label, rightRaw, leftRaw]) => {
    const right = normalizePreviewNumber(rightRaw);
    const left = normalizePreviewNumber(leftRaw);
    if (right == null || left == null) return [];
    return [{ label, right, left, delta: Math.round(Math.abs(right - left) * 10) / 10 }];
  });
}

function normalizePreviewNumber(value: unknown): number | null {
  const normalized = normalizeNullableNumberInput(value);
  return typeof normalized === "number" && Number.isFinite(normalized) ? normalized : null;
}

function syncLabel(status: string | null | undefined): string {
  if (status === "synced_to_actuar" || status === "succeeded") return "Sincronizado no Actuar";
  if (status === "saved") return "Salvo localmente";
  if (status === "sync_pending" || status === "pending") return "Pendente";
  if (status === "syncing" || status === "processing" || status === "started") return "Sincronizando";
  if (status === "sync_failed" || status === "failed") return "Falhou";
  if (status === "needs_review") return "Requer revisao";
  if (status === "manual_sync_required") return "Sync manual necessario";
  return "Rascunho";
}

function hasAnyBodyCompositionMetric(data: FormData): boolean {
  return SAVE_VALIDATION_FIELDS.some((field) => data[field] != null);
}

function warningTone(warning?: BodyCompositionOcrWarning): string {
  if (!warning) return "";
  return warning.severity === "critical"
    ? "border-lovable-danger focus:ring-lovable-danger/20"
    : "border-lovable-warning focus:ring-lovable-warning/20";
}

function fieldSignalTextClass(tone: "success" | "warning" | "neutral"): string {
  if (tone === "success") return "text-lovable-success";
  if (tone === "warning") return "text-lovable-warning";
  return "text-lovable-ink-muted";
}

function ocrEngineLabel(engine?: BodyCompositionOcrEngine | null): string | null {
  if (engine === "local") return "Leitura local";
  if (engine === "ai_assisted") return "Leitura assistida por IA";
  if (engine === "ai_fallback") return "Leitura assistida por IA";
  if (engine === "hybrid") return "Leitura hibrida";
  return null;
}

function buildAssistedReadSummary(
  result: BodyCompositionOcrResult | null,
  session: OcrReadSessionState,
): string | null {
  if (!result && !session.assistedAttempted) return null;
  if (result?.engine === "hybrid") {
    return "OCR local veio ambiguo; combinamos o OCR local com a leitura assistida por IA para cobrir os campos do exame com revisao final.";
  }
  if (result?.engine === "ai_assisted") {
    return "A imagem foi lida diretamente pela IA assistida e os campos reconhecidos do exame vieram estruturados para revisao final.";
  }
  if (result?.engine === "ai_fallback") {
    return "A leitura assistida por IA prevaleceu nos campos do exame porque a foto estava dificil para o OCR local.";
  }
  if (session.assistedAttempted) {
    return "Tentamos uma leitura assistida, mas mantivemos o OCR local nesta execucao. Revise manualmente os campos destacados.";
  }
  return null;
}

export function MemberBodyCompositionTab({ memberId, memberName, memberPhone }: Props) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [ocrFile, setOcrFile] = useState<File | null>(null);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrResult, setOcrResult] = useState<BodyCompositionOcrResult | null>(null);
  const [ocrReadSession, setOcrReadSession] = useState<OcrReadSessionState>(EMPTY_OCR_READ_SESSION);
  const [editingEvaluationId, setEditingEvaluationId] = useState<string | null>(null);
  const [reportReadyEvaluationId, setReportReadyEvaluationId] = useState<string | null>(null);
  const [currentSource, setCurrentSource] = useState<EvaluationSource>("manual");
  const [reviewedManually, setReviewedManually] = useState(true);
  const [ocrMetadata, setOcrMetadata] = useState<OcrMetadataState>(EMPTY_OCR_METADATA);

  const { data: evaluations, isLoading } = useQuery({
    queryKey: ["body-composition", memberId],
    queryFn: () => bodyCompositionService.list(memberId),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const actuarSettingsQuery = useQuery({
    queryKey: ["actuar-settings", "body-composition-workspace"],
    queryFn: () => actuarSettingsService.getSettings(),
    staleTime: 30 * 1000,
  });

  const focusEvaluation = editingEvaluationId
    ? evaluations?.find((evaluation) => evaluation.id === editingEvaluationId) ?? null
    : evaluations?.[0] ?? null;

  const { data: syncStatus, isFetching: syncLoading } = useQuery({
    queryKey: ["body-composition-sync", memberId, focusEvaluation?.id],
    queryFn: () => bodyCompositionService.getActuarSyncStatus(memberId, focusEvaluation!.id),
    enabled: Boolean(memberId && focusEvaluation?.id),
    staleTime: 15 * 1000,
  });

  const {
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: buildDefaultValues(null),
  });
  const watchedWeightKg = watch("weight_kg");
  const watchedBodyWaterKg = watch("body_water_kg");

  useEffect(() => {
    setValue(
      "body_water_percent",
      calculateBodyWaterPercent(watchedWeightKg, watchedBodyWaterKg),
      { shouldValidate: true },
    );
  }, [setValue, watchedBodyWaterKg, watchedWeightKg]);

  function resetEditor(evaluation?: BodyCompositionEvaluation | null) {
    reset(buildDefaultValues(evaluation));
    setCurrentSource((evaluation?.source as EvaluationSource | undefined) ?? "manual");
    setReviewedManually(evaluation?.reviewed_manually ?? true);
    setOcrMetadata(buildOcrMetadata(evaluation));
    setOcrFile(null);
    setOcrResult(null);
    setOcrReadSession(EMPTY_OCR_READ_SESSION);
    setEditingEvaluationId(evaluation?.id ?? null);
    setReportReadyEvaluationId(evaluation?.id ?? null);
  }

  const saveMutation = useMutation({
    mutationFn: ({ payload, syncActuar }: { payload: BodyCompositionEvaluationCreate; syncActuar: boolean }) => {
      if (editingEvaluationId) {
        return bodyCompositionService.update(memberId, editingEvaluationId, payload, { syncActuar });
      }
      return bodyCompositionService.create(memberId, payload, { syncActuar });
    },
    onSuccess: async (savedEvaluation, variables) => {
      if (!variables.syncActuar) {
        toast.success(editingEvaluationId ? "Bioimpedancia atualizada apenas no sistema." : "Bioimpedancia salva apenas no sistema.");
      } else if (savedEvaluation.actuar_sync_status === "sync_pending") {
        const bridgeMode = actuarSettingsQuery.data?.effective_sync_mode === "local_bridge";
        toast.success(
          bridgeMode
            ? "Bioimpedancia salva e enviada para a estacao do Actuar."
            : "Bioimpedancia salva e enviada para sincronizacao com o Actuar.",
        );
      } else {
        toast.success(editingEvaluationId ? "Bioimpedancia atualizada com sucesso." : "Bioimpedancia registrada com sucesso.");
      }
      await invalidateAssessmentQueries(queryClient, memberId);
      resetEditor(savedEvaluation);
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Erro ao salvar a bioimpedancia.");
    },
  });

  const retrySyncMutation = useMutation({
    mutationFn: (evaluationId: string) => bodyCompositionService.retryActuarSync(memberId, evaluationId),
    onSuccess: async () => {
      toast.success("Nova tentativa de sincronizacao agendada.");
      await invalidateAssessmentQueries(queryClient, memberId);
      if (focusEvaluation?.id) {
        await queryClient.invalidateQueries({ queryKey: ["body-composition-sync", memberId, focusEvaluation.id] });
      }
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Nao foi possivel reagendar a sincronizacao.");
    },
  });

  const enqueueSyncMutation = useMutation({
    mutationFn: (evaluationId: string) => bodyCompositionService.enqueueActuarSync(memberId, evaluationId),
    onSuccess: async (payload) => {
      if (payload.sync_mode === "csv_export") {
        toast.success("Exportacao CSV preparada para lancamento manual no Actuar.");
      } else {
        toast.success("Job de sync enviado para processamento do Actuar.");
      }
      await invalidateAssessmentQueries(queryClient, memberId);
      if (focusEvaluation?.id) {
        await queryClient.invalidateQueries({ queryKey: ["body-composition-sync", memberId, focusEvaluation.id] });
      }
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Nao foi possivel enviar a avaliacao para o Actuar.");
    },
  });

  const manualConfirmMutation = useMutation({
    mutationFn: ({ evaluationId, reason, note }: { evaluationId: string; reason: string; note?: string | null }) =>
      bodyCompositionService.confirmManualSync(memberId, evaluationId, { reason, note }),
    onSuccess: async () => {
      toast.success("Sincronizacao manual confirmada com auditoria.");
      await invalidateAssessmentQueries(queryClient, memberId);
      if (focusEvaluation?.id) {
        await queryClient.invalidateQueries({ queryKey: ["body-composition-sync", memberId, focusEvaluation.id] });
      }
    },
    onError: () => toast.error("Nao foi possivel confirmar o sync manual."),
  });

  const linkMutation = useMutation({
    mutationFn: (payload: {
      actuar_external_id?: string | null;
      actuar_search_name?: string | null;
      actuar_search_document?: string | null;
      actuar_search_birthdate?: string | null;
      match_confidence?: number | null;
    }) => bodyCompositionService.upsertActuarLink(memberId, payload),
    onSuccess: async () => {
      toast.success("Vinculo com o cadastro Actuar atualizado.");
      if (focusEvaluation?.id) {
        await queryClient.invalidateQueries({ queryKey: ["body-composition-sync", memberId, focusEvaluation.id] });
      }
    },
    onError: () => toast.error("Nao foi possivel salvar o vinculo Actuar."),
  });

  const sendWhatsAppMutation = useMutation({
    mutationFn: (evaluationId: string) => bodyCompositionService.sendWhatsAppSummary(memberId, evaluationId),
    onSuccess: (payload) => {
      if (payload.status === "sent") {
        toast.success("Relatorio tecnico completo enviado pelo WhatsApp.");
        return;
      }
      toast.error(payload.error_detail || "O envio por WhatsApp nao foi concluido.");
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Nao foi possivel enviar o relatorio tecnico no WhatsApp.");
    },
  });

  const sendKommoMutation = useMutation({
    mutationFn: (evaluationId: string) => bodyCompositionService.sendKommoHandoff(memberId, evaluationId),
    onSuccess: (payload) => {
      if (payload.status === "queued" || payload.status === "sent") {
        if (payload.kommo_file_uuid && payload.file_attach_status === "attached") {
          toast.success("PDF anexado nativamente na Kommo e Salesbot acionado.");
          return;
        }
        toast.success(payload.detail || "Salesbot acionado pela Kommo. Aguardando resposta pelo canal oficial.");
        return;
      }
      toast.error(payload.detail || "A Kommo nao recebeu o envio desta bioimpedancia.");
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Nao foi possivel enviar o PDF pela Kommo.");
    },
  });

  const prepareKommoMutation = useMutation({
    mutationFn: (evaluationId: string) => bodyCompositionService.prepareKommoHandoff(memberId, evaluationId),
    onSuccess: (payload) => {
      if (payload.status === "sent") {
        toast.success("Fallback preparado na Kommo para o operador.");
        return;
      }
      toast.error(payload.detail || "A Kommo nao recebeu o fallback desta bioimpedancia.");
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Nao foi possivel preparar esta bioimpedancia na Kommo.");
    },
  });

  const highlightedWarnings = new Map(
    (ocrMetadata.ocr_warnings_json ?? [])
      .filter((warning) => warning.field)
      .map((warning) => [String(warning.field), warning]),
  );

  const rangeClassifications = buildBodyCompositionRangeClassifications(focusEvaluation);
  const canManualConfirm = user?.role === "owner" || user?.role === "manager";
  const currentSyncMode = syncStatus?.sync_mode ?? focusEvaluation?.actuar_sync_mode ?? "disabled";
  const syncDisabled = currentSyncMode === "disabled";
  const canManageSync = canManageActuarSync(user?.role) && !syncDisabled;
  const canConfirmManualSync = canManualConfirm && !syncDisabled;
  const syncSummary: BodyCompositionManualSyncSummary | null = syncStatus?.fallback_manual_summary ?? null;
  const localBridgeReady =
    currentSyncMode === "local_bridge"
      ? typeof actuarSettingsQuery.data?.automatic_sync_ready === "boolean"
        ? actuarSettingsQuery.data.automatic_sync_ready
        : null
      : null;
  const readCapability = resolveReadCapability({
    currentSource,
    ocrResult,
    storedWarnings: ocrMetadata.ocr_warnings_json,
    assistedAttempted: ocrReadSession.assistedAttempted,
    assistedError: ocrReadSession.assistedError,
  });
  const actuarCapability = resolveActuarCapability(syncStatus, { localBridgeReady });
  const unsupportedFieldsMessage = buildUnsupportedFieldsMessage(syncStatus);
  const canSendWhatsAppSummary = Boolean(focusEvaluation?.id && memberPhone?.trim());
  const canSendKommoHandoff = Boolean(focusEvaluation?.id);
  const automaticActuarSaveReady = Boolean(
    actuarSettingsQuery.data?.actuar_enabled &&
      actuarSettingsQuery.data?.actuar_auto_sync_body_composition &&
      actuarSettingsQuery.data?.automatic_sync_ready,
  );
  const saveButtonLabel = saveMutation.isPending
    ? "Salvando..."
    : automaticActuarSaveReady
      ? editingEvaluationId
        ? "Salvar e reenviar ao Actuar"
        : "Salvar e enviar ao Actuar"
      : editingEvaluationId
        ? "Salvar alteracoes"
        : "Salvar bioimpedancia";
  const selectedSex = watch("sex");
  const watchedAgeYears = watch("age_years");
  const watchedHeightCm = watch("height_cm");
  const watchedWeightForAnthropometry = watch("weight_kg");
  const watchedBioimpedancePercent = watch("body_fat_percent");
  const watchedManualOverridePercent = watch("body_fat_manual_override_percent");
  const watchedPreferredBodyFatSource = watch("preferred_body_fat_source");
  const watchedNeckCm = watch("neck_cm");
  const watchedWaistCm = watch("waist_cm");
  const watchedAbdomenCm = watch("abdomen_cm");
  const watchedHipCm = watch("hip_cm");
  const watchedRightArmFlexedCm = watch("right_arm_flexed_cm");
  const watchedLeftArmFlexedCm = watch("left_arm_flexed_cm");
  const watchedRightThighCm = watch("right_thigh_cm");
  const watchedLeftThighCm = watch("left_thigh_cm");
  const watchedRightCalfCm = watch("right_calf_cm");
  const watchedLeftCalfCm = watch("left_calf_cm");
  const watchedMeasurementProtocol = watch("measurement_protocol");
  const watchedSkinfoldChestMm = watch("skinfold_chest_mm");
  const watchedSkinfoldMidaxillaryMm = watch("skinfold_midaxillary_mm");
  const watchedSkinfoldSubscapularMm = watch("skinfold_subscapular_mm");
  const watchedSkinfoldTricepsMm = watch("skinfold_triceps_mm");
  const watchedSkinfoldBicepsMm = watch("skinfold_biceps_mm");
  const watchedSkinfoldAbdominalMm = watch("skinfold_abdominal_mm");
  const watchedSkinfoldSuprailiacMm = watch("skinfold_suprailiac_mm");
  const watchedSkinfoldThighMm = watch("skinfold_thigh_mm");
  const watchedSkinfoldCalfMm = watch("skinfold_calf_mm");
  const watchedBodyFatReviewCompleted = watch("body_fat_manual_review_completed");
  const watchedAnthropometryReviewCompleted = watch("anthropometry_review_completed");
  const selectedProtocol = getBodyCompositionProtocol(watchedMeasurementProtocol);
  const anthropometryProtocolItems = useMemo(
    () => buildAnthropometryProtocolItems({
      sex: selectedSex,
      ageYears: watchedAgeYears,
      heightCm: watchedHeightCm,
      weightKg: watchedWeightForAnthropometry,
      neckCm: watchedNeckCm,
      waistCm: watchedWaistCm,
      abdomenCm: watchedAbdomenCm,
      hipCm: watchedHipCm,
      measurementProtocol: watchedMeasurementProtocol,
      values: {
        weight_kg: watchedWeightForAnthropometry,
        waist_cm: watchedWaistCm,
        skinfold_chest_mm: watchedSkinfoldChestMm,
        skinfold_midaxillary_mm: watchedSkinfoldMidaxillaryMm,
        skinfold_subscapular_mm: watchedSkinfoldSubscapularMm,
        skinfold_triceps_mm: watchedSkinfoldTricepsMm,
        skinfold_biceps_mm: watchedSkinfoldBicepsMm,
        skinfold_abdominal_mm: watchedSkinfoldAbdominalMm,
        skinfold_suprailiac_mm: watchedSkinfoldSuprailiacMm,
        skinfold_thigh_mm: watchedSkinfoldThighMm,
        skinfold_calf_mm: watchedSkinfoldCalfMm,
      },
    }),
    [
      selectedSex,
      watchedAgeYears,
      watchedAbdomenCm,
      watchedHeightCm,
      watchedHipCm,
      watchedMeasurementProtocol,
      watchedNeckCm,
      watchedSkinfoldAbdominalMm,
      watchedSkinfoldBicepsMm,
      watchedSkinfoldCalfMm,
      watchedSkinfoldChestMm,
      watchedSkinfoldMidaxillaryMm,
      watchedSkinfoldSubscapularMm,
      watchedSkinfoldSuprailiacMm,
      watchedSkinfoldThighMm,
      watchedSkinfoldTricepsMm,
      watchedWaistCm,
      watchedWeightForAnthropometry,
    ],
  );
  const perimetryBalanceItems = useMemo(
    () => buildPerimetryBalanceItems({
      rightArmFlexed: watchedRightArmFlexedCm,
      leftArmFlexed: watchedLeftArmFlexedCm,
      rightThigh: watchedRightThighCm,
      leftThigh: watchedLeftThighCm,
      rightCalf: watchedRightCalfCm,
      leftCalf: watchedLeftCalfCm,
    }),
    [
      watchedLeftArmFlexedCm,
      watchedLeftCalfCm,
      watchedLeftThighCm,
      watchedRightArmFlexedCm,
      watchedRightCalfCm,
      watchedRightThighCm,
    ],
  );
  const anthropometryPreview = useMemo(
    () => calculateAnthropometryPreview({
      sex: selectedSex,
      ageYears: watchedAgeYears,
      heightCm: watchedHeightCm,
      weightKg: watchedWeightForAnthropometry,
      bioimpedancePercent: watchedBioimpedancePercent,
      manualOverridePercent: watchedManualOverridePercent,
      preferredSource: watchedPreferredBodyFatSource,
      neckCm: watchedNeckCm,
      waistCm: watchedWaistCm,
      abdomenCm: watchedAbdomenCm,
      hipCm: watchedHipCm,
      measurementProtocol: watchedMeasurementProtocol,
      skinfoldChestMm: watchedSkinfoldChestMm,
      skinfoldMidaxillaryMm: watchedSkinfoldMidaxillaryMm,
      skinfoldSubscapularMm: watchedSkinfoldSubscapularMm,
      skinfoldTricepsMm: watchedSkinfoldTricepsMm,
      skinfoldBicepsMm: watchedSkinfoldBicepsMm,
      skinfoldAbdominalMm: watchedSkinfoldAbdominalMm,
      skinfoldSuprailiacMm: watchedSkinfoldSuprailiacMm,
      skinfoldThighMm: watchedSkinfoldThighMm,
      skinfoldCalfMm: watchedSkinfoldCalfMm,
      reviewCompleted: Boolean(watchedBodyFatReviewCompleted || watchedAnthropometryReviewCompleted),
    }),
    [
      selectedSex,
      watchedAgeYears,
      watchedAbdomenCm,
      watchedAnthropometryReviewCompleted,
      watchedBioimpedancePercent,
      watchedBodyFatReviewCompleted,
      watchedHeightCm,
      watchedHipCm,
      watchedManualOverridePercent,
      watchedMeasurementProtocol,
      watchedNeckCm,
      watchedPreferredBodyFatSource,
      watchedSkinfoldAbdominalMm,
      watchedSkinfoldBicepsMm,
      watchedSkinfoldCalfMm,
      watchedSkinfoldChestMm,
      watchedSkinfoldMidaxillaryMm,
      watchedSkinfoldSubscapularMm,
      watchedSkinfoldSuprailiacMm,
      watchedSkinfoldThighMm,
      watchedSkinfoldTricepsMm,
      watchedWaistCm,
      watchedWeightForAnthropometry,
    ],
  );
  const reportEvaluationId = reportReadyEvaluationId ?? focusEvaluation?.id ?? null;
  const reportHref = reportEvaluationId ? `/assessments/members/${memberId}/body-composition/${reportEvaluationId}/report` : null;
  const canSendReportWhatsApp = Boolean(reportEvaluationId && memberPhone?.trim());
  const canSendReportKommo = Boolean(reportEvaluationId);

  async function handleOpenPdf(kind: "summary" | "technical") {
    if (!reportEvaluationId) return;
    const popup = window.open("", "_blank");
    try {
      if (popup) popup.opener = null;
      await bodyCompositionService.openPdf(memberId, reportEvaluationId, kind, popup);
    } catch {
      popup?.close();
      toast.error(kind === "technical" ? "Nao foi possivel abrir o relatorio tecnico." : "Nao foi possivel abrir o resumo do aluno.");
    }
  }

  async function handleCopyCriticalFields() {
    if (!focusEvaluation?.id) return;
    try {
      const summary = await bodyCompositionService.getManualSyncSummary(memberId, focusEvaluation.id);
      await navigator.clipboard.writeText(summary.summary_text);
      toast.success("Campos criticos copiados para apoiar o lancamento manual no Actuar.");
    } catch {
      toast.error("Nao foi possivel copiar o resumo manual.");
    }
  }

  function handleLinkMember() {
    const externalId = window.prompt("External ID do aluno no Actuar", syncStatus?.member_link?.actuar_external_id ?? "")?.trim();
    if (externalId === undefined) return;
    const searchName = window.prompt("Nome de busca no Actuar", syncStatus?.member_link?.actuar_search_name ?? "")?.trim();
    const searchBirthdate = window.prompt(
      "Nascimento no Actuar (AAAA-MM-DD)",
      syncStatus?.member_link?.actuar_search_birthdate ?? "",
    )?.trim();
    const searchDocument = window.prompt("Documento/CPF para busca no Actuar", "")?.trim();
    linkMutation.mutate({
      actuar_external_id: externalId || null,
      actuar_search_name: searchName || null,
      actuar_search_birthdate: searchBirthdate || null,
      actuar_search_document: searchDocument || null,
      match_confidence: externalId ? 1 : 0.8,
    });
  }

  function handleManualConfirm() {
    if (!focusEvaluation?.id || !canManualConfirm) return;
    const reason = window.prompt("Motivo da confirmacao manual no Actuar");
    if (!reason?.trim()) return;
    const note = window.prompt("Observacao opcional para auditoria", "") || undefined;
    manualConfirmMutation.mutate({ evaluationId: focusEvaluation.id, reason: reason.trim(), note });
  }

  function buildPayload(data: FormData): BodyCompositionEvaluationCreate {
    const needsReview = currentSource === "ocr_receipt" ? (reviewedManually ? false : ocrMetadata.needs_review) : false;
    return {
      ...data,
      body_water_percent: calculateBodyWaterPercent(data.weight_kg, data.body_water_kg),
      source: currentSource,
      reviewed_manually: currentSource === "manual" ? true : reviewedManually,
      raw_ocr_text: ocrMetadata.raw_ocr_text,
      parsing_confidence: ocrMetadata.ocr_confidence,
      ocr_confidence: ocrMetadata.ocr_confidence,
      ocr_warnings_json: ocrMetadata.ocr_warnings_json.length > 0 ? ocrMetadata.ocr_warnings_json : null,
      needs_review: needsReview,
      device_model: ocrMetadata.device_model,
      device_profile: ocrMetadata.device_profile,
      parsed_from_image: currentSource === "ocr_receipt" ? true : ocrMetadata.parsed_from_image,
      measured_ranges_json: ocrMetadata.measured_ranges_json,
      ocr_source_file_ref: data.ocr_source_file_ref || ocrMetadata.ocr_source_file_ref,
      notes: data.notes || null,
      report_file_url: data.report_file_url || null,
    };
  }

  function fillFromOcr(result: BodyCompositionOcrResult, file: File) {
    for (const section of FORM_SECTIONS) {
      for (const field of section.fields) {
        setValue(field.key, null);
      }
    }
    const values = result.values;
    const rawValues = values as Record<string, unknown>;
    const numericKeys = Object.keys(values).filter(
      (key) => key !== "evaluation_date" && key !== "measured_at" && key !== "sex",
    ) as NumericFieldKey[];
    for (const key of numericKeys) {
      const value = rawValues[key];
      if (typeof value === "number") {
        setValue(key, value);
      }
    }
    setValue(
      "evaluation_date",
      values.evaluation_date ?? values.measured_at?.slice(0, 10) ?? new Date().toISOString().split("T")[0],
    );
    setValue("sex", values.sex ?? null);
    setValue("ocr_source_file_ref", `local://${file.name}`);
    setCurrentSource("ocr_receipt");
    setReviewedManually(false);
    setReportReadyEvaluationId(null);
    setOcrMetadata({
      raw_ocr_text: result.raw_text,
      ocr_confidence: result.confidence,
      ocr_warnings_json: result.warnings,
      needs_review: result.needs_review,
      device_model: result.device_model ?? null,
      device_profile: result.device_profile,
      parsed_from_image: true,
      measured_ranges_json: result.ranges,
      ocr_source_file_ref: `local://${file.name}`,
    });
  }

  function submitBodyComposition(data: FormData, syncActuar: boolean) {
    if (currentSource === "ocr_receipt" && !reviewedManually) {
      toast.error("Confirme a revisao humana dos campos OCR antes de salvar a bioimpedancia.");
      return;
    }
    if (!hasAnyBodyCompositionMetric(data)) {
      toast.error("Preencha ao menos uma metrica da bioimpedancia antes de salvar.");
      return;
    }
    saveMutation.mutate({ payload: buildPayload(data), syncActuar });
  }

  function onSubmit(data: FormData) {
    submitBodyComposition(data, true);
  }

  async function handleReadPhoto(forceAssisted = false) {
    if (!ocrFile) {
      toast.error("Selecione uma imagem do exame.");
      return;
    }
    if (!isSupportedOcrImageFile(ocrFile)) {
      toast.error("Use uma imagem JPEG, PNG ou WEBP para a leitura.");
      return;
    }

    setOcrLoading(true);
    try {
      const readOutcome = await bodyCompositionService.readWithAssistedFallback(memberId, ocrFile, {
        deviceProfile: "tezewa_receipt_v1",
        forceAssisted,
      });
      setOcrReadSession({
        localResult: readOutcome.localResult,
        fallbackReasons: readOutcome.fallbackReasons,
        assistedAttempted: readOutcome.assistedAttempted,
        assistedError: readOutcome.assistedError,
      });
      setOcrResult(readOutcome.result);
      fillFromOcr(readOutcome.result, ocrFile);

      if (readOutcome.assistedError) {
        toast.error(`${readOutcome.assistedError} Revise os campos reconhecidos antes de salvar.`, { duration: 8000 });
      } else if (readOutcome.assistedUsed) {
        toast.success("Leitura assistida revisou os campos extraidos. Revise os destaques antes de salvar.");
      } else if (readOutcome.assistedAttempted) {
        toast.success("Mantivemos o OCR local nesta execucao. Revise os campos destacados antes de salvar.");
      } else {
        toast.success("OCR local concluido. Revise os campos destacados antes de salvar.");
      }
    } catch {
      toast.error("Falha ao ler a imagem. O preenchimento manual continua disponivel.");
    } finally {
      setOcrLoading(false);
    }
  }

  function handleNewEvaluation() {
    resetEditor(null);
    setCurrentSource("manual");
    setReviewedManually(true);
  }

  function handleEditEvaluation(evaluation: BodyCompositionEvaluation) {
    resetEditor(evaluation);
  }

  const ocrEngine = ocrResult?.engine ?? null;
  const localOcrText = ocrReadSession.localResult?.raw_text ?? ocrResult?.raw_text ?? null;
  const assistedReadSummary = buildAssistedReadSummary(ocrResult, ocrReadSession);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
          <div>
            <CardTitle>Bioimpedancia v2</CardTitle>
            <p className="text-sm text-lovable-ink-muted">
              Upload da foto, OCR por profile, revisao manual, interpretacao de apoio e sync Actuar desacoplado.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {focusEvaluation ? (
              <Button type="button" size="sm" variant="secondary" onClick={() => handleEditEvaluation(focusEvaluation)}>
                <Pencil size={14} />
                Editar atual
              </Button>
            ) : null}
            <Button type="button" size="sm" variant="primary" onClick={handleNewEvaluation}>
              <FilePlus2 size={14} />
              Nova avaliacao
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {!focusEvaluation ? (
            <p className="text-sm text-lovable-ink-muted">Nenhuma bioimpedancia registrada ainda.</p>
          ) : (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Peso" value={fmt(focusEvaluation.weight_kg, " kg")} />
              <MetricCard
                label="Gordura corporal estimada"
                value={fmt(focusEvaluation.body_fat_used_percent, "%")}
                helper={`Fonte: ${bodyFatSourceLabel(focusEvaluation.body_fat_used_source)}`}
              />
              <MetricCard label="Musculo esqueletico" value={fmt(focusEvaluation.skeletal_muscle_kg, " kg")} />
              <MetricCard label="Health score" value={fmt(focusEvaluation.health_score)} />
            </div>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <StatusPill tone="neutral">{sourceLabel(focusEvaluation?.source ?? currentSource)}</StatusPill>
            <StatusPill tone={(focusEvaluation?.needs_review ?? ocrMetadata.needs_review) ? "warning" : "success"}>
              Precisa revisao: {(focusEvaluation?.needs_review ?? ocrMetadata.needs_review) ? "sim" : "nao"}
            </StatusPill>
            <StatusPill tone={(focusEvaluation?.reviewed_manually ?? reviewedManually) ? "success" : "neutral"}>
              Revisado manualmente: {(focusEvaluation?.reviewed_manually ?? reviewedManually) ? "sim" : "nao"}
            </StatusPill>
            <StatusPill tone={statusPillToneForSync(syncStatus?.sync_status ?? focusEvaluation?.actuar_sync_status ?? null)}>
              Sync: {syncLabel(syncStatus?.sync_status ?? focusEvaluation?.actuar_sync_status)}
            </StatusPill>
            {focusEvaluation?.body_fat_percent != null ? (
              <StatusPill tone="neutral">Bioimpedancia bruta: {fmt(focusEvaluation.body_fat_percent, "%")}</StatusPill>
            ) : null}
            {focusEvaluation?.body_fat_confidence ? (
              <StatusPill tone={focusEvaluation.body_fat_confidence === "inconsistent" ? "warning" : "success"}>
                Confianca gordura: {bodyFatConfidenceLabel(focusEvaluation.body_fat_confidence)}
              </StatusPill>
            ) : null}
            {(focusEvaluation?.age_years ?? watch("age_years")) != null ? (
              <StatusPill tone="neutral">Idade: {focusEvaluation?.age_years ?? watch("age_years")} anos</StatusPill>
            ) : null}
            {(focusEvaluation?.height_cm ?? watch("height_cm")) != null ? (
              <StatusPill tone="neutral">Altura: {fmt(focusEvaluation?.height_cm ?? watch("height_cm"), " cm")}</StatusPill>
            ) : null}
            {(focusEvaluation?.sex ?? selectedSex) ? (
              <StatusPill tone="neutral">Sexo: {(focusEvaluation?.sex ?? selectedSex) === "female" ? "Feminino" : "Masculino"}</StatusPill>
            ) : null}
          </div>
          {automaticActuarSaveReady ? (
            <p className="mt-3 text-xs font-medium text-lovable-success">
              Estacao Actuar online. Ao salvar, esta avaliacao entra automaticamente no fluxo externo.
            </p>
          ) : null}
          {reportHref ? (
            <div className="mt-4 rounded-2xl border border-lovable-primary/20 bg-lovable-primary/5 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Relatorio premium pronto</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    Use o laudo no atendimento, no acompanhamento do professor e na entrega para o aluno.
                  </p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <Link to={reportHref}>
                    <Button type="button" size="sm" variant="primary">
                      <ArrowUpRight size={14} />
                      Abrir relatorio
                    </Button>
                  </Link>
                  {reportEvaluationId ? (
                    <Button type="button" size="sm" variant="secondary" onClick={() => void handleOpenPdf("summary")}>
                      <Download size={14} />
                      Resumo do aluno
                    </Button>
                  ) : null}
                  {reportEvaluationId ? (
                    <Button type="button" size="sm" variant="secondary" onClick={() => void handleOpenPdf("technical")}>
                      <Download size={14} />
                      Relatorio tecnico
                    </Button>
                  ) : null}
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={!canSendReportWhatsApp || sendWhatsAppMutation.isPending}
                    onClick={() => reportEvaluationId && sendWhatsAppMutation.mutate(reportEvaluationId)}
                  >
                    <MessageCircle size={14} />
                    {sendWhatsAppMutation.isPending ? "Enviando..." : "Enviar relatorio WhatsApp"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    disabled={!canSendReportKommo || sendKommoMutation.isPending}
                    onClick={() => reportEvaluationId && sendKommoMutation.mutate(reportEvaluationId)}
                  >
                    <Link2 size={14} />
                    {sendKommoMutation.isPending ? "Enviando..." : "Enviar PDF nativo via Kommo"}
                  </Button>
                  <Button
                    type="button"
                    size="sm"
                    variant="ghost"
                    disabled={!canSendReportKommo || prepareKommoMutation.isPending}
                    onClick={() => reportEvaluationId && prepareKommoMutation.mutate(reportEvaluationId)}
                  >
                    <Link2 size={14} />
                    {prepareKommoMutation.isPending ? "Preparando..." : "Preparar na Kommo"}
                  </Button>
                </div>
              </div>
            </div>
          ) : null}
        </CardContent>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.9fr)]">
        <Card>
          <CardHeader>
            <CardTitle>{editingEvaluationId ? "Editar bioimpedancia" : "Registrar bioimpedancia"}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <section className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">Leitura da foto</p>
                    <p className="text-xs text-lovable-ink-muted">
                      Profile ativo: <strong>tezewa_receipt_v1</strong>. O OCR preenche os campos e o professor confirma antes de salvar.
                    </p>
                  </div>
                  <div className="flex flex-wrap justify-end gap-2">
                    {ocrEngineLabel(ocrEngine) ? (
                      <StatusPill tone={statusPillToneForEngine(ocrEngine)}>
                        {ocrEngineLabel(ocrEngine)}
                      </StatusPill>
                    ) : null}
                    {ocrMetadata.ocr_confidence != null ? (
                      <StatusPill tone={ocrMetadata.ocr_confidence >= 0.85 ? "success" : "warning"}>
                        Confianca final: {Math.round(ocrMetadata.ocr_confidence * 100)}%
                      </StatusPill>
                    ) : null}
                  </div>
                </div>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <Input
                    type="file"
                    accept={SUPPORTED_OCR_IMAGE_ACCEPT}
                    onChange={(event) => setOcrFile(event.target.files?.[0] ?? null)}
                  />
                  <Button type="button" variant="ghost" onClick={() => void handleReadPhoto()} disabled={!ocrFile || ocrLoading}>
                    <ScanText size={14} />
                    {ocrLoading ? "Lendo..." : "Ler foto"}
                  </Button>
                  <Button type="button" variant="secondary" onClick={() => void handleReadPhoto(true)} disabled={!ocrFile || ocrLoading}>
                    <Sparkles size={14} />
                    {ocrLoading ? "Processando..." : "Tentar leitura assistida (IA)"}
                  </Button>
                </div>
                <div className="mt-3 flex flex-wrap gap-3 text-xs text-lovable-ink-muted">
                  <label className="inline-flex items-center gap-2">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border border-lovable-border"
                      checked={reviewedManually}
                      onChange={(event) => setReviewedManually(event.target.checked)}
                    />
                    Revisao manual concluida
                  </label>
                  <span>Origem atual: {sourceLabel(currentSource)}</span>
                  {ocrMetadata.device_model ? <span>Modelo: {ocrMetadata.device_model}</span> : null}
                </div>
                <div
                  className={`mt-3 rounded-xl border px-3 py-3 text-sm ${
                    readCapability.tone === "success"
                      ? "border-lovable-success/30 bg-lovable-success/10 text-lovable-success"
                      : readCapability.tone === "warning"
                        ? "border-lovable-warning/30 bg-lovable-warning/10 text-lovable-warning"
                        : "border-lovable-border bg-lovable-surface text-lovable-ink"
                  }`}
                >
                  <p className="font-semibold">{readCapability.title}</p>
                  <p className="mt-1 text-xs">{readCapability.description}</p>
                </div>
                {ocrMetadata.ocr_warnings_json.length > 0 ? (
                  <div className="mt-3 rounded-xl border border-lovable-warning/30 bg-lovable-warning/10 p-3 text-xs text-lovable-warning">
                    {ocrMetadata.ocr_warnings_json.map((warning, index) => (
                      <p key={`${warning.field}-${index}`}>- {warning.message}</p>
                    ))}
                  </div>
                ) : null}
                {assistedReadSummary ? (
                  <div className="mt-3 rounded-xl border border-lovable-border bg-lovable-surface p-3 text-xs text-lovable-ink">
                    <p className="font-semibold">Resumo da leitura assistida</p>
                    <p className="mt-1 text-lovable-ink-muted">{assistedReadSummary}</p>
                    {ocrReadSession.fallbackReasons.length > 0 ? (
                      <div className="mt-2 space-y-1 text-lovable-ink-muted">
                        {ocrReadSession.fallbackReasons.map((reason) => (
                          <p key={reason}>- {reason}</p>
                        ))}
                      </div>
                    ) : null}
                    {ocrReadSession.assistedError ? (
                      <p className="mt-2 text-lovable-danger">Falha da leitura assistida: {ocrReadSession.assistedError}</p>
                    ) : null}
                  </div>
                ) : null}
                {currentSource === "ocr_receipt" ? (
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <StatusPill tone="success">IA revisou</StatusPill>
                    <StatusPill tone="neutral">OCR local</StatusPill>
                    <StatusPill tone="warning">Incerto</StatusPill>
                  </div>
                ) : null}
                {localOcrText ? (
                  <details className="mt-3 rounded-xl border border-lovable-border bg-lovable-surface p-3 text-xs text-lovable-ink-muted">
                    <summary className="cursor-pointer font-semibold">
                      {ocrReadSession.assistedAttempted ? "Texto OCR local" : "Texto OCR normalizado"}
                    </summary>
                    <pre className="mt-2 max-h-52 overflow-auto whitespace-pre-wrap">{localOcrText}</pre>
                  </details>
                ) : null}
              </section>

              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <FormField label="Data da avaliacao" error={errors.evaluation_date?.message} required>
                  <Input type="date" {...register("evaluation_date")} />
                </FormField>
                <FormField label="Idade no exame" error={errors.age_years?.message}>
                  <Input type="text" inputMode="numeric" placeholder="29" autoComplete="off" {...register("age_years")} />
                </FormField>
                <FormField label="Sexo" error={errors.sex?.message}>
                  <Select defaultValue="" {...register("sex")}>
                    <option value="">Nao informado</option>
                    <option value="male">Masculino</option>
                    <option value="female">Feminino</option>
                  </Select>
                </FormField>
                <FormField label="Altura (cm)" error={errors.height_cm?.message}>
                  <Input type="text" inputMode="decimal" placeholder="178" autoComplete="off" {...register("height_cm")} />
                </FormField>
              </div>

              <div className="grid gap-4 md:grid-cols-1">
                <FormField label="Referencia da imagem OCR" error={errors.ocr_source_file_ref?.message}>
                  <Input placeholder="local://arquivo.jpg" {...register("ocr_source_file_ref")} />
                </FormField>
              </div>

              <section className="space-y-3 rounded-2xl border border-lovable-primary/20 bg-lovable-primary/5 p-4">
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Composicao corporal por medidas</p>
                  <p className="text-xs text-lovable-ink-muted">
                    O percentual usado no relatorio e resolvido pelo backend. A bioimpedancia bruta fica preservada como dado do exame.
                  </p>
                </div>
                <div className="grid gap-3 md:grid-cols-[1fr_1.2fr]">
                  <FormField label="Fonte do percentual de gordura usado no relatorio" error={errors.preferred_body_fat_source?.message}>
                    <Select defaultValue="geneos_composite" {...register("preferred_body_fat_source")}>
                      <option value="geneos_composite">Usar metodo composto GeneOS</option>
                      <option value="anthropometry">Usar medidas manuais</option>
                      <option value="bioimpedance">Usar bioimpedancia bruta</option>
                      <option value="manual_override">Informar manualmente</option>
                    </Select>
                  </FormField>
                  <FormField label="Protocolo antropometrico" error={errors.measurement_protocol?.message}>
                    <Select defaultValue="manual_bioimpedance" {...register("measurement_protocol")}>
                      {BODY_COMPOSITION_PROTOCOLS.map((protocol) => (
                        <option key={protocol.key} value={protocol.key}>
                          {protocol.label}
                        </option>
                      ))}
                    </Select>
                    <p className="mt-1 text-xs text-lovable-ink-muted">
                      {selectedProtocol?.supported
                        ? "Calculavel automaticamente se todas as dobras obrigatorias forem preenchidas."
                        : "Protocolo catalogado para registro/revisao. Nao altera a gordura oficial sem dados calculaveis ou override."}
                    </p>
                  </FormField>
                </div>
                <div className="grid gap-3 md:grid-cols-[1fr_1.2fr]">
                  <div className="rounded-xl border border-lovable-border bg-lovable-surface p-3 text-xs text-lovable-ink-muted">
                    <p className="font-semibold text-lovable-ink">Resultado salvo</p>
                    <p className="mt-1">
                      Gordura oficial: {fmt(focusEvaluation?.body_fat_used_percent, "%")}
                      {" · "}
                      Fonte: {bodyFatSourceLabel(focusEvaluation?.body_fat_used_source)}
                      {" · "}
                      Metodo: {focusEvaluation?.body_fat_method ? bodyFatMethodLabel(focusEvaluation.body_fat_method) : preferredBodyFatSourceLabel(focusEvaluation?.preferred_body_fat_source)}
                    </p>
                    {focusEvaluation?.body_fat_range_min != null || focusEvaluation?.body_fat_range_max != null ? (
                      <p className="mt-1">
                        Faixa estimada: {fmt(focusEvaluation?.body_fat_range_min, "%")} a {fmt(focusEvaluation?.body_fat_range_max, "%")}
                      </p>
                    ) : null}
                    {focusEvaluation?.fat_mass_estimated_kg != null || focusEvaluation?.lean_mass_estimated_kg != null ? (
                      <p className="mt-1">
                        Massa gorda estimada: {fmt(focusEvaluation?.fat_mass_estimated_kg, " kg")} · Massa livre estimada:{" "}
                        {fmt(focusEvaluation?.lean_mass_estimated_kg, " kg")}
                      </p>
                    ) : null}
                  </div>
                </div>
                <div className="grid gap-3 lg:grid-cols-[1.15fr_0.85fr]">
                  <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Checklist do protocolo</p>
                    <p className="mt-1 text-xs text-lovable-ink-muted">
                      Confere os campos que entram no calculo. Braco, coxa, panturrilha, torax e ombro ficam so para evolucao.
                    </p>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {anthropometryProtocolItems.map((item) => (
                        <div key={item.label} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                          <div className="flex items-center justify-between gap-2">
                            <p className="text-sm font-semibold text-lovable-ink">{item.label}</p>
                            <StatusPill tone={item.ready ? "success" : "warning"}>{item.ready ? "ok" : "pendente"}</StatusPill>
                          </div>
                          <p className="mt-1 text-xs text-lovable-ink-muted">{item.description}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Comparativo bilateral</p>
                    <p className="mt-1 text-xs text-lovable-ink-muted">
                      Acompanha assimetria de medidas de evolucao. Estes valores nao entram no calculo da gordura.
                    </p>
                    <div className="mt-3 space-y-2">
                      {perimetryBalanceItems.length === 0 ? (
                        <p className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-xs text-lovable-ink-muted">
                          Preencha pares direito/esquerdo para comparar.
                        </p>
                      ) : (
                        perimetryBalanceItems.map((item) => (
                          <div key={item.label} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-xs">
                            <div className="flex items-center justify-between gap-2">
                              <p className="font-semibold text-lovable-ink">{item.label}</p>
                              <StatusPill tone={item.delta > 2 ? "warning" : "success"}>{item.delta.toFixed(1)} cm</StatusPill>
                            </div>
                            <p className="mt-1 text-lovable-ink-muted">
                              Direita {item.right.toFixed(1)} cm - Esquerda {item.left.toFixed(1)} cm
                            </p>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
                <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
                  <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Previa antes de salvar</p>
                      <p className="mt-1 text-xl font-semibold text-lovable-ink">{fmt(anthropometryPreview.usedPercent, "%")}</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">
                        O backend recalcula e valida ao salvar. Esta previa permite revisar fonte, metodo e divergencias antes de gerar relatorio.
                      </p>
                    </div>
                    <StatusPill
                      tone={
                        anthropometryPreview.status === "ready" || anthropometryPreview.status === "manual_override"
                          ? "success"
                          : anthropometryPreview.status === "needs_review"
                            ? "warning"
                            : "neutral"
                      }
                    >
                      {anthropometryStatusLabel(anthropometryPreview.status)}
                    </StatusPill>
                  </div>
                  <div className="mt-4 grid gap-3 md:grid-cols-4">
                    <Metric label="Fonte" value={bodyFatSourceLabel(anthropometryPreview.usedSource)} />
                    <Metric label="Metodo" value={bodyFatMethodLabel(anthropometryPreview.method)} />
                    <Metric label="Confianca" value={bodyFatConfidenceLabel(anthropometryPreview.confidence)} />
                    <Metric
                      label="Faixa provavel"
                      value={
                        anthropometryPreview.rangeMin != null || anthropometryPreview.rangeMax != null
                          ? `${fmt(anthropometryPreview.rangeMin, "%")} - ${fmt(anthropometryPreview.rangeMax, "%")}`
                          : "-"
                      }
                    />
                    <Metric label="Navy" value={fmt(anthropometryPreview.navyPercent, "%")} />
                    <Metric label="RFM" value={fmt(anthropometryPreview.rfmPercent, "%")} />
                    <Metric label="Massa gorda estimada" value={fmt(anthropometryPreview.fatMassKg, " kg")} />
                    <Metric label="Massa livre estimada" value={fmt(anthropometryPreview.leanMassKg, " kg")} />
                  </div>
                  {anthropometryPreview.differenceBetweenSources != null ? (
                    <p className="mt-3 text-xs text-lovable-ink-muted">
                      Divergencia contra a bioimpedancia bruta: {fmt(anthropometryPreview.differenceBetweenSources, " p.p.")}.
                    </p>
                  ) : null}
                  {anthropometryPreview.missingFields.length > 0 ? (
                    <p className="mt-3 text-xs text-lovable-warning">
                      Para calcular por medidas, complete: {anthropometryPreview.missingFields.join(", ")}.
                    </p>
                  ) : null}
                  {anthropometryPreview.flags.length > 0 ? (
                    <div className="mt-3 flex flex-wrap gap-2">
                      {anthropometryPreview.flags.map((flag) => (
                        <StatusPill key={flag} tone="warning">{qualityFlagLabel(flag)}</StatusPill>
                      ))}
                    </div>
                  ) : null}
                  <div className="mt-4 grid gap-3 md:grid-cols-2">
                    <label className="flex items-start gap-2 rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-xs text-lovable-ink-muted">
                      <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border border-lovable-border" {...register("body_fat_manual_review_completed")} />
                      <span>
                        <strong className="block text-lovable-ink">Revisao manual do percentual concluida</strong>
                        Use quando houver divergencia relevante, inconsistencia Navy/RFM ou override manual.
                      </span>
                    </label>
                    <label className="flex items-start gap-2 rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-xs text-lovable-ink-muted">
                      <input type="checkbox" className="mt-0.5 h-4 w-4 rounded border border-lovable-border" {...register("anthropometry_review_completed")} />
                      <span>
                        <strong className="block text-lovable-ink">Revisao antropometrica concluida</strong>
                        Confirma que pontos de medida e protocolo foram revisados pelo professor.
                      </span>
                    </label>
                  </div>
                </div>
              </section>

              {FORM_SECTIONS.map((section) => (
                <section key={section.title} className="space-y-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{section.title}</p>
                    <p className="text-xs text-lovable-ink-muted">{section.description}</p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    {section.fields.map((field) => {
                      const warning = highlightedWarnings.get(field.key);
                      const fieldSignal = field.calculated
                        ? null
                        : resolveBodyCompositionFieldSignal({
                            fieldKey: field.key,
                            currentSource,
                            currentValue: watch(field.key),
                            ocrResult,
                            localResult: ocrReadSession.localResult,
                            storedWarnings: ocrMetadata.ocr_warnings_json,
                          });
                      return (
                        <FormField
                          key={field.key}
                          label={
                            <span className="flex flex-wrap items-center gap-2">
                              <span>{field.label}</span>
                              {field.calculated ? <StatusPill tone="neutral">Calculado</StatusPill> : null}
                              {fieldSignal ? <StatusPill tone={fieldSignal.tone}>{fieldSignal.label}</StatusPill> : null}
                            </span>
                          }
                          error={errors[field.key]?.message}
                        >
                          <div className="space-y-1">
                            <Input
                              type="text"
                              inputMode={field.step === "1" ? "numeric" : "decimal"}
                              placeholder={field.placeholder}
                              className={warningTone(warning)}
                              autoComplete="off"
                              readOnly={field.calculated}
                              {...register(field.key)}
                            />
                            {field.description ? (
                              <p className="text-xs text-lovable-ink-muted">{field.description}</p>
                            ) : null}
                            {fieldSignal ? (
                              <p className={`text-xs ${fieldSignalTextClass(fieldSignal.tone)}`}>{fieldSignal.description}</p>
                            ) : null}
                          </div>
                        </FormField>
                      );
                    })}
                  </div>
                </section>
              ))}

              <div className="grid gap-4 md:grid-cols-3">
                <FormField label="URL do laudo/arquivo" error={errors.report_file_url?.message}>
                  <Input placeholder="https://..." {...register("report_file_url")} />
                </FormField>
                <FormField label="Observacoes" error={errors.notes?.message}>
                  <Textarea rows={4} placeholder="Notas operacionais para o professor..." {...register("notes")} />
                </FormField>
                <FormField label="Observacoes da antropometria" error={errors.anthropometry_notes?.message}>
                  <Textarea rows={4} placeholder="Observacoes sobre protocolo, pontos de medida ou revisao manual..." {...register("anthropometry_notes")} />
                </FormField>
              </div>

              <div className="flex flex-wrap justify-end gap-2">
                {editingEvaluationId ? (
                  <Button type="button" variant="ghost" onClick={handleNewEvaluation} disabled={saveMutation.isPending}>
                    <X size={14} />
                    Cancelar
                  </Button>
                ) : null}
                {automaticActuarSaveReady ? (
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={saveMutation.isPending}
                    onClick={() => void handleSubmit((data) => submitBodyComposition(data, false))()}
                  >
                    <Save size={14} />
                    Salvar apenas no sistema
                  </Button>
                ) : null}
                <Button type="submit" variant="primary" disabled={saveMutation.isPending}>
                  {editingEvaluationId ? <Save size={14} /> : <ImageUp size={14} />}
                  {saveButtonLabel}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Interpretacao de apoio</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!focusEvaluation ? (
                <p className="text-sm text-lovable-ink-muted">Salve a avaliacao para gerar a interpretacao de apoio ao professor.</p>
              ) : (
                <>
                  <AIAssistantPanel
                    assistant={focusEvaluation.assistant}
                    title="IA da bioimpedancia"
                    subtitle="Achados principais, comparacao com o exame anterior e orientacao inicial para o coach."
                  />
                  {focusEvaluation.ai_training_focus_json?.prompt_metadata ? (
                    <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-lovable-primary/20 bg-lovable-primary-soft/25 px-4 py-3 text-xs text-lovable-ink-muted">
                      <StatusPill tone="neutral">Agente especialista</StatusPill>
                      <StatusPill tone="neutral">
                        Prompt v{focusEvaluation.ai_training_focus_json.prompt_metadata.prompt_version ?? "-"}
                      </StatusPill>
                      <StatusPill tone="neutral">
                        Modelo: {focusEvaluation.ai_training_focus_json.prompt_metadata.model ?? "-"}
                      </StatusPill>
                    </div>
                  ) : null}
                  <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para professor</p>
                    <p className="mt-2 text-sm text-lovable-ink">{resolveCoachSummary(focusEvaluation) || "Resumo ainda nao gerado."}</p>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para o aluno</p>
                        <p className="mt-2 text-sm text-lovable-ink">{resolveMemberSummary(focusEvaluation) || "Resumo amigavel ainda nao gerado."}</p>
                      </div>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={!focusEvaluation?.id || !canSendWhatsAppSummary || sendWhatsAppMutation.isPending}
                        onClick={() => focusEvaluation?.id && sendWhatsAppMutation.mutate(focusEvaluation.id)}
                      >
                        <MessageCircle size={14} />
                        {sendWhatsAppMutation.isPending ? "Enviando..." : "Enviar no WhatsApp"}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        disabled={!canSendKommoHandoff || sendKommoMutation.isPending}
                        onClick={() => focusEvaluation?.id && sendKommoMutation.mutate(focusEvaluation.id)}
                      >
                        <Link2 size={14} />
                        {sendKommoMutation.isPending ? "Enviando..." : "Enviar PDF nativo via Kommo"}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        disabled={!canSendKommoHandoff || prepareKommoMutation.isPending}
                        onClick={() => focusEvaluation?.id && prepareKommoMutation.mutate(focusEvaluation.id)}
                      >
                        <Link2 size={14} />
                        {prepareKommoMutation.isPending ? "Preparando..." : "Preparar na Kommo"}
                      </Button>
                    </div>
                    <div className="mt-3 space-y-1 text-xs text-lovable-ink-muted">
                      <p>
                        {memberPhone
                          ? `WhatsApp direto: envia este resumo e o PDF da bioimpedancia para o numero cadastrado${memberName ? ` de ${memberName}` : " do aluno"}.`
                          : "Cadastre o WhatsApp do aluno para enviar este resumo com PDF pelo canal direto."}
                      </p>
                      <p>
                        Kommo: anexa o PDF nativamente no lead e aciona o Salesbot no pipeline configurado. Se a rota ainda nao estiver pronta, use Preparar na Kommo como fallback.
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Alertas principais</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {(focusEvaluation.ai_risk_flags_json ?? ["Sem alertas estruturados"]).map((flag) => (
                        <StatusPill key={flag} tone={flag.includes("acima") || flag.includes("abaixo") ? "warning" : "neutral"}>
                          {flag}
                        </StatusPill>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Classificacao por faixa</p>
                    <div className="mt-2 space-y-2">
                      {rangeClassifications.length === 0 ? (
                        <p className="text-sm text-lovable-ink-muted">Sem faixas impressas suficientes para classificar este exame.</p>
                      ) : (
                        rangeClassifications.map((item) => (
                          <div key={item.label} className="flex items-center justify-between rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm">
                            <span className="text-lovable-ink">{item.label}</span>
                            <StatusPill tone={item.status === "dentro" ? "success" : "warning"}>{item.status}</StatusPill>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                    <p className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">
                      <Sparkles size={14} />
                      Direcao inicial sugerida
                    </p>
                    <p className="mt-2 text-sm text-lovable-ink">
                      Objetivo principal: {formatBodyCompositionGoal(focusEvaluation.ai_training_focus_json?.primary_goal) || "Acompanhamento geral"}
                    </p>
                    <p className="text-sm text-lovable-ink">
                      Objetivo secundario: {formatBodyCompositionGoal(focusEvaluation.ai_training_focus_json?.secondary_goal) || "Preservacao de massa magra"}
                    </p>
                    <ul className="mt-2 space-y-1 text-sm text-lovable-ink-muted">
                      {(focusEvaluation.ai_training_focus_json?.suggested_focuses ?? []).map((focus) => (
                        <li key={focus}>- {focus}</li>
                      ))}
                    </ul>
                  </div>
                </>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3">
              <CardTitle>Sync Actuar</CardTitle>
              <div className="flex flex-wrap gap-2">
                {focusEvaluation?.id && canManageSync && !automaticActuarSaveReady ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => enqueueSyncMutation.mutate(focusEvaluation.id)}
                    disabled={enqueueSyncMutation.isPending || (currentSyncMode === "local_bridge" && localBridgeReady === false)}
                  >
                    <RefreshCcw size={14} />
                    {enqueueSyncMutation.isPending ? "Enviando..." : "Enviar para Actuar"}
                  </Button>
                ) : null}
                {focusEvaluation?.id && canManageSync && syncStatus?.can_retry ? (
                  <Button
                    type="button"
                    size="sm"
                    variant="secondary"
                    onClick={() => retrySyncMutation.mutate(focusEvaluation.id)}
                    disabled={retrySyncMutation.isPending || (currentSyncMode === "local_bridge" && localBridgeReady === false)}
                  >
                    <RefreshCcw size={14} />
                    {retrySyncMutation.isPending ? "Agendando..." : "Reprocessar"}
                  </Button>
                ) : null}
              </div>
            </CardHeader>
            <CardContent className="space-y-3">
              {!focusEvaluation ? (
                <p className="text-sm text-lovable-ink-muted">Salve uma avaliacao para acompanhar o sync externo.</p>
              ) : syncLoading ? (
                <Skeleton className="h-24 w-full rounded-2xl" />
              ) : !syncStatus ? (
                <div className="rounded-2xl border border-lovable-danger/25 bg-lovable-danger/10 px-4 py-3 text-sm text-lovable-danger">
                  {getPermissionAwareMessage(null, "Nao foi possivel carregar o status de sync do Actuar.")}
                </div>
              ) : (
                <>
                  <div
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      actuarCapability.tone === "success"
                        ? "border-lovable-success/30 bg-lovable-success/10 text-lovable-success"
                        : actuarCapability.tone === "warning"
                          ? "border-lovable-warning/30 bg-lovable-warning/10 text-lovable-warning"
                          : "border-lovable-border bg-lovable-surface text-lovable-ink"
                    }`}
                  >
                    <p className="font-semibold">{actuarCapability.title}</p>
                    <p className="mt-1 text-xs">{actuarCapability.description}</p>
                  </div>
                  <div
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      syncStatus?.training_ready
                        ? "border-lovable-success/30 bg-lovable-success/10 text-lovable-success"
                        : "border-lovable-warning/30 bg-lovable-warning/10 text-lovable-warning"
                    }`}
                  >
                    <p className="font-semibold">
                      {syncStatus?.training_ready
                        ? "Pronta para treino no Actuar"
                        : "Esta avaliacao ainda NAO esta pronta para uso no treino do Actuar"}
                    </p>
                    {!syncStatus?.training_ready ? (
                      <p className="mt-1 text-xs">
                        Os campos criticos ainda nao foram sincronizados com sucesso. Use o fallback manual assistido se necessario.
                      </p>
                    ) : null}
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <Metric label="Modo" value={syncModeLabel(syncStatus?.sync_mode ?? focusEvaluation.actuar_sync_mode)} />
                    <Metric label="Status" value={syncLabel(syncStatus?.sync_status ?? focusEvaluation.actuar_sync_status)} />
                    <Metric label="Pronta para treino?" value={syncStatus?.training_ready ? "Sim" : "Nao"} />
                    <Metric label="Ultimo sync" value={syncStatus?.last_synced_at ? new Date(syncStatus.last_synced_at).toLocaleString("pt-BR") : "-"} />
                    <Metric label="External ID" value={syncStatus?.external_id ?? focusEvaluation.actuar_external_id ?? "-"} />
                    <Metric label="Erro codigo" value={syncStatus?.last_error_code ?? focusEvaluation.sync_last_error_code ?? "-"} />
                  </div>
                  {(syncStatus?.last_error ?? focusEvaluation.actuar_last_error) ? (
                    <div className="rounded-xl border border-lovable-danger/25 bg-lovable-danger/10 px-3 py-2 text-sm text-lovable-danger">
                      {(syncStatus?.last_error ?? focusEvaluation.actuar_last_error) as string}
                    </div>
                  ) : null}
                  {syncStatus?.member_link ? (
                    <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink">
                      <p className="font-semibold">Vinculo Actuar</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">
                        External ID: {syncStatus.member_link.actuar_external_id ?? "-"} · Nome de busca: {syncStatus.member_link.actuar_search_name ?? "-"}
                      </p>
                    </div>
                  ) : null}
                  {syncStatus?.critical_fields?.length ? (
                    <div className="space-y-2">
                      <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Campos criticos para treino</p>
                      <div className="space-y-2">
                        {syncStatus.critical_fields.map((field) => (
                          <div key={field.field} className="flex items-center justify-between rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm">
                            <div>
                              <p className="font-semibold text-lovable-ink">{field.actuar_field ?? field.field}</p>
                              <p className="text-xs text-lovable-ink-muted">{field.classification}</p>
                            </div>
                            <span className="text-xs text-lovable-ink-muted">{field.value ?? "-"}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  {unsupportedFieldsMessage ? (
                    <div className="space-y-2 rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-3 text-sm text-lovable-ink">
                      <div>
                        <p className="font-semibold">Campos mantidos apenas no {PRODUCT_NAME}</p>
                        <p className="mt-1 text-xs text-lovable-ink-muted">{unsupportedFieldsMessage}</p>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {syncStatus.unsupported_fields.map((field) => (
                          <StatusPill key={field.field} tone="neutral">
                            {field.actuar_field ?? field.field}
                          </StatusPill>
                        ))}
                      </div>
                    </div>
                  ) : null}
                  <div className="flex flex-wrap gap-2">
                    <Button type="button" variant="ghost" onClick={() => void handleCopyCriticalFields()} disabled={!focusEvaluation?.id}>
                      <Copy size={14} />
                      {syncDisabled ? "Copiar resumo para lancamento manual" : "Copiar campos criticos"}
                    </Button>
                    {canManageSync ? (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={handleLinkMember}
                        disabled={linkMutation.isPending}
                      >
                        <Link2 size={14} />
                        {linkMutation.isPending ? "Salvando vinculo..." : "Vincular aluno Actuar"}
                      </Button>
                    ) : null}
                    {canConfirmManualSync ? (
                      <Button
                        type="button"
                        variant="ghost"
                        onClick={handleManualConfirm}
                        disabled={!focusEvaluation?.id || manualConfirmMutation.isPending}
                      >
                        <ShieldCheck size={14} />
                        {manualConfirmMutation.isPending ? "Confirmando..." : "Confirmar sync manual"}
                      </Button>
                    ) : null}
                  </div>
                  {syncSummary?.summary_text ? (
                    <details className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 text-xs text-lovable-ink-muted">
                      <summary className="cursor-pointer font-semibold text-lovable-ink">Resumo pronto para lancamento manual</summary>
                      <pre className="mt-2 whitespace-pre-wrap">{syncSummary.summary_text}</pre>
                    </details>
                  ) : null}
                  {syncStatus?.attempts?.length ? (
                    <div className="space-y-2">
                      <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Tentativas recentes</p>
                      {syncStatus.attempts.slice(0, 3).map((attempt) => (
                        <div key={attempt.id} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm">
                          <div className="flex items-center justify-between gap-2">
                            <span className="font-semibold text-lovable-ink">{syncLabel(attempt.status)}</span>
                            <span className="text-xs text-lovable-ink-muted">{new Date(attempt.started_at).toLocaleString("pt-BR")}</span>
                          </div>
                          <p className="text-xs text-lovable-ink-muted">
                            {attempt.worker_id ?? "worker"}{attempt.error_code ? ` · ${attempt.error_code}` : ""}
                          </p>
                        </div>
                      ))}
                    </div>
                  ) : null}
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Historico de bioimpedancia</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {isLoading ? (
            <>
              <Skeleton className="h-28 w-full rounded-2xl" />
              <Skeleton className="h-28 w-full rounded-2xl" />
            </>
          ) : !evaluations?.length ? (
            <p className="text-sm text-lovable-ink-muted">Nenhuma bioimpedancia registrada ainda.</p>
          ) : (
            evaluations.map((evaluation) => (
              <article key={evaluation.id} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="space-y-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-semibold text-lovable-ink">{fmtDate(evaluation.evaluation_date)}</span>
                      <StatusPill tone="neutral">{sourceLabel(evaluation.source)}</StatusPill>
                      <StatusPill tone={evaluation.needs_review ? "warning" : "success"}>
                        Revisao: {evaluation.needs_review ? "pendente" : "ok"}
                      </StatusPill>
                      <StatusPill tone={evaluation.reviewed_manually ? "success" : "neutral"}>
                        Revisado manualmente: {evaluation.reviewed_manually ? "sim" : "nao"}
                      </StatusPill>
                      <StatusPill tone={statusPillToneForSync(evaluation.actuar_sync_status)}>
                        Sync: {syncLabel(evaluation.actuar_sync_status)}
                      </StatusPill>
                    </div>
                    <div className="grid gap-x-4 gap-y-2 sm:grid-cols-2 xl:grid-cols-3">
                      {HISTORY_METRICS.map((metric) => (
                        <Metric
                          key={metric.label}
                          label={metric.label}
                          value={fmt((evaluation[metric.field] as number | null | undefined) ?? null, metric.unit ?? "")}
                        />
                      ))}
                    </div>
                    {evaluation.ai_coach_summary ? (
                      <p className="text-sm text-lovable-ink-muted">{evaluation.ai_coach_summary}</p>
                    ) : null}
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Link to={`/assessments/members/${memberId}/body-composition/${evaluation.id}/report`}>
                      <Button type="button" size="sm" variant="ghost">
                        <ArrowUpRight size={14} />
                        Relatorio
                      </Button>
                    </Link>
                    <Button type="button" size="sm" variant="secondary" onClick={() => handleEditEvaluation(evaluation)}>
                      <Pencil size={14} />
                      Editar
                    </Button>
                  </div>
                </div>
              </article>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-xs text-lovable-ink-muted">{label}</span>
      <p className="font-semibold text-lovable-ink">{value}</p>
    </div>
  );
}

function MetricCard({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
      <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-lovable-ink">{value}</p>
      {helper ? <p className="mt-1 text-xs text-lovable-ink-muted">{helper}</p> : null}
    </article>
  );
}

function StatusPill({ children, tone }: { children: ReactNode; tone: "success" | "warning" | "neutral" }) {
  const className =
    tone === "success"
      ? "border-lovable-success/30 bg-lovable-success/10 text-lovable-success"
      : tone === "warning"
        ? "border-lovable-warning/30 bg-lovable-warning/10 text-lovable-warning"
        : "border-lovable-border bg-lovable-surface text-lovable-ink";

  return <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${className}`}>{children}</span>;
}
