import { describe, expect, it } from "vitest";

import type { BodyCompositionActuarSyncStatus } from "../types";
import type { BodyCompositionOcrResult } from "../services/bodyCompositionOcr";
import {
  buildUnsupportedFieldsMessage,
  resolveActuarCapability,
  resolveReadCapability,
  syncModeLabel,
} from "../components/assessments/bodyCompositionCapability";

function makeOcrResult(overrides?: Partial<BodyCompositionOcrResult>): BodyCompositionOcrResult {
  return {
    device_profile: "tezewa_receipt_v1",
    values: {
      weight_kg: 84.5,
      body_fat_kg: 19.46,
      body_fat_percent: 23.0,
      waist_hip_ratio: 0.88,
    },
    ranges: {},
    warnings: [],
    confidence: 0.92,
    raw_text: "Weight 84.5",
    needs_review: false,
    engine: "local",
    fallback_used: false,
    ...overrides,
  };
}

function makeSyncStatus(overrides?: Partial<BodyCompositionActuarSyncStatus>): BodyCompositionActuarSyncStatus {
  return {
    evaluation_id: "evaluation-1",
    member_id: "member-1",
    sync_mode: "assisted_rpa",
    sync_status: "saved",
    training_ready: false,
    sync_required_for_training: true,
    external_id: null,
    last_synced_at: null,
    last_attempt_at: null,
    last_error_code: null,
    last_error: null,
    can_retry: true,
    critical_fields: [],
    unsupported_fields: [],
    fallback_manual_summary: {
      evaluation_id: "evaluation-1",
      member_id: "member-1",
      sync_status: "saved",
      training_ready: false,
      critical_fields: [],
      summary_text: "manual",
    },
    current_job: null,
    attempts: [],
    member_link: null,
    ...overrides,
  };
}

describe("bodyCompositionCapability helpers", () => {
  it("marks assisted read as disabled when AI warning is present", () => {
    const capability = resolveReadCapability({
      currentSource: "ocr_receipt",
      ocrResult: makeOcrResult({
        warnings: [{ field: "weight_kg", message: "Leitura assistida por IA indisponivel; mantivemos a leitura local com revisao manual obrigatoria.", severity: "warning" }],
      }),
      storedWarnings: [],
      assistedAttempted: true,
      assistedError: null,
    });

    expect(capability.title).toBe("Leitura assistida desligada no ambiente");
    expect(capability.tone).toBe("warning");
  });

  it("describes pure AI assisted read without fallback wording", () => {
    const capability = resolveReadCapability({
      currentSource: "ocr_receipt",
      ocrResult: makeOcrResult({
        engine: "ai_assisted",
        fallback_used: false,
      }),
      storedWarnings: [],
      assistedAttempted: true,
      assistedError: null,
    });

    expect(capability.title).toBe("Leitura assistida por IA ativa");
    expect(capability.description).toContain("diretamente pela IA assistida");
    expect(capability.tone).toBe("success");
  });

  it("describes disabled Actuar sync as outside environment scope", () => {
    const capability = resolveActuarCapability(makeSyncStatus({ sync_mode: "disabled", sync_status: "saved" }));

    expect(capability.title).toBe("Actuar fora do escopo deste ambiente");
    expect(capability.tone).toBe("warning");
  });

  it("builds a summary message for unsupported Actuar fields", () => {
    const message = buildUnsupportedFieldsMessage(
      makeSyncStatus({
        unsupported_fields: [
          { field: "bmr_kcal", actuar_field: "bmr_kcal", classification: "unsupported", supported: false, required: false, value: 1880 },
          { field: "visceral_fat", actuar_field: "visceral_fat", classification: "unsupported", supported: false, required: false, value: 9 },
        ],
      }),
    );

    expect(message).toContain("2 campos");
  });

  it("returns user friendly labels for sync modes", () => {
    expect(syncModeLabel("assisted_rpa")).toBe("RPA assistido");
    expect(syncModeLabel("disabled")).toBe("Desligado");
  });
});
