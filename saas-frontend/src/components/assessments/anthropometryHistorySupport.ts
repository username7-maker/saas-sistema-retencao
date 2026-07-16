import type { Assessment } from "../../services/assessmentService";
import type { AIAssistantPayload } from "../../types";

type JsonRecord = Record<string, unknown>;

const PERIMETRY_LABELS: Record<string, string> = {
  waist_cm: "Cintura",
  hip_cm: "Quadril",
  shoulders_cm: "Ombros",
  chest_cm: "Torax",
  right_arm_relaxed_cm: "Braco direito relaxado",
  left_arm_relaxed_cm: "Braco esquerdo relaxado",
  right_arm_flexed_cm: "Braco direito contraido",
  left_arm_flexed_cm: "Braco esquerdo contraido",
  right_thigh_cm: "Coxa direita",
  left_thigh_cm: "Coxa esquerda",
  right_calf_cm: "Panturrilha direita",
  left_calf_cm: "Panturrilha esquerda",
};

export function isManualAnthropometryAssessment(assessment: Assessment): boolean {
  return assessment.assessment_method === "manual_anthropometry";
}

export function getAnthropometryProtocolDisplay(assessment: Assessment): string {
  const snapshotProtocol = asRecord(assessment.anthropometry_snapshot_json?.protocol);
  const label = readString(snapshotProtocol, "label");
  if (label) return label;
  return assessment.measurement_protocol || "Protocolo antropometrico";
}

export function buildAnthropometryCoachSummary(assessment: Assessment, memberName?: string | null): string {
  const firstName = firstNameOf(memberName);
  const pieces = [
    `${firstName} registrou avaliacao antropometrica com peso de ${formatMetric(assessment.weight_kg, " kg")}`,
    `percentual de gordura estimado em ${formatMetric(assessment.body_fat_pct, "%")}`,
    `IMC ${formatMetric(assessment.bmi)}`,
  ];
  if (assessment.fat_mass_kg != null) pieces.push(`massa de gordura ${formatMetric(assessment.fat_mass_kg, " kg")}`);
  if (assessment.lean_mass_kg != null) pieces.push(`massa livre de gordura ${formatMetric(assessment.lean_mass_kg, " kg")}`);
  if (assessment.waist_hip_ratio != null) pieces.push(`RCQ ${formatMetric(assessment.waist_hip_ratio)}`);

  return `${pieces.join(", ")}. Massa muscular, agua corporal, gordura visceral e idade metabolica permanecem indisponiveis nesta modalidade. Compare a evolucao usando o mesmo protocolo sempre que possivel.`;
}

export function buildAnthropometryMemberSummary(assessment: Assessment, memberName?: string | null): string {
  const firstName = firstNameOf(memberName);
  const bodyFatText = assessment.body_fat_pct == null ? "com gordura corporal estimada pela antropometria" : `com gordura corporal estimada em ${formatMetric(assessment.body_fat_pct, "%")}`;
  const bmiText = assessment.bmi == null ? "" : ` e IMC ${formatMetric(assessment.bmi)}`;
  return `${firstName}, sua avaliacao antropometrica foi registrada ${bodyFatText}${bmiText}. Vamos acompanhar peso, medidas e percentual de gordura nas proximas semanas, sempre comparando pelo mesmo metodo para manter a leitura justa.`;
}

