import type {
  ActuarMemberLink,
  BodyCompositionActuarSyncStatus,
  BodyCompositionKommoDispatch,
  BodyCompositionEvaluation,
  BodyCompositionEvaluationCreate,
  BodyCompositionEvaluationReviewInput,
  BodyCompositionManualSyncSummary,
  BodyCompositionReport,
  BodyCompositionWhatsAppDispatch,
  BodyCompositionEvaluationUpdate,
} from "../types";
import { api } from "./api";
import {
  BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE,
  ensureOcrResultMetadata,
  getBodyCompositionAiFallbackReasons,
  readBodyCompositionFromImage,
  type BodyCompositionDeviceProfile,
  type BodyCompositionOcrResult,
} from "./bodyCompositionOcr";

const NUMERIC_FIELDS = [
  "weight_kg",
  "height_cm",
  "body_fat_kg",
  "body_fat_percent",
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
  "physical_age",
  "health_score",
  "parsing_confidence",
] as const;

function toNullableNumber(value: unknown): number | null {
  if (value == null || value === "") return null;
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : null;
}

function normalizeBodyComposition(payload: BodyCompositionEvaluation): BodyCompositionEvaluation {
  const normalized = { ...payload } as BodyCompositionEvaluation;
  for (const key of NUMERIC_FIELDS) {
    normalized[key] = toNullableNumber(payload[key]) as never;
  }
  return normalized;
}

function stripLocalOcrTransportMetadata(result: BodyCompositionOcrResult): Omit<BodyCompositionOcrResult, "engine" | "fallback_used"> {
  const { engine: _engine, fallback_used: _fallbackUsed, ...payload } = ensureOcrResultMetadata(result);
  return payload;
}

function parseFilename(contentDisposition?: string, fallback = "bioimpedancia.pdf"): string {
  if (!contentDisposition) return fallback;
  const match = /filename="?([^"]+)"?/i.exec(contentDisposition);
  return match?.[1] ?? fallback;
}

