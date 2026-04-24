import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { MemberTimeline } from "../../components/common/MemberTimeline";
import { QuickActions } from "../../components/common/QuickActions";
import { StatCard } from "../../components/common/StatCard";
import { useRetentionDashboard } from "../../hooks/useDashboard";
import { riskAlertService } from "../../services/riskAlertService";
import type { Member } from "../../types";

type RetentionMember = Member & {
  churn_type?: string | null;
  extra_data?: Record<string, unknown> | null;
};

const CHURN_LABELS: Record<string, { label: string; tone: "danger" | "warning" | "info" | "neutral" }> = {
  frequencia: { label: "Frequencia", tone: "danger" },
  frustracao: { label: "Frustracao", tone: "warning" },
  lifestyle: { label: "Lifestyle / Rotina", tone: "info" },
  financeiro: { label: "Financeiro", tone: "neutral" },
};

const CHURN_ORDER = ["frequencia", "frustracao", "lifestyle", "financeiro"];
const EMPTY_RETENTION_ITEMS: RetentionMember[] = [];
const EMPTY_LAST_CONTACT_MAP: Record<string, string> = {};

function daysInactive(lastCheckinAt: string | null): number | null {
  if (!lastCheckinAt) return null;
  return Math.floor((Date.now() - new Date(lastCheckinAt).getTime()) / (1000 * 60 * 60 * 24));
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatLastContact(lastContactMap: Record<string, string>, memberId: string): string {
  const iso = lastContactMap[memberId];
  if (!iso) return "";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / (1000 * 60 * 60 * 24));
  if (days === 0) return "hoje";
  if (days === 1) return "ha 1 dia";
  return `ha ${days} dias`;
}

type ChipColor = "danger" | "warning" | "info";
const chipClass: Record<ChipColor, string> = {
  danger: "bg-lovable-danger/10 text-lovable-danger",
  warning: "bg-lovable-warning/10 text-lovable-warning",
  info: "bg-lovable-primary/10 text-lovable-primary",
};

function computeRiskChips(member: Member): { label: string; color: ChipColor }[] {
  const chips: { label: string; color: ChipColor }[] = [];
  const days = daysInactive(member.last_checkin_at);
  if (days !== null && days >= 7) chips.push({ label: "Inatividade", color: "danger" });
  if (member.nps_last_score > 0 && member.nps_last_score < 7) chips.push({ label: "NPS Baixo", color: "warning" });
  if (member.loyalty_months < 2) chips.push({ label: "Novo", color: "info" });
  return chips;
}

interface MemberCardProps {
  member: RetentionMember;
  lastContactMap: Record<string, string>;
  onTimeline: (m: Member) => void;
  onActionComplete: () => void;
}

