import type {
  BodyCompositionActuarSyncStatus,
  BodyCompositionEvaluation,
  BodyCompositionEvaluationCreate,
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

export interface BodyCompositionAssistedReadResult {
  localResult: BodyCompositionOcrResult;
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
    const localResult = ensureOcrResultMetadata(await readBodyCompositionFromImage(file, deviceProfile), "local", false);
    const fallbackReasons = getBodyCompositionAiFallbackReasons(localResult);
    const shouldAttemptAssisted = forceAssisted || fallbackReasons.length > 0;

    if (!shouldAttemptAssisted) {
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
