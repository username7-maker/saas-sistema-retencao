import type {
  Assessment,
  AssessmentMini,
  AssessmentSummary360,
  MemberConstraints,
  MemberGoal,
  TrainingPlan,
} from "../../services/assessmentService";
import type { BodyCompositionEvaluation, RiskLevel } from "../../types";

export type AssessmentWorkspaceTab =
  | "overview"
  | "registro"
  | "evolucao"
  | "plano"
  | "contexto"
  | "acoes"
  | "bioimpedancia";

export const ASSESSMENT_WORKSPACE_TABS: Array<{ key: AssessmentWorkspaceTab; label: string }> = [
  { key: "overview", label: "Visao geral" },
  { key: "registro", label: "Registrar avaliacao" },
  { key: "evolucao", label: "Evolucao" },
  { key: "plano", label: "Plano e objetivos" },
  { key: "contexto", label: "Restricoes e contexto" },
  { key: "acoes", label: "Acoes" },
  { key: "bioimpedancia", label: "Bioimpedancia" },
];

export function normalizeAssessmentWorkspaceTab(value: string | null | undefined): AssessmentWorkspaceTab {
  const normalized = (value ?? "").toLowerCase();
  if (
    normalized === "overview" ||
    normalized === "registro" ||
    normalized === "evolucao" ||
    normalized === "plano" ||
    normalized === "contexto" ||
    normalized === "acoes" ||
    normalized === "bioimpedancia"
  ) {
    return normalized;
  }
  return "overview";
}

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("") || "AL";
}

function normalizeDate(value: unknown): Date | null {
  if (typeof value !== "string") return null;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return null;
  return new Date(parsed);
}

function normalizeCalendarDate(value: string | null | undefined): Date | null {
  if (!value) return null;
  const parsed = new Date(`${value}T12:00:00`);
  if (Number.isNaN(parsed.getTime())) return null;
  return parsed;
}

export function getAge(extraData: Record<string, unknown> | undefined): number | null {
  if (!extraData) return null;

  const directAge = extraData.age;
  if (typeof directAge === "number" && Number.isFinite(directAge) && directAge > 0) {
    return Math.floor(directAge);
  }

  const birthDate = normalizeDate(extraData.birth_date);
  if (!birthDate) return null;

  const now = new Date();
  let age = now.getFullYear() - birthDate.getFullYear();
  const monthDiff = now.getMonth() - birthDate.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < birthDate.getDate())) {
    age -= 1;
  }
  return age >= 0 ? age : null;
}

export function daysSince(dateValue: string | null | undefined): number | null {
  if (!dateValue) return null;
  const parsed = Date.parse(dateValue);
  if (Number.isNaN(parsed)) return null;
  return Math.floor((Date.now() - parsed) / (1000 * 60 * 60 * 24));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleDateString("pt-BR");
}

export function formatBirthdayDayMonth(value: string | null | undefined): string | null {
  const parsed = normalizeCalendarDate(value);
  if (!parsed) return null;
  return parsed.toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
  });
}

export function getBirthdayCountdownLabel(value: string | null | undefined, now = new Date()): string | null {
  const birthdate = normalizeCalendarDate(value);
  if (!birthdate) return null;

  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  let nextBirthday = new Date(today.getFullYear(), birthdate.getMonth(), birthdate.getDate());
  if (nextBirthday < today) {
    nextBirthday = new Date(today.getFullYear() + 1, birthdate.getMonth(), birthdate.getDate());
  }

  const diffDays = Math.round((nextBirthday.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return "Hoje";
  if (diffDays === 1) return "Amanhã";
  return `Em ${diffDays} dias`;
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function riskBadgeVariant(level: RiskLevel): "success" | "warning" | "danger" {
  if (level === "red") return "danger";
  if (level === "yellow") return "warning";
  return "success";
}

export function riskLabel(level: RiskLevel): string {
  if (level === "red") return "Risco alto";
  if (level === "yellow") return "Atencao";
  return "Estavel";
}

export function statusBadgeVariant(status: AssessmentSummary360["status"]): "success" | "warning" | "danger" {
  if (status === "critical") return "danger";
  if (status === "attention") return "warning";
  return "success";
}

export function statusLabel(status: AssessmentSummary360["status"]): string {
  if (status === "critical") return "Meta em risco";
  if (status === "attention") return "Atencao operacional";
  return "Na curva esperada";
}

export function formatGoalType(goalType: string): string {
  if (goalType === "fat_loss") return "Perda de gordura";
  if (goalType === "muscle_gain") return "Ganho de massa";
  if (goalType === "performance") return "Performance";
  return "Geral";
}

export function summarizeLatestAssessment(assessment: AssessmentMini | Assessment | null): string {
  if (!assessment) return "Sem avaliacao estruturada";
  const metrics: string[] = [];
  if (assessment.weight_kg != null) metrics.push(`${assessment.weight_kg} kg`);
  if (assessment.body_fat_pct != null) metrics.push(`${assessment.body_fat_pct}% BF`);
  if (assessment.bmi != null) metrics.push(`BMI ${assessment.bmi}`);
  const summary = metrics.length > 0 ? metrics.join(" - ") : "Sem medidas principais";
  return `${formatDate(assessment.assessment_date)} - ${summary}`;
}

export function summarizeGoals(goals: MemberGoal[]): string {
  if (goals.length === 0) return "Sem metas ativas registradas";
  const active = goals.filter((goal) => goal.status !== "cancelled" && !goal.achieved);
  if (active.length === 0) return `${goals.length} meta(s) encerrada(s)`;
  if (active.length === 1) return active[0].title;
  return `${active.length} metas ativas`;
}

export function summarizeTrainingPlan(plan: TrainingPlan | null): string {
  if (!plan) return "Sem plano ativo";
  const frequency = plan.sessions_per_week ? `${plan.sessions_per_week}x semana` : "frequencia nao definida";
  return `${plan.name} - ${frequency}`;
}

export function summarizeConstraints(constraints: MemberConstraints | null): string {
  if (!constraints) return "Sem restricoes registradas";
  const highlights = [
    constraints.injuries,
    constraints.medical_conditions,
    constraints.contraindications,
    constraints.preferred_training_times,
  ].filter((value): value is string => Boolean(value && value.trim()));
  if (highlights.length === 0) return "Sem restricoes detalhadas";
  return highlights.slice(0, 2).join(" - ");
}

export function summarizeBodyComposition(evaluation: BodyCompositionEvaluation | null | undefined): string {
  if (!evaluation) return "Sem bioimpedancia registrada";
  const highlights: string[] = [];
  if (evaluation.weight_kg != null) highlights.push(`${evaluation.weight_kg} kg`);
  if (evaluation.body_fat_percent != null) highlights.push(`${evaluation.body_fat_percent}% BF`);
  if (evaluation.health_score != null) highlights.push(`score ${evaluation.health_score}`);
  return highlights.length > 0 ? highlights.join(" - ") : "Registro salvo na aba dedicada";
}
