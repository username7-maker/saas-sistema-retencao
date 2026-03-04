import { useState } from "react";
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
  if (days === 1) return "há 1 dia";
  return `há ${days} dias`;
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
  // nps_last_score: backend defaults to 0.0 when no NPS response exists, so > 0 is the "scored" guard
  if (member.nps_last_score > 0 && member.nps_last_score < 7) chips.push({ label: "NPS Baixo", color: "warning" });
  // loyalty_months: backend computes this from join_date; 0 can mean brand-new member
  if (member.loyalty_months < 2) chips.push({ label: "Novo", color: "info" });
  return chips;
}

interface MemberCardProps {
  member: Member;
  lastContactMap: Record<string, string>;
  onTimeline: (m: Member) => void;
  onActionComplete: () => void;
}

function MemberCard({ member, lastContactMap, onTimeline, onActionComplete }: MemberCardProps) {
  const days = daysInactive(member.last_checkin_at);
  const chips = computeRiskChips(member);
  const hasContact = Boolean(lastContactMap[member.id]);
  const lastContactLabel = formatLastContact(lastContactMap, member.id);

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
            {days === 0 ? "Treinou hoje" : `Há ${days} dia${days !== 1 ? "s" : ""} sem treinar`}
          </span>
        ) : (
          <span className="text-xs text-lovable-ink-muted">Sem check-in registrado</span>
        )}
      </div>

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

      <p
        className={`mt-2 text-[11px] ${
          hasContact ? "text-lovable-ink-muted" : "font-semibold text-lovable-warning"
        }`}
      >
        {hasContact ? `Último contato: ${lastContactLabel}` : "⚠ Nunca contatado"}
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
  members: Member[];
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

  return (
    <section className={`rounded-2xl border ${borderCls} bg-lovable-surface p-4 shadow-panel`}>
      <div className="mb-4 flex items-center justify-between">
        <h3 className={`text-sm font-semibold uppercase tracking-wider ${headingCls}`}>
          {label} ({count})
        </h3>
        {count > 0 && (
          <span className="text-xs text-lovable-ink-muted">
            Score médio:{" "}
            <strong className="text-lovable-ink">{avgScore.toFixed(0)}</strong>
          </span>
        )}
      </div>
      {members.length === 0 ? (
        <p className="text-sm text-lovable-ink-muted">Nenhum aluno neste nível de risco.</p>
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
      return riskAlertService.resolve(alertId, "Resolvido no dashboard de retenção");
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

  if (query.isLoading) return <LoadingPanel text="Carregando dashboard de retenção..." />;
  if (query.isError) return <LoadingPanel text="Erro ao carregar dados de retenção." />;
  if (!query.data) return <LoadingPanel text="Sem dados de retenção." />;

  const red = query.data.red ?? { total: 0, items: [] };
  const yellow = query.data.yellow ?? { total: 0, items: [] };
  const nps_trend = query.data.nps_trend ?? [];
  const mrr_at_risk = Number(query.data.mrr_at_risk ?? 0);
  const avg_red_score = Number(query.data.avg_red_score ?? 0);
  const avg_yellow_score = Number(query.data.avg_yellow_score ?? 0);
  const last_contact_map = query.data.last_contact_map ?? {};
  const totalRisk = red.total + yellow.total;

  // Build member-id → name map for alert section
  const memberById: Record<string, string> = {};
  for (const m of [...red.items, ...yellow.items]) {
    memberById[m.id] = m.full_name;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard de Retenção</h2>
          <p className="text-sm text-lovable-ink-muted">
            Alunos em risco, evolução NPS e ações de retenção.
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
            {" — ação imediata recomendada."}
          </p>
        </div>
      )}

      {/* KPI tiles */}
      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="Risco Vermelho"
          value={String(red.total)}
          tone="danger"
          tooltip={red.total > 0 ? `Score médio: ${avg_red_score.toFixed(0)}` : undefined}
        />
        <StatCard
          label="Risco Amarelo"
          value={String(yellow.total)}
          tone="warning"
          tooltip={yellow.total > 0 ? `Score médio: ${avg_yellow_score.toFixed(0)}` : undefined}
        />
        <StatCard
          label="MRR em Risco"
          value={formatCurrency(mrr_at_risk)}
          tone="neutral"
          tooltip="Receita mensal dos alunos em risco vermelho e amarelo"
        />
      </div>

      {/* Member panels */}
      <div className="grid gap-4 xl:grid-cols-2">
        <RiskPanel
          tone="danger"
          label="Alunos em Vermelho"
          count={red.total}
          avgScore={avg_red_score}
          members={red.items}
          lastContactMap={last_contact_map}
          onTimeline={setSelectedMember}
          onActionComplete={handleActionComplete}
        />
        <RiskPanel
          tone="warning"
          label="Alunos em Amarelo"
          count={yellow.total}
          avgScore={avg_yellow_score}
          members={yellow.items}
          lastContactMap={last_contact_map}
          onTimeline={setSelectedMember}
          onActionComplete={handleActionComplete}
        />
      </div>

      {/* NPS Evolution chart */}
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-1 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">
          Evolução NPS
        </h3>
        <p className="mb-3 text-xs text-lovable-ink-muted">
          Score médio de satisfação dos alunos nos últimos meses.
        </p>
        <LineSeriesChart data={nps_trend} xKey="month" yKey="average_score" />
      </section>

      {/* Active alerts */}
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
                        {actionCount} ação
                        {actionCount !== 1 ? "ões" : ""} registrada
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