function MemberCard({ member, lastContactMap, onTimeline, onActionComplete }: MemberCardProps) {
  const days = daysInactive(member.last_checkin_at);
  const chips = computeRiskChips(member);
  const hasContact = Boolean(lastContactMap[member.id]);
  const lastContactLabel = formatLastContact(lastContactMap, member.id);
  const churnType = member.churn_type ?? null;

  return (
    <li className="rounded-xl border border-lovable-border bg-lovable-surface/50 px-4 py-3 text-sm shadow-sm transition-shadow hover:shadow-panel">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="truncate font-semibold text-lovable-ink">{member.full_name}</p>
          <p className="text-xs text-lovable-ink-muted">{member.plan_name}</p>
        </div>
        <span className="shrink-0 rounded-full bg-lovable-danger/10 px-2 py-0.5 text-[11px] font-bold text-lovable-danger">
          {member.risk_score}
        </span>
      </div>

      <div className="mt-2">
        {days !== null ? (
          <span
            className={`text-xs font-medium ${
              days >= 14
                ? "text-lovable-danger"
                : days >= 7
                  ? "text-lovable-warning"
                  : "text-lovable-ink-muted"
            }`}
          >
            {days === 0 ? "Treinou hoje" : `Ha ${days} dia${days !== 1 ? "s" : ""} sem treinar`}
          </span>
        ) : (
          <span className="text-xs text-lovable-ink-muted">Sem check-in registrado</span>
        )}
      </div>

      {churnType && CHURN_LABELS[churnType] ? (
        <span className="mt-1 inline-block rounded-full border border-lovable-border bg-lovable-surface-soft px-2 py-0.5 text-[10px] font-semibold text-lovable-ink-muted">
          {CHURN_LABELS[churnType].label}
        </span>
      ) : null}

      {chips.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {chips.map((chip) => (
            <span
              key={chip.label}
              className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${chipClass[chip.color]}`}
            >
              {chip.label}
            </span>
          ))}
        </div>
      )}

      {member.suggested_action && (
        <div className="mt-2">
          <span className="inline-flex items-center gap-1 rounded-full bg-lovable-primary/10 px-2 py-0.5 text-[10px] font-semibold text-lovable-primary">
            <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 18l6-6-6-6"/></svg>
            {member.suggested_action}
          </span>
        </div>
      )}

      <p
        className={`mt-2 text-[11px] ${
          hasContact ? "text-lovable-ink-muted" : "font-semibold text-lovable-warning"
        }`}
      >
        {hasContact ? `Ultimo contato: ${lastContactLabel}` : "Nunca contatado"}
      </p>

      <div className="mt-3 flex flex-col gap-2">
        <button
          type="button"
          onClick={() => onTimeline(member)}
          className="self-start rounded-full border border-lovable-border px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted hover:border-lovable-border-strong hover:text-lovable-ink"
        >
          Ver timeline 360
        </button>
        <QuickActions member={member} onActionComplete={onActionComplete} />
      </div>
    </li>
  );
}

interface RiskPanelProps {
  tone: "danger" | "warning";
  label: string;
  count: number;
  avgScore: number;
  members: RetentionMember[];
  lastContactMap: Record<string, string>;
  onTimeline: (m: Member) => void;
  onActionComplete: () => void;
}

function RiskPanel({
  tone,
  label,
  count,
  avgScore,
  members,
  lastContactMap,
  onTimeline,
  onActionComplete,
}: RiskPanelProps) {
  const borderCls = tone === "danger" ? "border-lovable-danger/30" : "border-lovable-warning/30";
  const headingCls = tone === "danger" ? "text-lovable-danger" : "text-lovable-warning";
  const vipCount = tone === "danger" ? members.filter((m) => m.loyalty_months >= 6 && m.risk_score >= 70).length : 0;

  return (
    <section className={`rounded-2xl border ${borderCls} bg-lovable-surface p-4 shadow-panel`}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className={`text-sm font-semibold uppercase tracking-wider ${headingCls}`}>
          {label} ({count})
        </h3>
        {count > 0 && (
          <span className="text-xs text-lovable-ink-muted">
            Score medio:{" "}
            <strong className="text-lovable-ink">{avgScore.toFixed(0)}</strong>
          </span>
        )}
      </div>
      {vipCount > 0 ? (
        <div className="mb-3 rounded-xl border border-lovable-warning/40 bg-lovable-warning/5 px-3 py-2">
          <p className="text-xs font-semibold text-lovable-warning">
            ⭐ {vipCount} aluno{vipCount !== 1 ? "s" : ""} VIP (6+ meses) em risco critico - priorize o contato
          </p>
        </div>
      ) : null}
      {members.length === 0 ? (
        <p className="text-sm text-lovable-ink-muted">Nenhum aluno neste nivel de risco.</p>
      ) : (
        <ul className="space-y-3">
          {members.map((m) => (
            <MemberCard
              key={m.id}
              member={m}
              lastContactMap={lastContactMap}
              onTimeline={onTimeline}
              onActionComplete={onActionComplete}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export function RetentionDashboardPage() {
  const queryClient = useQueryClient();
  const [selectedMember, setSelectedMember] = useState<Member | null>(null);
  const [pendingAlertId, setPendingAlertId] = useState<string | null>(null);
  const query = useRetentionDashboard();

  const alertsQuery = useQuery({
    queryKey: ["risk-alerts", "unresolved-red"],
    queryFn: () => riskAlertService.listUnresolved("red"),
    staleTime: 60 * 1000,
  });

  const resolveMutation = useMutation({
    mutationFn: (alertId: string) => {
      setPendingAlertId(alertId);
      return riskAlertService.resolve(alertId, "Resolvido no dashboard de retencao");
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["risk-alerts", "unresolved-red"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "retention"] });
      toast.success("Alerta resolvido!");
    },
    onError: () => {
      toast.error("Falha ao resolver alerta.");
    },
    onSettled: () => setPendingAlertId(null),
  });

  const handleActionComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "retention"] });
  };

  const data = query.data;
  const redItems = (data?.red?.items ?? EMPTY_RETENTION_ITEMS) as RetentionMember[];
  const yellowItems = (data?.yellow?.items ?? EMPTY_RETENTION_ITEMS) as RetentionMember[];
  const red = data?.red ?? { total: redItems.length, items: redItems };
  const yellow = data?.yellow ?? { total: yellowItems.length, items: yellowItems };
  const nps_trend = data?.nps_trend ?? [];
  const mrr_at_risk = Number(data?.mrr_at_risk ?? 0);
  const avg_red_score = Number(data?.avg_red_score ?? 0);
  const avg_yellow_score = Number(data?.avg_yellow_score ?? 0);
  const last_contact_map = data?.last_contact_map ?? EMPTY_LAST_CONTACT_MAP;
  const totalRisk = red.total + yellow.total;

  const churnCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const member of [...redItems, ...yellowItems]) {
      const churnType = member.churn_type;
      if (churnType && CHURN_LABELS[churnType]) {
        counts[churnType] = (counts[churnType] ?? 0) + 1;
      }
    }
    return counts;
  }, [redItems, yellowItems]);

  const churnTotal = useMemo(() => Object.values(churnCounts).reduce((sum, value) => sum + value, 0), [churnCounts]);

  const forecast60Avg = useMemo(() => {
    const values = redItems
      .map((member) => {
        const forecast = member.extra_data?.retention_forecast_60d;
        return typeof forecast === "number" && forecast >= 0 && forecast <= 100 ? forecast : null;
      })
      .filter((value): value is number => value !== null);
    if (values.length === 0) return null;
    return Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
  }, [redItems]);

  const memberById: Record<string, string> = {};
  for (const m of [...redItems, ...yellowItems]) {
    memberById[m.id] = m.full_name;
  }

  if (query.isLoading) return <LoadingPanel text="Carregando dashboard de retencao..." />;
  if (query.isError) return <LoadingPanel text="Erro ao carregar dados de retencao." />;
  if (!data) return <LoadingPanel text="Sem dados de retencao." />;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard de Retencao</h2>
          <p className="text-sm text-lovable-ink-muted">
            Alunos em risco, evolucao NPS e acoes de retencao.
          </p>
        </div>
        <DashboardActions dashboard="retention" />
      </header>

      <AiInsightCard dashboard="retention" />

      {totalRisk > 0 && (
        <div className="rounded-xl border border-lovable-danger/30 bg-lovable-danger/5 px-4 py-3">
          <p className="text-sm font-semibold text-lovable-danger">
            {red.total > 0 && `${red.total} aluno${red.total !== 1 ? "s" : ""} em risco vermelho`}
            {red.total > 0 && yellow.total > 0 && " e "}
            {yellow.total > 0 && `${yellow.total} em risco amarelo`}
            {" - acao imediata recomendada."}
          </p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Risco Vermelho"
          value={String(red.total)}
          tone="danger"
          tooltip={red.total > 0 ? `Score medio: ${avg_red_score.toFixed(0)}` : undefined}
        />
        <StatCard
          label="Risco Amarelo"
          value={String(yellow.total)}
          tone="warning"
          tooltip={yellow.total > 0 ? `Score medio: ${avg_yellow_score.toFixed(0)}` : undefined}
        />
        <StatCard
          label="MRR em Risco"
          value={formatCurrency(mrr_at_risk)}
          tone="neutral"
          tooltip="Receita mensal dos alunos em risco vermelho e amarelo"
        />
        <StatCard
          label="Forecast 60 dias"
          value={forecast60Avg !== null ? `${forecast60Avg}%` : "-"}
          tone={forecast60Avg === null ? "neutral" : forecast60Avg < 40 ? "danger" : forecast60Avg < 60 ? "warning" : "success"}
          tooltip="Probabilidade media de os alunos em risco vermelho permanecerem nos proximos 60 dias."
        />
      </div>

      {churnTotal > 0 ? (
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">
            Distribuicao de Churn
          </h3>
          <div className="space-y-2">
            {CHURN_ORDER.filter((key) => churnCounts[key]).map((key) => {
              const pct = churnTotal > 0 ? Math.round((churnCounts[key] / churnTotal) * 100) : 0;
              const toneClass = {
                danger: "bg-lovable-danger/20",
                warning: "bg-lovable-warning/20",
                info: "bg-lovable-primary/20",
                neutral: "bg-lovable-surface-soft",
              }[CHURN_LABELS[key].tone] ?? "bg-lovable-surface-soft";

              return (
                <div key={key} className="flex items-center gap-3">
                  <span className="w-36 shrink-0 text-xs text-lovable-ink-muted">{CHURN_LABELS[key].label}</span>
                  <div className="h-2 flex-1 overflow-hidden rounded-full bg-lovable-border">
                    <div className={`h-2 rounded-full ${toneClass} transition-all`} style={{ width: `${pct}%` }} />
                  </div>
                  <span className="w-16 shrink-0 text-right text-xs font-semibold text-lovable-ink">
                    {churnCounts[key]} alunos
                  </span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <RiskPanel
          tone="danger"
          label="Alunos em Vermelho"
          count={red.total}
          avgScore={avg_red_score}
          members={redItems}
          lastContactMap={last_contact_map}
          onTimeline={setSelectedMember}
          onActionComplete={handleActionComplete}
        />
        <RiskPanel
          tone="warning"
          label="Alunos em Amarelo"
          count={yellow.total}
          avgScore={avg_yellow_score}
          members={yellowItems}
          lastContactMap={last_contact_map}
          onTimeline={setSelectedMember}
          onActionComplete={handleActionComplete}
        />
      </div>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-1 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">
          Evolucao NPS
        </h3>
        <p className="mb-3 text-xs text-lovable-ink-muted">
          Score medio de satisfacao dos alunos nos ultimos meses.
        </p>
        <LineSeriesChart data={nps_trend} xKey="month" yKey="average_score" />
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">
          Alertas Ativos (Vermelho)
        </h3>
        {alertsQuery.isLoading ? (
          <p className="text-sm text-lovable-ink-muted">Carregando alertas...</p>
        ) : (alertsQuery.data?.items ?? []).length === 0 ? (
          <p className="text-sm text-lovable-ink-muted">Nenhum alerta ativo no momento.</p>
        ) : (
          <div className="space-y-2">
            {(alertsQuery.data?.items ?? []).map((alert) => {
              const actionCount = Array.isArray(alert.action_history) ? alert.action_history.length : 0;
              return (
                <article key={alert.id} className="rounded-lg border border-lovable-border p-3">
                  <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
                    <div>
                      <p className="text-sm font-semibold text-lovable-ink">
                        {memberById[alert.member_id] ?? `Alerta ${alert.id.slice(0, 8)}`}
                        <span className="ml-2 text-xs font-normal text-lovable-ink-muted">
                          Score {alert.score}
                        </span>
                      </p>
                      <p className="text-xs text-lovable-ink-muted">
                        {actionCount} acao
                        {actionCount !== 1 ? "es" : ""} registrada
                        {actionCount !== 1 ? "s" : ""} ·{" "}
                        {new Date(alert.created_at).toLocaleString("pt-BR")}
                      </p>
                    </div>
                    <button
                      type="button"
                      onClick={() => resolveMutation.mutate(alert.id)}
                      disabled={pendingAlertId === alert.id}
                      className="shrink-0 rounded-full bg-lovable-success px-3 py-1 text-xs font-semibold uppercase tracking-wider text-white hover:opacity-90 disabled:opacity-60"
                    >
                      Marcar resolvido
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>

      {selectedMember && (
        <MemberTimeline member={selectedMember} onClose={() => setSelectedMember(null)} />
      )}
    </section>
  );
}