export function buildAnthropometryAssistantPayload(
  assessment: Assessment,
  memberId: string,
  memberName?: string | null,
): AIAssistantPayload {
  const protocol = getAnthropometryProtocolDisplay(assessment);
  const evidence = buildAnthropometryEvidence(assessment);
  const focus = resolveAnthropometryFocus(assessment);
  return {
    summary: `Antropometria com foco em ${focus}.`,
    why_it_matters:
      "Esta leitura usa dobras e perimetros para acompanhar composicao corporal, sem inventar metricas exclusivas da bioimpedancia.",
    next_best_action: buildAnthropometryNextAction(assessment),
    suggested_message: buildAnthropometryMemberSummary(assessment, memberName),
    evidence,
    provider: "system",
    mode: "rule_based",
    fallback_used: false,
    manual_required: true,
    confidence_label: "Leitura antropometrica",
    recommended_channel: "Copiar mensagem",
    cta_target: `/assessments/members/${memberId}?tab=registro`,
    cta_label: "Ajustar plano",
    prompt_key: "anthropometry_support_v1",
    prompt_version: "1.0.0",
    model: "rules-anthropometry-v1",
    safety_profile: "anthropometry_no_bioimpedance_invention",
    message_source: "anthropometry_local_support",
    blocked_reasons: [],
  };

  function buildAnthropometryEvidence(input: Assessment): string[] {
    const output = [
      `Protocolo: ${protocol}`,
      `Peso: ${formatMetric(input.weight_kg, " kg")}`,
      `Gordura corporal: ${formatMetric(input.body_fat_pct, "%")}`,
      `IMC: ${formatMetric(input.bmi)}`,
    ];
    if (input.fat_mass_kg != null) output.push(`Massa de gordura: ${formatMetric(input.fat_mass_kg, " kg")}`);
    if (input.lean_mass_kg != null) output.push(`Massa livre de gordura: ${formatMetric(input.lean_mass_kg, " kg")}`);
    if (input.waist_hip_ratio != null) output.push(`Relacao cintura-quadril: ${formatMetric(input.waist_hip_ratio)}`);
    output.push("Massa muscular indisponivel nesta modalidade.");
    return output;
  }
}

export function buildAnthropometryPerimetryEvidence(assessment: Assessment): string[] {
  const extraData = asRecord(assessment.extra_data);
  const perimetry = asRecord(extraData?.perimetry_evolution);
  const snapshotMeasurements = asRecord(assessment.anthropometry_snapshot_json?.measurements);
  const output: string[] = [];

  for (const [field, label] of Object.entries(PERIMETRY_LABELS)) {
    const value = readString(perimetry, field) ?? readMeasurementValue(snapshotMeasurements, field);
    if (value) output.push(`${label}: ${value} cm`);
  }

  return output;
}

function buildAnthropometryNextAction(assessment: Assessment): string {
  const bodyFat = assessment.body_fat_pct;
  const bmi = assessment.bmi;
  if ((bodyFat != null && bodyFat >= 25) || (bmi != null && bmi >= 30)) {
    return "Usar o resultado para ajustar o plano com foco inicial em reducao de gordura e reavaliar medidas no mesmo protocolo.";
  }
  if (bodyFat != null && bodyFat <= 12) {
    return "Acompanhar manutencao de massa livre e evitar reducao agressiva de peso sem necessidade tecnica.";
  }
  return "Manter acompanhamento de peso, perimetros e percentual de gordura, repetindo o mesmo protocolo na proxima avaliacao.";
}

function resolveAnthropometryFocus(assessment: Assessment): string {
  const bodyFat = assessment.body_fat_pct;
  const bmi = assessment.bmi;
  if ((bodyFat != null && bodyFat >= 25) || (bmi != null && bmi >= 30)) return "reducao de gordura e controle de medidas";
  if (bodyFat != null && bodyFat <= 12) return "preservacao de massa livre e performance";
  return "evolucao corporal por medidas e consistencia de protocolo";
}

function readMeasurementValue(measurements: JsonRecord | undefined, field: string): string | null {
  const entry = asRecord(measurements?.[field]);
  return readString(entry, "consolidated_value");
}

function asRecord(value: unknown): JsonRecord | undefined {
  if (!value || typeof value !== "object" || Array.isArray(value)) return undefined;
  return value as JsonRecord;
}

function readString(record: JsonRecord | undefined, key: string): string | null {
  const value = record?.[key];
  if (typeof value === "string" && value.trim()) return value;
  if (typeof value === "number" && Number.isFinite(value)) return String(value);
  return null;
}

function firstNameOf(memberName?: string | null): string {
  const value = memberName?.trim();
  return value ? value.split(/\s+/)[0] : "Aluno";
}

function formatMetric(value: number | null | undefined, unit = ""): string {
  if (value == null || !Number.isFinite(value)) return "-";
  return `${Number(value).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}${unit}`;
}
