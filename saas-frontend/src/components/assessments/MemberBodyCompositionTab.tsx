import { AxiosError } from "axios";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Copy,
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
import { useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { z } from "zod";

import { AIAssistantPanel } from "../common/AIAssistantPanel";
import { actuarSettingsService } from "../../services/actuarSettingsService";
import { bodyCompositionService } from "../../services/bodyCompositionService";
import type { BodyCompositionOcrEngine, BodyCompositionOcrResult } from "../../services/bodyCompositionOcr";
import type {
  BodyCompositionEvaluation,
  BodyCompositionEvaluationCreate,
  BodyCompositionManualSyncSummary,
  BodyCompositionOcrWarning,
  EvaluationSource,
} from "../../types";
import { useAuth } from "../../hooks/useAuth";
import { getPermissionAwareMessage } from "../../utils/httpErrors";
import { canManageActuarSync } from "../../utils/roleAccess";
import { Button } from "../ui2/Button";
import { Card, CardContent, CardHeader, CardTitle } from "../ui2/Card";
import { FormField } from "../ui2/FormField";
import { Input } from "../ui2/Input";
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

const schema = z.object({
  evaluation_date: z.string().min(1, "Data obrigatoria"),
  weight_kg: nullableNumberField,
  body_fat_kg: nullableNumberField,
  body_fat_percent: nullableNumberField,
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
  | "weight_kg"
  | "body_fat_kg"
  | "body_fat_percent"
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
    title: "Composicao corporal",
    description: "Medidas principais do exame e leitura corporal central.",
    fields: [
      { key: "weight_kg", label: "Peso (kg)", placeholder: "84.5", step: "0.1" },
      { key: "body_fat_kg", label: "Gordura corporal (kg)", placeholder: "19.46", step: "0.01" },
      { key: "body_fat_percent", label: "Gordura corporal (%)", placeholder: "23.0", step: "0.1" },
      { key: "waist_hip_ratio", label: "Relacao cintura-quadril", placeholder: "0.88", step: "0.01" },
      { key: "fat_free_mass_kg", label: "Massa livre de gordura (kg)", placeholder: "65.0", step: "0.1" },
      { key: "lean_mass_kg", label: "Massa magra (legado)", placeholder: "63.0", step: "0.1" },
      { key: "muscle_mass_kg", label: "Massa muscular (kg)", placeholder: "37.2", step: "0.1" },
      { key: "skeletal_muscle_kg", label: "Musculo esqueletico (kg)", placeholder: "35.6", step: "0.1" },
      { key: "body_water_kg", label: "Agua corporal (kg)", placeholder: "43.3", step: "0.1" },
      { key: "body_water_percent", label: "Agua corporal (%)", placeholder: "51.2", step: "0.1" },
      { key: "protein_kg", label: "Proteina (kg)", placeholder: "17.7", step: "0.1" },
      { key: "inorganic_salt_kg", label: "Sal inorganico (kg)", placeholder: "3.2", step: "0.1" },
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

const HISTORY_METRICS: Array<{ label: string; field: keyof BodyCompositionEvaluation; unit?: string }> = [
  { label: "Peso", field: "weight_kg", unit: " kg" },
  { label: "Gordura kg", field: "body_fat_kg", unit: " kg" },
  { label: "Gordura %", field: "body_fat_percent", unit: "%" },
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
  return {
    evaluation_date: evaluation?.evaluation_date ?? new Date().toISOString().split("T")[0],
    weight_kg: evaluation?.weight_kg ?? null,
    body_fat_kg: evaluation?.body_fat_kg ?? null,
    body_fat_percent: evaluation?.body_fat_percent ?? null,
    waist_hip_ratio: evaluation?.waist_hip_ratio ?? null,
    fat_free_mass_kg: evaluation?.fat_free_mass_kg ?? null,
    inorganic_salt_kg: evaluation?.inorganic_salt_kg ?? null,
    protein_kg: evaluation?.protein_kg ?? null,
    body_water_kg: evaluation?.body_water_kg ?? null,
    lean_mass_kg: evaluation?.lean_mass_kg ?? null,
    muscle_mass_kg: evaluation?.muscle_mass_kg ?? null,
    skeletal_muscle_kg: evaluation?.skeletal_muscle_kg ?? null,
    body_water_percent: evaluation?.body_water_percent ?? null,
    visceral_fat_level: evaluation?.visceral_fat_level ?? null,
    bmi: evaluation?.bmi ?? null,
    basal_metabolic_rate_kcal: evaluation?.basal_metabolic_rate_kcal ?? null,
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

function warningTone(warning?: BodyCompositionOcrWarning): string {
  if (!warning) return "";
  return warning.severity === "critical" ? "border-lovable-danger focus:ring-lovable-danger/20" : "border-amber-400 focus:ring-amber-300/20";
}

function fieldSignalTextClass(tone: "success" | "warning" | "neutral"): string {
  if (tone === "success") return "text-emerald-700";
  if (tone === "warning") return "text-amber-800";
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

  function resetEditor(evaluation?: BodyCompositionEvaluation | null) {
    reset(buildDefaultValues(evaluation));
    setCurrentSource((evaluation?.source as EvaluationSource | undefined) ?? "manual");
    setReviewedManually(evaluation?.reviewed_manually ?? true);
    setOcrMetadata(buildOcrMetadata(evaluation));
    setOcrFile(null);
    setOcrResult(null);
    setOcrReadSession(EMPTY_OCR_READ_SESSION);
    setEditingEvaluationId(evaluation?.id ?? null);
  }

  const saveMutation = useMutation({
    mutationFn: (payload: BodyCompositionEvaluationCreate) => {
      if (editingEvaluationId) {
        return bodyCompositionService.update(memberId, editingEvaluationId, payload);
      }
      return bodyCompositionService.create(memberId, payload);
    },
    onSuccess: async (savedEvaluation) => {
      if (savedEvaluation.actuar_sync_status === "sync_pending") {
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
      resetEditor(null);
    },
    onError: () => toast.error("Erro ao salvar a bioimpedancia."),
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
        toast.success("Resumo do aluno e PDF enviados pelo WhatsApp.");
        return;
      }
      toast.error(payload.error_detail || "O envio por WhatsApp nao foi concluido.");
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Nao foi possivel enviar o resumo do aluno no WhatsApp.");
    },
  });

  const sendKommoMutation = useMutation({
    mutationFn: (evaluationId: string) => bodyCompositionService.sendKommoHandoff(memberId, evaluationId),
    onSuccess: (payload) => {
      if (payload.status === "sent") {
        toast.success("Handoff da bioimpedancia enviado para a Kommo.");
        return;
      }
      toast.error(payload.detail || "A Kommo nao recebeu o handoff desta bioimpedancia.");
    },
    onError: (error) => {
      if (error instanceof AxiosError && typeof error.response?.data?.detail === "string") {
        toast.error(error.response.data.detail);
        return;
      }
      toast.error("Nao foi possivel enviar esta bioimpedancia para a Kommo.");
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
      source: currentSource,
      reviewed_manually: currentSource === "manual" ? true : reviewedManually,
      raw_ocr_text: ocrMetadata.raw_ocr_text,
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
    const numericKeys = Object.keys(values).filter((key) => key !== "evaluation_date") as NumericFieldKey[];
    for (const key of numericKeys) {
      const value = values[key];
      if (typeof value === "number") {
        setValue(key, value);
      }
    }
    setValue("evaluation_date", values.evaluation_date ?? new Date().toISOString().split("T")[0]);
    setValue("ocr_source_file_ref", `local://${file.name}`);
    setCurrentSource("ocr_receipt");
    setReviewedManually(false);
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

      if (readOutcome.assistedUsed) {
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

  function onSubmit(data: FormData) {
    saveMutation.mutate(buildPayload(data));
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
              <MetricCard label="Gordura corporal" value={`${fmt(focusEvaluation.body_fat_kg, " kg")} / ${fmt(focusEvaluation.body_fat_percent, "%")}`} />
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
          </div>
          {automaticActuarSaveReady ? (
            <p className="mt-3 text-xs font-medium text-emerald-700">
              Estacao Actuar online. Ao salvar, esta avaliacao entra automaticamente no fluxo externo.
            </p>
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
                      ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                      : readCapability.tone === "warning"
                        ? "border-amber-200 bg-amber-50 text-amber-900"
                        : "border-lovable-border bg-lovable-surface text-lovable-ink"
                  }`}
                >
                  <p className="font-semibold">{readCapability.title}</p>
                  <p className="mt-1 text-xs">{readCapability.description}</p>
                </div>
                {ocrMetadata.ocr_warnings_json.length > 0 ? (
                  <div className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900">
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

              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="Data da avaliacao" error={errors.evaluation_date?.message} required>
                  <Input type="date" {...register("evaluation_date")} />
                </FormField>
                <FormField label="Referencia da imagem OCR" error={errors.ocr_source_file_ref?.message}>
                  <Input placeholder="local://arquivo.jpg" {...register("ocr_source_file_ref")} />
                </FormField>
              </div>

              {FORM_SECTIONS.map((section) => (
                <section key={section.title} className="space-y-3 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{section.title}</p>
                    <p className="text-xs text-lovable-ink-muted">{section.description}</p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    {section.fields.map((field) => {
                      const warning = highlightedWarnings.get(field.key);
                      const fieldSignal = resolveBodyCompositionFieldSignal({
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
                              {...register(field.key)}
                            />
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

              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="URL do laudo/arquivo" error={errors.report_file_url?.message}>
                  <Input placeholder="https://..." {...register("report_file_url")} />
                </FormField>
                <FormField label="Observacoes" error={errors.notes?.message}>
                  <Textarea rows={4} placeholder="Notas operacionais para o professor..." {...register("notes")} />
                </FormField>
              </div>

              <div className="flex flex-wrap justify-end gap-2">
                {editingEvaluationId ? (
                  <Button type="button" variant="ghost" onClick={handleNewEvaluation} disabled={saveMutation.isPending}>
                    <X size={14} />
                    Cancelar
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
                        {sendKommoMutation.isPending ? "Enviando..." : "Enviar para Kommo"}
                      </Button>
                    </div>
                    <div className="mt-3 space-y-1 text-xs text-lovable-ink-muted">
                      <p>
                        {memberPhone
                          ? `WhatsApp direto: envia este resumo e o PDF da bioimpedancia para o numero cadastrado${memberName ? ` de ${memberName}` : " do aluno"}.`
                          : "Cadastre o WhatsApp do aluno para enviar este resumo com PDF pelo canal direto."}
                      </p>
                      <p>
                        Kommo: cria um handoff operacional com resumo, alertas e link do exame no AI GYM OS para a equipe usar o numero oficial por la.
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
                <div className="rounded-2xl border border-lovable-danger/20 bg-red-50 px-4 py-3 text-sm text-red-800">
                  {getPermissionAwareMessage(null, "Nao foi possivel carregar o status de sync do Actuar.")}
                </div>
              ) : (
                <>
                  <div
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      actuarCapability.tone === "success"
                        ? "border-emerald-200 bg-emerald-50 text-emerald-800"
                        : actuarCapability.tone === "warning"
                          ? "border-amber-200 bg-amber-50 text-amber-900"
                          : "border-lovable-border bg-lovable-surface text-lovable-ink"
                    }`}
                  >
                    <p className="font-semibold">{actuarCapability.title}</p>
                    <p className="mt-1 text-xs">{actuarCapability.description}</p>
                  </div>
                  <div
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      syncStatus?.training_ready ? "border-emerald-200 bg-emerald-50 text-emerald-800" : "border-amber-200 bg-amber-50 text-amber-900"
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
                    <div className="rounded-xl border border-lovable-danger/20 bg-red-50 px-3 py-2 text-sm text-red-800">
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
                        <p className="font-semibold">Campos mantidos apenas no AI GYM OS</p>
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
                  <Button type="button" size="sm" variant="secondary" onClick={() => handleEditEvaluation(evaluation)}>
                    <Pencil size={14} />
                    Editar
                  </Button>
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

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
      <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">{label}</p>
      <p className="mt-1 text-lg font-semibold text-lovable-ink">{value}</p>
    </article>
  );
}

function StatusPill({ children, tone }: { children: ReactNode; tone: "success" | "warning" | "neutral" }) {
  const className =
    tone === "success"
      ? "border-emerald-200 bg-emerald-50 text-emerald-700"
      : tone === "warning"
        ? "border-amber-200 bg-amber-50 text-amber-800"
        : "border-lovable-border bg-lovable-surface text-lovable-ink";

  return <span className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-semibold ${className}`}>{children}</span>;
}
