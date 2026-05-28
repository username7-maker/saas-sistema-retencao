import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, BarChart3, Briefcase, Target, Trophy, UserRoundCheck } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { getChartSeriesState } from "../../components/charts/chartState";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { QuickLeadActions } from "../../components/common/QuickLeadActions";
import { EmptyState } from "../../components/ui";
import {
  CommandCard,
  MetricCard,
  PremiumEmptyState,
  PremiumTable,
  PremiumTableBody,
  PremiumTableCell,
  PremiumTableHead,
  PremiumTableHeader,
  PremiumTableRow,
  SectionHeader,
  StatusPill,
} from "../../components/ui2";
import { useCommercialDashboard } from "../../hooks/useDashboard";
import { getPermissionAwareMessage } from "../../utils/httpErrors";

const STAGE_LABELS: Record<string, string> = {
  new: "Novo",
  contacted: "Contactado",
  contact: "Contato",
  visit: "Visita",
  trial: "Aula experimental",
  proposal: "Proposta",
  proposal_sent: "Proposta enviada",
  meeting_scheduled: "Reunião",
  won: "Fechado",
  lost: "Perdido",
};

function stageColor(stage: string): string {
  if (stage === "won") return "hsl(var(--lovable-success))";
  if (stage === "lost") return "hsl(var(--lovable-danger))";
  if (stage === "proposal" || stage === "proposal_sent") return "hsl(var(--lovable-warning))";
  return "hsl(var(--lovable-primary))";
}

function daysSince(isoDate: string | null | undefined): number | null {
  if (!isoDate) return null;
  return Math.floor((Date.now() - new Date(isoDate).getTime()) / 86_400_000);
}