function triggerBrowserDownload(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export type BodyCompositionPdfKind = "summary" | "technical";

export interface BodyCompositionAssistedReadResult {
  localResult: BodyCompositionOcrResult | null;
  result: BodyCompositionOcrResult;
  fallbackReasons: string[];
  assistedAttempted: boolean;
  assistedUsed: boolean;
  assistedError: string | null;
}

export const bodyCompositionService = {
  async list(memberId: string, limit = 20): Promise<BodyCompositionEvaluation[]> {
    const { data } = await api.get<BodyCompositionEvaluation[]>(
      `/api/v1/members/${memberId}/body-composition`,
      { params: { limit } },
    );
    return data.map(normalizeBodyComposition);
  },

  async get(memberId: string, evaluationId: string): Promise<BodyCompositionEvaluation> {
    const { data } = await api.get<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}`,
    );
    return normalizeBodyComposition(data);
  },

  async create(
    memberId: string,
    payload: BodyCompositionEvaluationCreate,
  ): Promise<BodyCompositionEvaluation> {
    const { data } = await api.post<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition`,
      payload,
    );
    return normalizeBodyComposition(data);
  },

  async update(
    memberId: string,
    evaluationId: string,
    payload: BodyCompositionEvaluationUpdate,
  ): Promise<BodyCompositionEvaluation> {
    const { data } = await api.put<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}`,
      payload,
    );
    return normalizeBodyComposition(data);
  },

  async review(
    memberId: string,
    evaluationId: string,
    payload: BodyCompositionEvaluationReviewInput,
  ): Promise<BodyCompositionEvaluation> {
    const { data } = await api.post<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/review`,
      payload,
    );
    return normalizeBodyComposition(data);
  },

  async getActuarSyncStatus(memberId: string, evaluationId: string): Promise<BodyCompositionActuarSyncStatus> {
    const { data } = await api.get<BodyCompositionActuarSyncStatus>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/actuar-sync-status`,
    );
    return data;
  },

  async retryActuarSync(memberId: string, evaluationId: string): Promise<BodyCompositionActuarSyncStatus> {
    const { data } = await api.post<BodyCompositionActuarSyncStatus>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/retry-actuar-sync`,
    );
    return data;
  },

  async enqueueActuarSync(memberId: string, evaluationId: string): Promise<BodyCompositionActuarSyncStatus> {
    const { data } = await api.post<BodyCompositionActuarSyncStatus>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/actuar-sync`,
    );
    return data;
  },

  async getManualSyncSummary(memberId: string, evaluationId: string): Promise<BodyCompositionManualSyncSummary> {
    const { data } = await api.get<BodyCompositionManualSyncSummary>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/manual-sync-summary`,
    );
    return data;
  },

  async confirmManualSync(
    memberId: string,
    evaluationId: string,
    payload: { reason: string; note?: string | null },
  ): Promise<BodyCompositionActuarSyncStatus> {
    const { data } = await api.post<BodyCompositionActuarSyncStatus>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/manual-sync-confirm`,
      payload,
    );
    return data;
  },

  async sendWhatsAppSummary(memberId: string, evaluationId: string): Promise<BodyCompositionWhatsAppDispatch> {
    const { data } = await api.post<BodyCompositionWhatsAppDispatch>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/send-whatsapp`,
    );
    return data;
  },

  async sendKommoHandoff(memberId: string, evaluationId: string): Promise<BodyCompositionKommoDispatch> {
    const { data } = await api.post<BodyCompositionKommoDispatch>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/send-kommo`,
    );
    return data;
  },

  async upsertActuarLink(
    memberId: string,
    payload: {
      actuar_external_id?: string | null;
      actuar_search_name?: string | null;
      actuar_search_document?: string | null;
      actuar_search_birthdate?: string | null;
      match_confidence?: number | null;
    },
  ): Promise<ActuarMemberLink> {
    const { data } = await api.put<ActuarMemberLink>(`/api/v1/members/${memberId}/actuar-link`, payload);
    return data;
  },

  async parseImage(
    memberId: string,
    file: File,
    localOcrResult?: BodyCompositionOcrResult | null,
    deviceProfile: BodyCompositionDeviceProfile = BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE,
  ): Promise<BodyCompositionOcrResult> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("device_profile", deviceProfile);
    if (localOcrResult) {
      formData.append("local_ocr_result", JSON.stringify(stripLocalOcrTransportMetadata(localOcrResult)));
    }

    const { data } = await api.post<BodyCompositionOcrResult>(
      `/api/v1/members/${memberId}/body-composition/parse-image`,
      formData,
    );
    return ensureOcrResultMetadata(data, data.engine ?? "local", Boolean(data.fallback_used));
  },

  async parseOcr(
    memberId: string,
    file: File,
    localOcrResult?: BodyCompositionOcrResult | null,
    deviceProfile: BodyCompositionDeviceProfile = BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE,
  ): Promise<BodyCompositionOcrResult> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("device_profile", deviceProfile);
    if (localOcrResult) {
      formData.append("local_ocr_result", JSON.stringify(stripLocalOcrTransportMetadata(localOcrResult)));
    }

    const { data } = await api.post<BodyCompositionOcrResult>(
      `/api/v1/members/${memberId}/body-composition/parse-ocr`,
      formData,
    );
    return ensureOcrResultMetadata(data, data.engine ?? "local", Boolean(data.fallback_used));
  },

  async getReport(memberId: string, evaluationId: string): Promise<BodyCompositionReport> {
    const { data } = await api.get<BodyCompositionReport>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/report`,
    );
    return data;
  },

  async fetchPdf(
    memberId: string,
    evaluationId: string,
    kind: BodyCompositionPdfKind,
  ): Promise<{ blob: Blob; filename: string }> {
    const path = kind === "technical" ? "technical-pdf" : "pdf";
    const response = await api.get<Blob>(`/api/v1/members/${memberId}/body-composition/${evaluationId}/${path}`, {
      responseType: "blob",
      params: { ts: Date.now() },
    });

    return {
      blob: response.data,
      filename: parseFilename(
        response.headers["content-disposition"],
        kind === "technical" ? "relatorio-tecnico-bioimpedancia.pdf" : "resumo-aluno-bioimpedancia.pdf",
      ),
    };
  },

  async openPdf(
    memberId: string,
    evaluationId: string,
    kind: BodyCompositionPdfKind,
    popup?: Window | null,
  ): Promise<void> {
    const { blob, filename } = await this.fetchPdf(memberId, evaluationId, kind);
    const url = window.URL.createObjectURL(blob);
    const targetWindow = popup ?? window.open("", "_blank");

    if (targetWindow) {
      try {
        targetWindow.opener = null;
      } catch {
        // noop
      }
      targetWindow.location.href = url;
      window.setTimeout(() => window.URL.revokeObjectURL(url), 60_000);
      return;
    }

    triggerBrowserDownload(blob, filename);
  },

  async readWithAssistedFallback(
    memberId: string,
    file: File,
    options?: {
      deviceProfile?: BodyCompositionDeviceProfile;
      forceAssisted?: boolean;
    },
  ): Promise<BodyCompositionAssistedReadResult> {
    const deviceProfile = options?.deviceProfile ?? BODY_COMPOSITION_DEFAULT_DEVICE_PROFILE;
    const forceAssisted = Boolean(options?.forceAssisted);
    let localResult: BodyCompositionOcrResult | null = null;
    let fallbackReasons: string[] = [];
    let localOcrError: Error | null = null;

    try {
      localResult = ensureOcrResultMetadata(await readBodyCompositionFromImage(file, deviceProfile), "local", false);
      fallbackReasons = getBodyCompositionAiFallbackReasons(localResult);
    } catch (error) {
      localOcrError = error instanceof Error ? error : new Error("Falha ao carregar imagem para OCR");
      if (!forceAssisted) {
        throw localOcrError;
      }
      fallbackReasons = ["OCR local falhou antes da leitura assistida."];
    }

    const shouldAttemptAssisted = forceAssisted || fallbackReasons.length > 0;

    if (!shouldAttemptAssisted && localResult) {
      return {
        localResult,
        result: localResult,
        fallbackReasons,
        assistedAttempted: false,
        assistedUsed: false,
        assistedError: null,
      };
    }

    try {
      const assistedResult = await bodyCompositionService.parseImage(memberId, file, localResult, deviceProfile);
      return {
        localResult,
        result: assistedResult,
        fallbackReasons,
        assistedAttempted: true,
        assistedUsed: assistedResult.engine !== "local" || Boolean(assistedResult.fallback_used),
        assistedError: null,
      };
    } catch (error) {
      const message = error instanceof Error ? error.message : "Leitura assistida indisponivel no momento.";
      if (!localResult) {
        if (localOcrError && localOcrError.message !== message) {
          throw new Error(`${message} OCR local tambem falhou: ${localOcrError.message}`);
        }
        throw new Error(localOcrError?.message ?? message);
      }
      return {
        localResult,
        result: localResult,
        fallbackReasons,
        assistedAttempted: true,
        assistedUsed: false,
        assistedError: message,
      };
    }
  },
};
