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
  "body_fat_bioimpedance_percent",
  "body_fat_anthropometric_percent",
  "body_fat_manual_override_percent",
  "body_fat_used_percent",
  "body_fat_range_min",
  "body_fat_range_max",
  "fat_mass_estimated_kg",
  "lean_mass_estimated_kg",
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
  "neck_cm",
  "shoulders_cm",
  "chest_cm",
  "waist_cm",
  "abdomen_cm",
  "hip_cm",
  "iliac_cm",
  "right_arm_relaxed_cm",
  "left_arm_relaxed_cm",
  "right_arm_flexed_cm",
  "left_arm_flexed_cm",
  "right_thigh_cm",
  "left_thigh_cm",
  "right_calf_cm",
  "left_calf_cm",
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

function isPdfBlob(blob: Blob): boolean {
  if (blob.size === 0) return false;
  return !blob.type || blob.type.toLowerCase().includes("pdf");
}

function openBlobInPopup(targetWindow: Window, url: string): boolean {
  try {
    if (targetWindow.closed) return false;
    if (typeof targetWindow.location.replace === "function") {
      targetWindow.location.replace(url);
    } else {
      targetWindow.location.href = url;
    }
    targetWindow.focus?.();
    return true;
  } catch {
    return false;
  }
}

function writePdfWindowMessage(targetWindow: Window | null | undefined, title: string, message: string): void {
  if (!targetWindow) return;
  try {
    targetWindow.document.title = title;
    targetWindow.document.body.innerHTML = `
      <main style="min-height:100vh;display:flex;align-items:center;justify-content:center;margin:0;background:#0a0b0f;color:#f8fafc;font-family:Inter,Arial,sans-serif;">
        <section style="width:min(420px,calc(100vw - 32px));border:1px solid rgba(255,255,255,.14);border-radius:18px;background:#101320;padding:28px;box-shadow:0 24px 60px rgba(0,0,0,.28);">
          <p style="margin:0 0 8px;color:#60a5fa;font-size:12px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;">Cordex Gym OS</p>
          <h1 style="margin:0 0 10px;font-size:22px;line-height:1.2;">${title}</h1>
          <p style="margin:0;color:#aab4c3;font-size:14px;line-height:1.55;">${message}</p>
        </section>
      </main>
    `;
  } catch {
    // Browser may block document writes after navigation. The PDF flow can continue.
  }
}

export type BodyCompositionPdfKind = "summary" | "technical";
export interface BodyCompositionSaveOptions {
  syncActuar?: boolean;
}

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

  async delete(memberId: string, evaluationId: string): Promise<void> {
    await api.delete(`/api/v1/members/${memberId}/body-composition/${evaluationId}`);
  },

  async create(
    memberId: string,
    payload: BodyCompositionEvaluationCreate,
    options?: BodyCompositionSaveOptions,
  ): Promise<BodyCompositionEvaluation> {
    const { data } = await api.post<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition`,
      payload,
      { params: { sync_actuar: options?.syncActuar ?? true } },
    );
    return normalizeBodyComposition(data);
  },

  async update(
    memberId: string,
    evaluationId: string,
    payload: BodyCompositionEvaluationUpdate,
    options?: BodyCompositionSaveOptions,
  ): Promise<BodyCompositionEvaluation> {
    const { data } = await api.put<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}`,
      payload,
      { params: { sync_actuar: options?.syncActuar ?? true } },
    );
    return normalizeBodyComposition(data);
  },

  async review(
    memberId: string,
    evaluationId: string,
    payload: BodyCompositionEvaluationReviewInput,
    options?: BodyCompositionSaveOptions,
  ): Promise<BodyCompositionEvaluation> {
    const { data } = await api.post<BodyCompositionEvaluation>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/review`,
      payload,
      { params: { sync_actuar: options?.syncActuar ?? true } },
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

  async prepareKommoHandoff(memberId: string, evaluationId: string): Promise<BodyCompositionKommoDispatch> {
    const { data } = await api.post<BodyCompositionKommoDispatch>(
      `/api/v1/members/${memberId}/body-composition/${evaluationId}/prepare-kommo`,
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
      headers: { Accept: "application/pdf" },
      responseType: "blob",
      params: { ts: Date.now() },
      timeout: 90_000,
    });

    if (!isPdfBlob(response.data)) {
      throw new Error("O servidor nao retornou um PDF valido.");
    }

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
    const targetWindow = popup ?? window.open("", "_blank");

    if (targetWindow) {
      try {
        targetWindow.opener = null;
      } catch {
        // noop
      }
      writePdfWindowMessage(
        targetWindow,
        "Gerando PDF",
        "Estamos montando o relatorio completo. A primeira geracao pode levar alguns segundos.",
      );
    }

    try {
      const { blob, filename } = await this.fetchPdf(memberId, evaluationId, kind);
      const url = window.URL.createObjectURL(blob);

      if (targetWindow && openBlobInPopup(targetWindow, url)) {
        // Keep the object URL alive while the browser PDF viewer initializes.
        window.setTimeout(() => window.URL.revokeObjectURL(url), 15 * 60_000);
        return;
      }

      triggerBrowserDownload(blob, filename);
    } catch (error) {
      writePdfWindowMessage(
        targetWindow,
        "Nao foi possivel gerar o PDF",
        "O backend nao retornou o arquivo dentro do tempo esperado. Volte para o Cordex e tente novamente.",
      );
      throw error;
    }
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
      const assistedUsed = assistedResult.engine !== "local" || Boolean(assistedResult.fallback_used);
      const assistedWarning = assistedResult.warnings.find(
        (warning) => warning.field == null && warning.message.toLowerCase().includes("leitura assistida"),
      );
      return {
        localResult,
        result: assistedResult,
        fallbackReasons,
        assistedAttempted: true,
        assistedUsed,
        assistedError: assistedUsed ? null : assistedWarning?.message ?? null,
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