export function CommercialDashboardPage() {
  const queryClient = useQueryClient();
  const query = useCommercialDashboard();

  const pipelineData = useMemo(() => {
    if (!query.data) return [];
    return Object.entries(query.data.pipeline).map(([stage, total]) => ({
      stage,
      label: STAGE_LABELS[stage] ?? stage,
      total,
    }));
  }, [query.data]);

  const pipelineState = getChartSeriesState(pipelineData, ["total"]);
  const hasPipeline = pipelineState.hasMeaningfulValues;
  const hasCommercialBase = hasPipeline || (query.data?.conversion_by_source.length ?? 0) > 0 || (query.data?.stale_leads_total ?? 0) > 0;

  const handleActionComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "commercial"] });
  };

  if (query.isLoading) {
    return <LoadingPanel text="Carregando dashboard comercial..." />;
  }

  if (query.isError || !query.data) {
    return (
      <EmptyState
        icon={AlertTriangle}
        title="Não foi possível carregar o dashboard comercial"
        description={getPermissionAwareMessage(query.error, "Tente novamente para recuperar pipeline, conversão e leads parados.")}
        action={{ label: "Tentar novamente", onClick: () => void query.refetch() }}
      />
    );
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-4 rounded-[28px] border border-lovable-border/70 bg-[linear-gradient(135deg,hsl(var(--lovable-surface)/0.96),hsl(var(--lovable-bg-muted)/0.78))] p-5 shadow-panel md:flex-row md:items-end md:justify-between">
        <div>
          <p className="text-[11px] font-bold uppercase tracking-[0.3em] text-lovable-ink-muted">Comercial</p>
          <h2 className="mt-2 font-heading text-3xl font-bold text-lovable-ink">Dashboard Comercial</h2>
          <p className="mt-1 text-sm text-lovable-ink-muted">Pipeline, conversão por origem, follow-up e oportunidades paradas.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <DashboardActions dashboard="commercial" />
          <Link
            to="/crm"
            className="inline-flex h-10 items-center justify-center rounded-xl border border-[hsl(var(--lovable-primary)/0.75)] bg-[linear-gradient(135deg,hsl(var(--lovable-primary)),hsl(var(--lovable-info)/0.92))] px-4 text-xs font-semibold uppercase tracking-wider text-[hsl(207_58%_4%)] shadow-[0_18px_46px_-26px_hsl(var(--lovable-primary)/0.9)] hover:brightness-110"
          >
            Abrir CRM Kanban
          </Link>
        </div>
      </header>

      <AiInsightCard dashboard="commercial" />

      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard
          label="CAC"
          value={hasCommercialBase ? `R$ ${query.data.cac.toFixed(2)}` : "Sem base"}
          subtitle="Custo de aquisição estimado"
          icon={Target}
          tone={hasCommercialBase ? "warning" : "neutral"}
        />
        <MetricCard
          label="Leads em proposta"
          value={String(query.data.pipeline.proposal ?? query.data.pipeline.proposal_sent ?? 0)}
          subtitle="Oportunidades em negociação"
          icon={Briefcase}
          tone="info"
        />
        <MetricCard
          label="Fechados"
          value={String(query.data.pipeline.won ?? 0)}
          subtitle="Conversões registradas no funil"
          icon={Trophy}
          tone="success"
        />
      </div>

      <CommandCard>
        <SectionHeader title="Pipeline por estágio" subtitle="Distribuição visual das oportunidades comerciais." />
        <div className="h-72">
          {hasPipeline ? (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={pipelineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--lovable-chart-grid) / 0.55)" />
                <XAxis dataKey="label" stroke="hsl(var(--lovable-ink-muted))" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis stroke="hsl(var(--lovable-ink-muted))" axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "rgba(14,16,24,0.97)",
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: "12px",
                    padding: "10px 14px",
                    color: "hsl(var(--lovable-ink))",
                    boxShadow: "0 8px 32px rgba(0,0,0,0.48)",
                  }}
                  labelStyle={{ color: "hsl(var(--lovable-ink-muted))", fontSize: "11px" }}
                  itemStyle={{ fontFamily: "'JetBrains Mono',monospace", fontSize: "13px", fontWeight: 600 }}
                  cursor={{ fill: "rgba(255,255,255,0.04)" }}
                />
                <Bar dataKey="total" radius={[10, 10, 0, 0]}>
                  {pipelineData.map((entry) => (
                    <Cell key={entry.stage} fill={stageColor(entry.stage)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <PremiumEmptyState
              icon={BarChart3}
              title="Pipeline ainda sem base útil"
              description="Quando houver leads e mudanças reais de estágio, o funil aparece aqui."
              className="h-full"
            />
          )}
        </div>
      </CommandCard>

      <CommandCard>
        <SectionHeader title="Conversão por origem" subtitle="Quais canais estão gerando alunos reais." />
        {(query.data.conversion_by_source ?? []).length === 0 ? (
          <PremiumEmptyState
            icon={UserRoundCheck}
            title="Conversão ainda sem volume confiável"
            description="Registre origem e resultado dos leads para ativar essa leitura."
          />
        ) : (
          <PremiumTable>
            <PremiumTableHead>
              <PremiumTableRow>
                <PremiumTableHeader>Origem</PremiumTableHeader>
                <PremiumTableHeader>Total</PremiumTableHeader>
                <PremiumTableHeader>Fechados</PremiumTableHeader>
                <PremiumTableHeader>Conversão</PremiumTableHeader>
              </PremiumTableRow>
            </PremiumTableHead>
            <PremiumTableBody>
              {query.data.conversion_by_source.map((row) => (
                <PremiumTableRow key={row.source}>
                  <PremiumTableCell className="font-medium text-lovable-ink">{row.source}</PremiumTableCell>
                  <PremiumTableCell className="text-lovable-ink-muted">{row.total}</PremiumTableCell>
                  <PremiumTableCell className="text-lovable-ink-muted">{row.won}</PremiumTableCell>
                  <PremiumTableCell className="font-medium text-lovable-ink">{row.conversion_rate}%</PremiumTableCell>
                </PremiumTableRow>
              ))}
            </PremiumTableBody>
          </PremiumTable>
        )}
      </CommandCard>

      <CommandCard variant={query.data.stale_leads_total > 0 ? "warning" : "default"}>
        <SectionHeader
          title="Leads parados 3+ dias"
          subtitle="Oportunidades que precisam de retomada antes de esfriar."
          actions={<StatusPill tone={query.data.stale_leads_total > 0 ? "warning" : "neutral"}>{query.data.stale_leads_total}</StatusPill>}
        />
        {query.data.stale_leads.length === 0 ? (
          <PremiumEmptyState
            icon={Briefcase}
            title="Nenhum lead parado"
            description="O pipeline comercial está sem bloqueio operacional neste recorte."
          />
        ) : (
          <ul className="space-y-3">
            {query.data.stale_leads.map((lead) => {
              const dias = daysSince(lead.last_contact_at);
              return (
                <li key={lead.id} className="rounded-[18px] border border-lovable-border/70 bg-lovable-surface/58 px-3 py-3 text-sm">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="font-medium text-lovable-ink">{lead.full_name}</p>
                      <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-lovable-ink-muted">
                        <span>Estágio: {STAGE_LABELS[lead.stage] ?? lead.stage}</span>
                        <span>Origem: {lead.source}</span>
                        {dias !== null ? (
                          <StatusPill tone={dias > 7 ? "danger" : "warning"}>
                            {dias}d sem contato
                          </StatusPill>
                        ) : null}
                      </div>
                    </div>
                  </div>
                  <div className="mt-2">
                    <QuickLeadActions lead={lead} onActionComplete={handleActionComplete} />
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </CommandCard>
    </section>
  );
}
