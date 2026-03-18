import type { AssessmentDashboard, MemberMini } from "../../services/assessmentService";
import type { RiskLevel } from "../../types";

export type AssessmentQueueFilter = "all" | "overdue" | "never" | "week";
export type AssessmentQueueBucket = "overdue" | "never" | "week" | "upcoming" | "covered";

export type DashboardMember = MemberMini & { next_assessment_due?: string | null };

export interface OperationalAssessmentMember extends DashboardMember {
  queueBucket: AssessmentQueueBucket;
  urgencyScore: number;
  dueLabel: string;
  coverageLabel: string;
  daysOffset: number | null;
}

export interface AssessmentQueueGroup {
  key: AssessmentQueueBucket;
  label: string;
  description: string;
  members: OperationalAssessmentMember[];
  emptyMessage: string;
}

export function normalizeText(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return "-";
  return parsed.toLocaleDateString("pt-BR");
}

function daysUntilDue(member: DashboardMember): number | null {
  if (!member.next_assessment_due) return null;
  const due = new Date(member.next_assessment_due);
  if (Number.isNaN(due.getTime())) return null;
  return Math.floor((due.getTime() - Date.now()) / 86_400_000);
}

function riskBoost(level: RiskLevel): number {
  if (level === "red") return 60;
  if (level === "yellow") return 28;
  return 0;
}

function quickDueLabel(daysOffset: number | null): string {
  if (daysOffset === null) return "Sem prazo definido";
  if (daysOffset < 0) return `${Math.abs(daysOffset)} dia(s) de atraso`;
  if (daysOffset === 0) return "Vence hoje";
  if (daysOffset === 1) return "Vence amanha";
  if (daysOffset <= 7) return `Vence em ${daysOffset} dia(s)`;
  return `Proxima janela: ${daysOffset} dia(s)`;
}

function bucketMeta(bucket: AssessmentQueueBucket): { label: string; description: string; emptyMessage: string } {
  if (bucket === "overdue") {
    return {
      label: "Atrasadas",
      description: "Casos que ja estouraram a janela operacional",
      emptyMessage: "Nenhum aluno com avaliacao atrasada.",
    };
  }
  if (bucket === "never") {
    return {
      label: "Nunca avaliados",
      description: "Primeira leitura estruturada ainda pendente",
      emptyMessage: "Nenhum aluno sem avaliacao estruturada.",
    };
  }
  if (bucket === "week") {
    return {
      label: "Hoje e esta semana",
      description: "Janela operacional imediata",
      emptyMessage: "Nenhuma avaliacao prevista para esta semana.",
    };
  }
  if (bucket === "upcoming") {
    return {
      label: "Proximas",
      description: "Planejamento das proximas janelas",
      emptyMessage: "Nenhuma avaliacao futura mapeada.",
    };
  }
  return {
    label: "Em dia recentemente",
    description: "Base com cobertura recente ou sem pressao imediata",
    emptyMessage: "Sem alunos em acompanhamento recente.",
  };
}

export function buildOperationalAssessmentMembers(data: AssessmentDashboard): OperationalAssessmentMember[] {
  const combined = new Map<string, DashboardMember>();
  const collect = (items: MemberMini[] | undefined) => {
    for (const item of items ?? []) {
      const member = item as DashboardMember;
      combined.set(member.id, { ...(combined.get(member.id) ?? {}), ...member });
    }
  };

  collect(data.total_members_items);
  collect(data.assessed_members);
  collect(data.overdue_members);
  collect(data.never_assessed_members);
  collect(data.upcoming_members);

  const assessedIds = new Set((data.assessed_members ?? []).map((member) => member.id));
  const overdueIds = new Set((data.overdue_members ?? []).map((member) => member.id));
  const neverIds = new Set((data.never_assessed_members ?? []).map((member) => member.id));

  return Array.from(combined.values())
    .map((member) => {
      const daysOffset = daysUntilDue(member);
      let queueBucket: AssessmentQueueBucket = "covered";
      if (neverIds.has(member.id)) {
        queueBucket = "never";
      } else if (overdueIds.has(member.id) || (daysOffset !== null && daysOffset < 0)) {
        queueBucket = "overdue";
      } else if (daysOffset !== null && daysOffset <= 7) {
        queueBucket = "week";
      } else if (daysOffset !== null) {
        queueBucket = "upcoming";
      }

      let urgencyScore = member.risk_score + riskBoost(member.risk_level);
      if (queueBucket === "never") urgencyScore += 180;
      if (queueBucket === "overdue") urgencyScore += 150 + Math.abs(daysOffset ?? 0) * 4;
      if (queueBucket === "week") urgencyScore += 110 - Math.max(0, daysOffset ?? 0) * 6;
      if (queueBucket === "upcoming") urgencyScore += 40;

      const dueLabel =
        queueBucket === "never"
          ? "Primeira avaliacao pendente"
          : member.next_assessment_due
            ? `${quickDueLabel(daysOffset)} - ${formatDate(member.next_assessment_due)}`
            : "Sem proxima janela definida";

      const coverageLabel = neverIds.has(member.id)
        ? "Nenhuma avaliacao registrada"
        : assessedIds.has(member.id)
          ? "Cobertura recente nos ultimos 90 dias"
          : "Ultima avaliacao fora da janela recente";

      return {
        ...member,
        queueBucket,
        urgencyScore,
        dueLabel,
        coverageLabel,
        daysOffset,
      };
    })
    .sort((left, right) => right.urgencyScore - left.urgencyScore || left.full_name.localeCompare(right.full_name));
}

export function getAttentionNowMembers(members: OperationalAssessmentMember[]): OperationalAssessmentMember[] {
  return members
    .filter(
      (member) =>
        member.queueBucket === "overdue" ||
        member.queueBucket === "never" ||
        member.queueBucket === "week" ||
        member.risk_level === "red",
    )
    .slice(0, 6);
}

export function filterOperationalAssessmentMembers(
  members: OperationalAssessmentMember[],
  searchQuery: string,
  activeFilter: AssessmentQueueFilter,
): OperationalAssessmentMember[] {
  const normalizedSearch = normalizeText(searchQuery);
  return members.filter((member) => {
    if (activeFilter === "overdue" && member.queueBucket !== "overdue") return false;
    if (activeFilter === "never" && member.queueBucket !== "never") return false;
    if (activeFilter === "week" && member.queueBucket !== "week") return false;
    if (!normalizedSearch) return true;
    const haystack = normalizeText(
      [member.full_name, member.plan_name, member.email ?? "", member.coverageLabel, member.dueLabel].join(" "),
    );
    return haystack.includes(normalizedSearch);
  });
}

export function groupOperationalAssessmentMembers(members: OperationalAssessmentMember[]): AssessmentQueueGroup[] {
  const orderedBuckets: AssessmentQueueBucket[] = ["overdue", "never", "week", "upcoming", "covered"];
  return orderedBuckets
    .map((bucket) => {
      const meta = bucketMeta(bucket);
      return {
        key: bucket,
        ...meta,
        members: members.filter((member) => member.queueBucket === bucket),
      };
    })
    .filter((group) => group.members.length > 0);
}
