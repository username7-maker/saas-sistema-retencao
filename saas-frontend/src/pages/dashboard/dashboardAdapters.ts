import type { ChurnPoint, ExecutiveDashboard, NPSEvolutionPoint } from "../../types";

interface CommercialInput {
  pipeline: Record<string, number>;
  stale_leads_total: number;
}

interface OperationalInput {
  realtime_checkins: number;
  inactive_7d_total: number;
}

interface RetentionInput {
  red: { total: number };
  yellow: { total: number };
  nps_trend: NPSEvolutionPoint[];
}

export interface LovableAlert {
  id: string;
  title: string;
  description: string;
  tone: "danger" | "warning" | "neutral";
  href: string;
}

export interface LovableQuickAction {
  id: string;
  label: string;
  description: string;
  href: string;
}

export interface RetentionChartPoint {
  month: string;
  churn_rate: number | null;
  nps_avg: number | null;
}

export interface LovableDashboardViewModel {
  cards: {
    revenue: number;
    leads: number;
    checkins: number;
    highRiskMembers: number;
  };
  alerts: LovableAlert[];
  insight: string;
  retentionChart: RetentionChartPoint[];
  quickActions: LovableQuickAction[];
  hasData: boolean;
}

function pipelineTotal(pipeline: Record<string, number> | undefined): number {
  if (!pipeline) return 0;
  return Object.values(pipeline).reduce((acc, value) => acc + value, 0);
}

function mapRetentionSeries(churn: ChurnPoint[] | undefined, nps: NPSEvolutionPoint[] | undefined): RetentionChartPoint[] {
  const churnMap = new Map((churn ?? []).map((point) => [point.month, point.churn_rate]));
  const npsMap = new Map((nps ?? []).map((point) => [point.month, point.average_score]));
  const months = Array.from(new Set([...churnMap.keys(), ...npsMap.keys()])).sort();

  return months.map((month) => ({
    month,
    churn_rate: churnMap.get(month) ?? null,
    nps_avg: npsMap.get(month) ?? null,
  }));
}

function buildInsight(
  highRiskMembers: number,
  inactiveMembers: number,
  staleLeads: number,
  npsLatest: number | null,
): string {
  if (highRiskMembers === 0 && inactiveMembers === 0 && staleLeads === 0 && npsLatest === null) {
    return "Sem dados suficientes ainda para gerar recomendacoes. Importe check-ins e alunos para ativar insights.";
  }

  const insightParts: string[] = [];

  if (highRiskMembers > 0) {
    insightParts.push(`${highRiskMembers} aluno(s) em risco alto exigem contato ativo nas proximas 24h`);
  }
  if (inactiveMembers > 0) {
    insightParts.push(`${inactiveMembers} aluno(s) estao ha 7+ dias sem treinar`);
  }
  if (staleLeads > 0) {
    insightParts.push(`${staleLeads} lead(s) comercial(is) estao sem follow-up`);
  }
  if (npsLatest !== null) {
    insightParts.push(`NPS atual em ${npsLatest.toFixed(1)} indica tendencia de satisfacao`);
  }

  return insightParts.join(". ") + ".";
}

export function buildLovableDashboardViewModel(input: {
  executive?: ExecutiveDashboard;
  commercial?: CommercialInput;
  operational?: OperationalInput;
  retention?: RetentionInput;
  churn?: ChurnPoint[];
}): LovableDashboardViewModel {
  const revenue = input.executive?.mrr ?? 0;
  const leads = pipelineTotal(input.commercial?.pipeline);
  const checkins = input.operational?.realtime_checkins ?? 0;
  const highRiskMembers = input.retention?.red.total ?? 0;
  const inactiveMembers = input.operational?.inactive_7d_total ?? 0;
  const staleLeads = input.commercial?.stale_leads_total ?? 0;
  const npsSeries = input.retention?.nps_trend ?? [];
  const npsLatest = npsSeries.length > 0 ? npsSeries[npsSeries.length - 1].average_score : null;

  const alerts: LovableAlert[] = [];
  if (highRiskMembers > 0) {
    alerts.push({
      id: "high-risk",
      title: "Risco vermelho ativo",
      description: `${highRiskMembers} aluno(s) requer(em) acao imediata da equipe de retencao.`,
      tone: "danger",
      href: "/dashboard/retention",
    });
  }
  if (inactiveMembers > 0) {
    alerts.push({
      id: "inactive-members",
      title: "Inatividade acima do ideal",
      description: `${inactiveMembers} aluno(s) estao sem check-in por 7 dias ou mais.`,
      tone: "warning",
      href: "/dashboard/operational",
    });
  }
  if (staleLeads > 0) {
    alerts.push({
      id: "stale-leads",
      title: "Pipeline comercial parado",
      description: `${staleLeads} lead(s) estao sem contato recente e podem esfriar.`,
      tone: "neutral",
      href: "/dashboard/commercial",
    });
  }

  const quickActions: LovableQuickAction[] = [
    {
      id: "quick-retention",
      label: "Abrir Retencao",
      description: `${highRiskMembers} aluno(s) em risco vermelho`,
      href: "/dashboard/retention",
    },
    {
      id: "quick-crm",
      label: "Avancar CRM",
      description: `${staleLeads} lead(s) sem contato recente`,
      href: "/crm",
    },
    {
      id: "quick-import",
      label: "Importar CSV",
      description: "Atualize base de membros e catraca",
      href: "/imports",
    },
    {
      id: "quick-tasks",
      label: "Executar Tasks",
      description: "Acompanhe as tarefas abertas da equipe",
      href: "/tasks",
    },
  ];

  const hasData = revenue > 0 || leads > 0 || checkins > 0 || highRiskMembers > 0 || npsSeries.length > 0;

  return {
    cards: { revenue, leads, checkins, highRiskMembers },
    alerts,
    insight: buildInsight(highRiskMembers, inactiveMembers, staleLeads, npsLatest),
    retentionChart: mapRetentionSeries(input.churn, npsSeries),
    quickActions,
    hasData,
  };
}
