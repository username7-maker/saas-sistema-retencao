import type {
  ActuarSyncMode,
  ActuarSyncStatus,
  BodyCompositionActuarSyncStatus,
  BodyCompositionOcrWarning,
  EvaluationSource,
} from "../../types";
import type { BodyCompositionOcrEngine, BodyCompositionOcrResult } from "../../services/bodyCompositionOcr";

export type CapabilityTone = "success" | "warning" | "neutral";

export interface CapabilityBanner {
  tone: CapabilityTone;
  title: string;
  description: string;
}

interface ReadCapabilityInput {
  currentSource: EvaluationSource;
  ocrResult: BodyCompositionOcrResult | null;
  storedWarnings: BodyCompositionOcrWarning[];
  assistedAttempted: boolean;
  assistedError: string | null;
}

function hasAiUnavailableWarning(warnings: BodyCompositionOcrWarning[]): boolean {
  return warnings.some((warning) => warning.message.includes("Leitura assistida por IA indisponivel"));
}

function hasCriticalWarnings(warnings: BodyCompositionOcrWarning[]): boolean {
  return warnings.some((warning) => warning.severity === "critical");
}

export function syncModeLabel(mode: ActuarSyncMode | string | null | undefined): string {
  if (mode === "disabled") return "Desligado";
  if (mode === "http_api") return "API direta";
  if (mode === "csv_export") return "Exportacao CSV";
  if (mode === "assisted_rpa") return "RPA assistido";
  if (mode === "local_bridge") return "Ponte local";
  return "Nao configurado";
}

export function resolveReadCapability(input: ReadCapabilityInput): CapabilityBanner {
  const warnings = input.ocrResult?.warnings ?? input.storedWarnings;
  const engine = input.ocrResult?.engine ?? null;

  if (input.currentSource === "manual" && !input.ocrResult) {
    return {
      tone: "neutral",
      title: "Fluxo manual",
      description: "Neste momento a avaliacao esta em preenchimento manual, sem leitura automatica da imagem.",
    };
  }

  if (input.assistedAttempted && hasAiUnavailableWarning(warnings)) {
    return {
      tone: "warning",
      title: "Leitura assistida desligada no ambiente",
      description: "O piloto manteve o OCR local e exige revisao manual antes de salvar a bioimpedancia.",
    };
  }

  if (engine === "hybrid") {
    return {
      tone: "success",
      title: "Leitura hibrida ativa",
      description: "O OCR local encontrou ambiguidades e a leitura assistida ajudou a cobrir os campos do exame para revisao final.",
    };
  }

  if (engine === "ai_assisted") {
    return {
      tone: "success",
      title: "Leitura assistida por IA ativa",
      description: "A leitura foi interpretada diretamente pela IA assistida e trouxe os campos reconhecidos do exame para revisao final.",
    };
  }

  if (engine === "ai_fallback") {
    return {
      tone: "success",
      title: "Leitura assistida por IA ativa",
      description: "A leitura assistida prevaleceu nos campos do exame, mas os destaques ainda devem ser revisados antes do salvamento.",
    };
  }

  if (engine === "local" && input.assistedAttempted) {
    return {
      tone: "warning",
      title: "OCR local mantido com revisao manual",
      description: input.assistedError
        ? `A tentativa assistida falhou (${input.assistedError}) e o piloto manteve o OCR local para conferencia humana.`
        : "O piloto manteve o OCR local nesta execucao e espera revisao manual antes de salvar.",
    };
  }

  if (engine === "local" || input.currentSource === "ocr_receipt") {
    return {
      tone: hasCriticalWarnings(warnings) ? "warning" : "neutral",
      title: "OCR local com conferencia humana",
      description: hasCriticalWarnings(warnings)
        ? "A imagem foi lida localmente, mas ha campos sensiveis que exigem revisao manual."
        : "A imagem foi lida localmente. Revise o preenchimento antes de salvar.",
    };
  }

  return {
    tone: "neutral",
    title: "Fluxo de leitura ainda nao iniciado",
    description: "Envie a imagem para leitura automatica ou mantenha o preenchimento manual desta avaliacao.",
  };
}

