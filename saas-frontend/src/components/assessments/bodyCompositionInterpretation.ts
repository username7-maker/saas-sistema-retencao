import type { BodyCompositionEvaluation } from "../../types";

const GOAL_LABELS: Record<string, string> = {
  reducao_de_gordura: "Reducao de gordura",
  ganho_de_massa: "Ganho de massa",
  melhora_metabolica: "Melhora metabolica",
  acompanhamento_geral: "Acompanhamento geral",
  preservacao_de_massa_magra: "Preservacao de massa magra",
  controle_de_gordura: "Controle de gordura",
};

const RANGE_FIELD_ORDER: Array<keyof BodyCompositionEvaluation> = [
  "weight_kg",
  "body_fat_percent",
  "waist_hip_ratio",
  "skeletal_muscle_kg",
  "muscle_mass_kg",
  "visceral_fat_level",
  "bmi",
  "health_score",
];

const RANGE_LABELS: Partial<Record<keyof BodyCompositionEvaluation, string>> = {
  weight_kg: "Peso",
  body_fat_percent: "Gordura corporal",
  waist_hip_ratio: "Relacao cintura-quadril",
  skeletal_muscle_kg: "Musculo esqueletico",
  muscle_mass_kg: "Massa muscular",
  visceral_fat_level: "Gordura visceral",
  bmi: "IMC",
  health_score: "Health score",
};

function normalizeSummary(text: string | null | undefined): string {
  return (text ?? "").replace(/\s+/g, " ").trim();
}

function looksTruncated(text: string | null | undefined): boolean {
  const normalized = normalizeSummary(text);
  if (!normalized) return false;
  if (normalized.length >= 495 && !/[.!?…]$/.test(normalized)) return true;
  const parts = normalized.split(" ");
  const lastToken = parts[parts.length - 1] ?? "";
  return normalized.length >= 80 && lastToken.length <= 2 && !/[.!?…]$/.test(normalized);
}

export function formatBodyCompositionGoal(value: string | null | undefined): string {
  const normalized = (value ?? "").trim();
  if (!normalized) return "Acompanhamento geral";
  return GOAL_LABELS[normalized] ?? normalized.replace(/_/g, " ");
}

export function resolveCoachSummary(evaluation: BodyCompositionEvaluation | null | undefined): string {
  const stored = normalizeSummary(evaluation?.ai_coach_summary);
  if (stored && !looksTruncated(stored)) return stored;

  const flags = (evaluation?.ai_risk_flags_json ?? []).slice(0, 2);
  const primaryGoal = formatBodyCompositionGoal(evaluation?.ai_training_focus_json?.primary_goal);
  if (flags.length > 0) {
    const flagsText = flags.map((flag) => flag.toLowerCase()).join(" e ");
    return `Leitura corporal com foco inicial em ${primaryGoal.toLowerCase()}, com atencao principal para ${flagsText}.`;
  }
  return `Leitura corporal sem alertas prioritarios fora da faixa, com foco inicial em ${primaryGoal.toLowerCase()}.`;
}

export function resolveMemberSummary(evaluation: BodyCompositionEvaluation | null | undefined): string {
  const stored = normalizeSummary(evaluation?.ai_member_friendly_summary);
  if (stored && !looksTruncated(stored)) return stored;

  const primaryGoal = formatBodyCompositionGoal(evaluation?.ai_training_focus_json?.primary_goal);
  return (
    `Este exame serve como ponto de partida para organizar o acompanhamento com foco inicial em ${primaryGoal.toLowerCase()}. ` +
    "Vamos revisar os proximos passos com clareza e acompanhar a evolucao nas proximas semanas."
  );
}

export function buildBodyCompositionRangeClassifications(
  evaluation?: BodyCompositionEvaluation | null,
): Array<{ label: string; status: "abaixo" | "dentro" | "acima" }> {
  if (!evaluation?.measured_ranges_json) return [];

  const results: Array<{ label: string; status: "abaixo" | "dentro" | "acima" }> = [];
  for (const field of RANGE_FIELD_ORDER) {
    const range = evaluation.measured_ranges_json[field];
    const currentValue = evaluation[field];
    if (typeof currentValue !== "number" || !range) continue;
    const min = typeof range.min === "number" ? range.min : null;
    const max = typeof range.max === "number" ? range.max : null;
    if (min == null && max == null) continue;

    let status: "abaixo" | "dentro" | "acima" = "dentro";
    if (min != null && currentValue < min) status = "abaixo";
    if (max != null && currentValue > max) status = "acima";

    results.push({ label: RANGE_LABELS[field] ?? String(field), status });
  }

  return results.slice(0, 6);
}
