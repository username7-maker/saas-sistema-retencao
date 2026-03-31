import type { AssessmentQueueBucket, AssessmentQueueFilter, AssessmentQueueItem } from "../../services/assessmentService";
import type { RiskLevel } from "../../types";

export type { AssessmentQueueBucket, AssessmentQueueFilter, AssessmentQueueItem };
export type PreferredShiftFilter = "all" | "morning" | "afternoon" | "evening";

export interface AssessmentQueueFilterOption {
  key: AssessmentQueueFilter;
  label: string;
}

export const ASSESSMENT_QUEUE_FILTER_OPTIONS: AssessmentQueueFilterOption[] = [
  { key: "all", label: "Tudo" },
  { key: "overdue", label: "Atrasadas" },
  { key: "never", label: "Nunca avaliados" },
  { key: "week", label: "Esta semana" },
  { key: "upcoming", label: "Próximas" },
  { key: "covered", label: "Cobertura recente" },
];

export function normalizeText(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleDateString("pt-BR");
}

export function getQueueBucketLabel(bucket: AssessmentQueueBucket): string {
  if (bucket === "overdue") return "Atrasada";
  if (bucket === "never") return "Primeira avaliação";
  if (bucket === "week") return "Esta semana";
  if (bucket === "upcoming") return "Próxima";
  return "Cobertura recente";
}

export function getQueueBucketVariant(bucket: AssessmentQueueBucket): "neutral" | "warning" | "danger" | "info" | "success" {
  if (bucket === "never") return "warning";
  if (bucket === "overdue") return "danger";
  if (bucket === "week") return "info";
  if (bucket === "upcoming") return "neutral";
  return "success";
}

export function getRiskVariant(level: RiskLevel): "success" | "warning" | "danger" {
  if (level === "red") return "danger";
  if (level === "yellow") return "warning";
  return "success";
}

export function filterAttentionNowItems(
  items: AssessmentQueueItem[],
  searchQuery: string,
  activeFilter: AssessmentQueueFilter,
  preferredShift: PreferredShiftFilter,
): AssessmentQueueItem[] {
  const normalizedSearch = normalizeText(searchQuery);

  return items.filter((item) => {
    if (activeFilter !== "all" && item.queue_bucket !== activeFilter) return false;
    if (preferredShift !== "all") {
      const shift = normalizeText(item.preferred_shift ?? "");
      const matchesShift =
        (preferredShift === "morning" && ["morning", "manha", "matutino"].includes(shift)) ||
        (preferredShift === "afternoon" && ["afternoon", "tarde", "vespertino"].includes(shift)) ||
        (preferredShift === "evening" && ["evening", "night", "noite", "noturno"].includes(shift));
      if (!matchesShift) return false;
    }
    if (!normalizedSearch) return true;
    const haystack = normalizeText([
      item.full_name,
      item.email ?? "",
      item.plan_name,
      item.preferred_shift ?? "",
      item.coverage_label,
      item.due_label,
    ].join(" "));
    return haystack.includes(normalizedSearch);
  });
}

export function getQueueRangeLabel(total: number, page: number, pageSize: number): string {
  if (total === 0) return "Nenhum aluno encontrado";
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(total, start + pageSize - 1);
  return `Mostrando ${start}-${end} de ${total} aluno(s)`;
}