export function resolveActuarCapability(syncStatus: BodyCompositionActuarSyncStatus | null | undefined): CapabilityBanner {
  if (!syncStatus || syncStatus.sync_mode === "disabled") {
    return {
      tone: "warning",
      title: "Actuar fora do escopo deste ambiente",
      description: "A avaliacao fica valida dentro do AI GYM OS e o resumo manual pode apoiar o lancamento externo quando necessario.",
    };
  }

  if (syncStatus.sync_mode === "csv_export" && (syncStatus.sync_status === "manual_sync_required" || syncStatus.sync_status === "needs_review")) {
    return {
      tone: "warning",
      title: "Exportacao CSV pronta",
      description:
        "Geramos a exportacao para apoio manual no Actuar. Esse e o metodo mais seguro quando o professor ja esta com o Actuar aberto em outra aba: lance externamente e confirme o sync so depois da conclusao.",
    };
  }

  if (syncStatus.sync_mode === "local_bridge" && (syncStatus.sync_status === "sync_pending" || syncStatus.sync_status === "syncing")) {
    return {
      tone: "neutral",
      title: "Ponte local em andamento",
      description:
        "A bioimpedancia foi entregue para a estacao local do Actuar. Aguarde o retorno da ponte antes de repetir o lancamento manual.",
    };
  }

  if (syncStatus.sync_mode === "local_bridge" && (syncStatus.sync_status === "manual_sync_required" || syncStatus.sync_status === "needs_review")) {
    return {
      tone: "warning",
      title: "Ponte local precisa de revisao",
      description:
        "A estacao local nao concluiu o sync no Actuar. Revise a estacao, a aba aberta do Actuar e siga pelo fallback manual assistido se necessario.",
    };
  }

  if (syncStatus.sync_status === "synced_to_actuar") {
    return {
      tone: "success",
      title: "Sincronizacao concluida",
      description: "Os campos criticos foram enviados com sucesso e a avaliacao esta pronta para uso no Actuar.",
    };
  }

  if (syncStatus.sync_status === "manual_sync_required" || syncStatus.sync_status === "needs_review") {
    return {
      tone: "warning",
      title: "Fluxo manual assistido",
      description:
        "O piloto nao concluiu o envio automatico. Use o resumo manual no Actuar aberto pelo operador e confirme o sync apenas depois do lancamento externo.",
    };
  }

  if (syncStatus.sync_status === "sync_failed") {
    return {
      tone: "warning",
      title: "Sync automatico falhou",
      description: "A automacao nao concluiu nesta tentativa. Revise o erro, reprocessse se fizer sentido ou siga pelo fallback manual assistido.",
    };
  }

  if (syncStatus.sync_status === "sync_pending" || syncStatus.sync_status === "syncing") {
    return {
      tone: "neutral",
      title: "Sync automatico em andamento",
      description:
        "Os campos criticos ja estao em processamento no worker. Essa tentativa nao usa a aba do operador; evite lancamento duplicado antes do retorno final.",
    };
  }

  if (syncStatus.sync_status === "saved") {
    return {
      tone: "neutral",
      title: "Pronta para envio ao Actuar",
      description: "A avaliacao foi salva localmente e ainda nao passou pelo envio automatico. O proximo passo e sincronizar ou usar o resumo manual.",
    };
  }

  return {
    tone: syncStatus.training_ready ? "success" : "warning",
    title: syncStatus.training_ready ? "Pronta para treino no Actuar" : "Avaliacao ainda depende de acao externa",
    description: syncStatus.training_ready
      ? "Os campos criticos ja estao consistentes para uso no fluxo de treino."
      : "Os campos criticos ainda nao fecharam no fluxo externo e exigem atencao antes do treino no Actuar.",
  };
}

export function buildUnsupportedFieldsMessage(
  syncStatus: Pick<BodyCompositionActuarSyncStatus, "unsupported_fields"> | null | undefined,
): string | null {
  const total = syncStatus?.unsupported_fields?.length ?? 0;
  if (!total) return null;
  return total === 1
    ? "1 campo permanece apenas no AI GYM OS porque ainda nao tem destino suportado no Actuar."
    : `${total} campos permanecem apenas no AI GYM OS porque ainda nao tem destino suportado no Actuar.`;
}

export function statusPillToneForSync(syncStatus: ActuarSyncStatus | null | undefined): CapabilityTone {
  if (syncStatus === "synced_to_actuar") return "success";
  if (syncStatus === "manual_sync_required" || syncStatus === "needs_review" || syncStatus === "sync_failed") return "warning";
  return "neutral";
}

export function statusPillToneForEngine(engine: BodyCompositionOcrEngine | null): CapabilityTone {
  if (engine === "ai_assisted" || engine === "ai_fallback" || engine === "hybrid") return "success";
  return "neutral";
}
