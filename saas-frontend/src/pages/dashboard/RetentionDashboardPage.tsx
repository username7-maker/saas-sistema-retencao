import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
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
};

type ChurnKey = "frequencia" | "frustracao" | "lifestyle" | "financeiro";

const CHURN_META: Record<ChurnKey, { label: string; emoji: string; color: string; bg: string; desc: string }> = {
  frequencia: { label: "Churn de frequencia", emoji: "🏃", color: "#C0392B", bg: "#FCEBEB", desc: "Treinou, parou. Rotina quebrou." },
  frustracao: { label: "Churn de frustracao", emoji: "😤", color: "#BA7517", bg: "#FAEEDA", desc: "Ainda treina, mas o resultado nao apareceu." },
  lifestyle: { label: "Churn de estilo de vida", emoji: "🔄", color: "#185FA5", bg: "#E6F1FB", desc: "Mudou turno, cidade ou ritmo de trabalho." },
  financeiro: { label: "Churn financeiro", emoji: "💰", color: "#0F7553", bg: "#E1F5EE", desc: "Preco virou objecao com frequencia ainda saudavel." },
};

const PLAYBOOK_ACTIONS: Record<ChurnKey, Array<{ day: string; badge: string; title: string; desc: string }>> = {
  frequencia: [
    { day: "D3", badge: "automatico", title: "E-mail com dado de progresso", desc: "Claude usa dados da ultima avaliacao para mostrar o que o aluno perdeu sem tom de cobranca." },
    { day: "D7", badge: "consultor", title: "Ligacao com script contextual", desc: "Script combina historico de frequencia, ultima avaliacao e pergunta aberta sobre a rotina." },
    { day: "D10", badge: "automatico", title: "Oferta de horario alternativo", desc: "Sugestao de horario com menor movimento para remover a barreira de tempo percebida." },
    { day: "D14", badge: "gerente", title: "Decisao: pausa ou cortesia", desc: "Forecast abaixo de 40% apos 14 dias aciona decisao humana para segurar o LTV." },
  ],
  frustracao: [
    { day: "D1", badge: "urgente", title: "Diagnostico de frustracao", desc: "NPS baixo com risco alto pede ligacao no mesmo dia." },
    { day: "D3", badge: "consultor", title: "Mostrar progresso real com dados", desc: "Comparar avaliacoes reduz a distancia entre percepcao e resultado real." },
    { day: "D5", badge: "coach", title: "Revisar meta e expectativa", desc: "Professor redefine meta e expectativa com base no ritmo real do aluno." },
  ],
  lifestyle: [
    { day: "D2", badge: "automatico", title: "Detectar mudanca de rotina", desc: "A abordagem comeca por curiosidade sobre o que mudou no dia a dia." },
    { day: "D5", badge: "coach", title: "Protocolo express 45 min", desc: "Trocar o formato de treino e manter resultado com menos tempo por sessao." },
    { day: "D14", badge: "gerente", title: "Pausa estrategica", desc: "Pausar 30 dias pode ser melhor do que perder o aluno em definitivo." },
  ],
  financeiro: [
    { day: "D2", badge: "consultor", title: "Comparativo de custo por treino", desc: "Mostrar valor por sessao versus alternativas de maior custo." },
    { day: "D5", badge: "gerente", title: "Proposta de plano trimestral", desc: "Desconto menor com compromisso menor para reduzir friccao de preco." },
    { day: "D7", badge: "gerente", title: "Upgrade de fidelidade", desc: "Promotor com objecao de preco vira candidato a anual com mensalidade menor." },
  ],
};

function isChurnKey(value: string): value is ChurnKey {
  return value in CHURN_META;
}

function daysInactive(lastCheckinAt: string | null): number | null {
  if (!lastCheckinAt) return null;
  const date = new Date(lastCheckinAt);
  if (Number.isNaN(date.getTime())) return null;
  const diff = Math.floor((Date.now() - date.getTime()) / 86400000);
  return diff >= 0 ? diff : null;
}

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function badgeClass(badge: string): string {
  if (badge === "urgente") return "bg-red-100 text-red-700";
  if (badge === "gerente") return "bg-purple-100 text-purple-700";
  if (badge === "coach") return "bg-blue-100 text-blue-700";
  if (badge === "consultor") return "bg-indigo-100 text-indigo-700";
  return "bg-green-100 text-green-700";
}

function SignalsPanel({ member }: { member: RetentionMember }) {
  const days = daysInactive(member.last_checkin_at);
  const forecastValue = member.extra_data?.retention_forecast_60d;
  const forecast = typeof forecastValue === "number" && forecastValue >= 0 && forecastValue <= 100 ? forecastValue : null;
  const nps = member.nps_last_score > 0 ? member.nps_last_score : null;

  const signals: Array<{ label: string; icon: string; value: string; barPct: number; isDanger: boolean; isWarn: boolean }> = [];

  if (days !== null) {
    signals.push({
      label: "Dias sem check-in",
      icon: "📅",
      value: `${days} dias`,
      barPct: Math.min(100, (days / 30) * 100),
      isDanger: days >= 14,
      isWarn: days >= 7 && days < 14,
    });
  }

  signals.push({
    label: "Risk score",
    icon: "📉",
    value: String(member.risk_score ?? "—"),
    barPct: Math.min(100, member.risk_score ?? 0),
    isDanger: (member.risk_score ?? 0) >= 70,
    isWarn: (member.risk_score ?? 0) >= 40 && (member.risk_score ?? 0) < 70,
  });

  if (forecast !== null) {
    signals.push({
      label: "Forecast 60d",
      icon: "🔮",
      value: `${forecast}%`,
      barPct: forecast,
      isDanger: forecast < 40,
      isWarn: forecast >= 40 && forecast < 60,
    });
  }

  if (nps !== null) {
    signals.push({
      label: "Ultimo NPS",
      icon: "⭐",
      value: String(nps),
      barPct: (nps / 10) * 100,
      isDanger: nps <= 6,
      isWarn: nps === 7,
    });
  }

  if (signals.length === 0) {
    return <p className="text-xs text-lovable-ink-muted">Sinais nao disponiveis para este aluno.</p>;
  }

  return (
    <div className="space-y-2.5">
      {signals.map((signal) => (
        <div key={signal.label}>
          <div className="mb-1 flex items-center justify-between">
            <span className="text-xs text-lovable-ink">
              {signal.icon} {signal.label}
            </span>
            <span
              className={clsx(
                "text-xs font-semibold",
                signal.isDanger ? "text-red-600" : signal.isWarn ? "text-yellow-600" : "text-green-700",
              )}
            >
              {signal.value}
            </span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-lovable-border">
            <div
              className={clsx(
                "h-1.5 rounded-full transition-all",
                signal.isDanger ? "bg-[#C0392B]" : signal.isWarn ? "bg-[#BA7517]" : "bg-[#0F7553]",
              )}
              style={{ width: `${signal.barPct}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function PlaybookPanel({ member }: { member: RetentionMember }) {
  const churnKey: ChurnKey = member.churn_type && isChurnKey(member.churn_type) ? member.churn_type : "frequencia";
  const meta = CHURN_META[churnKey];
  const actions = PLAYBOOK_ACTIONS[churnKey];

  return (
    <div className="overflow-hidden rounded-2xl border bg-lovable-surface" style={{ borderColor: `${meta.color}30` }}>
      <div className="border-b px-4 py-3" style={{ background: meta.bg, borderColor: `${meta.color}30` }}>
        <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: meta.color }}>
          Playbook de retencao gerado
        </p>
        <p className="mt-0.5 text-xs" style={{ color: meta.color }}>
          {meta.emoji} {meta.label} - {meta.desc}
        </p>
      </div>
      <div className="divide-y divide-lovable-border">
        {actions.map((action, index) => (
          <div key={index} className="flex gap-3 p-3">
            <div className="flex shrink-0 flex-col items-center gap-1 pt-0.5">
              <span className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ background: meta.bg, color: meta.color }}>
                {action.day}
              </span>
              {index < actions.length - 1 ? <div className="min-h-3 w-px flex-1" style={{ background: `${meta.color}30` }} /> : null}
            </div>
            <div className="min-w-0 flex-1 pb-1">
              <div className="mb-0.5 flex flex-wrap items-center gap-2">
                <p className="text-xs font-semibold text-lovable-ink">{action.title}</p>
                <span className={clsx("shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide", badgeClass(action.badge))}>
                  {action.badge}
                </span>
              </div>
              <p className="text-[11px] leading-relaxed text-lovable-ink-muted">{action.desc}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function RetentionDashboardPage() {
  const queryClient = useQueryClient();
  const [selectedMember, setSelectedMember] = useState<RetentionMember | null>(null);
  const [timelineMember, setTimelineMember] = useState<Member | null>(null);
  const [pendingAlertId, setPendingAlertId] = useState<string | null>(null);
  const query = useRetentionDashboard();

  const alertsQuery = useQuery({
    queryKey: ["risk-alerts", "unresolved-red"],
    queryFn: () => riskAlertService.listUnresolved("red"),
    staleTime: 60_000,
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
    onError: () => toast.error("Falha ao resolver alerta."),
    onSettled: () => setPendingAlertId(null),
  });

  const handleActionComplete = () => {
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "retention"] });
  };

  if (query.isLoading) return <LoadingPanel text="Carregando Retention Intelligence..." />;
  if (query.isError || !query.data) return <LoadingPanel text="Erro ao carregar dados de retencao." />;

  const red = query.data.red ?? { total: 0, items: [] };
  const yellow = query.data.yellow ?? { total: 0, items: [] };
  const npsTrend = query.data.nps_trend ?? [];
  const mrrAtRisk = Number(query.data.mrr_at_risk ?? 0);
  const avgRedScore = Number(query.data.avg_red_score ?? 0);
  const avgYellowScore = Number(query.data.avg_yellow_score ?? 0);

  const redItems = red.items as RetentionMember[];
  const yellowItems = yellow.items as RetentionMember[];
  const allAtRisk = [...redItems, ...yellowItems];

  const churnCounts = useMemo(() => {
    const counts: Partial<Record<ChurnKey, number>> = {};
    for (const member of allAtRisk) {
      const churnType = member.churn_type;
      if (churnType && isChurnKey(churnType)) {
        counts[churnType] = (counts[churnType] ?? 0) + 1;
      }
    }
    return counts;
  }, [allAtRisk]);

  const churnTotal = Object.values(churnCounts).reduce((sum, value) => sum + (value ?? 0), 0);

  const forecast60Avg = useMemo(() => {
    const values = redItems
      .map((member) => {
        const value = member.extra_data?.retention_forecast_60d;
        return typeof value === "number" && value >= 0 && value <= 100 ? value : null;
      })
      .filter((value): value is number => value !== null);

    return values.length === 0 ? null : Math.round(values.reduce((sum, value) => sum + value, 0) / values.length);
  }, [redItems]);

  const memberById: Record<string, string> = {};
  for (const member of allAtRisk) {
    memberById[member.id] = member.full_name;
  }

  const activeSelected = selectedMember ?? redItems[0] ?? yellowItems[0] ?? null;

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Dashboard de Retencao</h2>
          <p className="text-sm text-lovable-ink-muted">
            O sistema identifica o tipo de churn e personaliza a intervencao. Hoje todos recebem o mesmo e-mail no D3.
          </p>
        </div>
        <DashboardActions dashboard="retention" />
      </header>

      <AiInsightCard dashboard="retention" />

      <div className="grid gap-4 md:grid-cols-4">
        <StatCard
          label="Risco Vermelho"
          value={String(red.total)}
          tone="danger"
          tooltip={red.total > 0 ? `Score medio: ${avgRedScore.toFixed(0)}` : undefined}
        />
        <StatCard
          label="Risco Amarelo"
          value={String(yellow.total)}
          tone="warning"
          tooltip={yellow.total > 0 ? `Score medio: ${avgYellowScore.toFixed(0)}` : undefined}
        />
        <StatCard
          label="MRR em Risco"
          value={formatCurrency(mrrAtRisk)}
          tone="neutral"
          tooltip="Receita mensal dos alunos em risco."
        />
        <StatCard
          label="Forecast 60 dias"
          value={forecast60Avg !== null ? `${forecast60Avg}%` : "—"}
          tone={forecast60Avg === null ? "neutral" : forecast60Avg < 40 ? "danger" : forecast60Avg < 60 ? "warning" : "success"}
          tooltip="Probabilidade media de permanencia dos alunos vermelhos."
        />
      </div>

      {churnTotal > 0 ? (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {(Object.keys(CHURN_META) as ChurnKey[]).map((key) => {
            const meta = CHURN_META[key];
            const count = churnCounts[key] ?? 0;
            const pct = churnTotal > 0 ? Math.round((count / churnTotal) * 100) : 0;
            return (
              <button
                key={key}
                type="button"
                className="rounded-2xl border p-4 text-left transition-all hover:shadow-sm"
                style={{ borderColor: `${meta.color}30`, background: meta.bg }}
                onClick={() => {
                  const member = allAtRisk.find((item) => item.churn_type === key);
                  if (member) setSelectedMember(member);
                }}
              >
                <p className="mb-1 text-xl">{meta.emoji}</p>
                <p className="mb-0.5 text-xs font-semibold text-lovable-ink">{meta.label}</p>
                <p className="mb-2 text-[11px] leading-relaxed text-lovable-ink-muted">{meta.desc}</p>
                <p className="text-2xl font-bold" style={{ color: meta.color }}>
                  {pct}%
                </p>
                <p className="text-[10px]" style={{ color: meta.color }}>
                  {count} alunos
                </p>
              </button>
            );
          })}
        </div>
      ) : null}

      {allAtRisk.length > 0 ? (
        <div className="overflow-hidden rounded-2xl border border-lovable-border bg-lovable-surface">
          <div className="flex flex-wrap items-center gap-2 border-b border-lovable-border bg-lovable-surface-soft px-4 py-3">
            <span className="shrink-0 text-xs font-semibold text-lovable-ink-muted">Perfil de aluno:</span>
            {allAtRisk.slice(0, 5).map((member) => {
              const meta = member.churn_type && isChurnKey(member.churn_type) ? CHURN_META[member.churn_type] : null;
              const isActive = activeSelected?.id === member.id;
              return (
                <button
                  key={member.id}
                  type="button"
                  onClick={() => setSelectedMember(member)}
                  className={clsx(
                    "rounded-full border px-3 py-1 text-xs font-semibold transition-all",
                    isActive ? "border-2" : "border-lovable-border bg-lovable-surface text-lovable-ink hover:border-lovable-ink/30",
                  )}
                  style={isActive && meta ? { borderColor: meta.color, background: meta.bg, color: meta.color } : undefined}
                >
                  {member.full_name.split(" ")[0]} · {member.plan_name?.split(" ")[0] ?? "—"} · {member.loyalty_months}m
                </button>
              );
            })}
          </div>

          {activeSelected ? (
            <div className="grid gap-0 md:grid-cols-2">
              <div className="border-r border-lovable-border p-4">
                <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">
                  Sinais captados pelo sistema
                </p>
                <SignalsPanel member={activeSelected} />
                <div className="mt-4 border-t border-lovable-border pt-3">
                  <button
                    type="button"
                    onClick={() => setTimelineMember(activeSelected)}
                    className="mr-2 mb-2 rounded-full border border-lovable-border px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted transition hover:border-lovable-border-strong hover:text-lovable-ink"
                  >
                    Ver timeline 360
                  </button>
                  <QuickActions member={activeSelected} onActionComplete={handleActionComplete} />
                </div>
              </div>
              <div className="p-4">
                <PlaybookPanel member={activeSelected} />
              </div>
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="grid gap-4 xl:grid-cols-2">
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-1 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Evolucao NPS</h3>
          <p className="mb-3 text-xs text-lovable-ink-muted">Score medio de satisfacao nos ultimos meses.</p>
          <LineSeriesChart data={npsTrend} xKey="month" yKey="average_score" />
        </section>

        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Alertas Ativos (Vermelho)</h3>
          {alertsQuery.isLoading ? (
            <p className="text-sm text-lovable-ink-muted">Carregando alertas...</p>
          ) : (alertsQuery.data?.items ?? []).length === 0 ? (
            <p className="text-sm text-lovable-ink-muted">Nenhum alerta ativo.</p>
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
                          <span className="ml-2 text-xs font-normal text-lovable-ink-muted">Score {alert.score}</span>
                        </p>
                        <p className="text-xs text-lovable-ink-muted">
                          {actionCount} acao{actionCount !== 1 ? "es" : ""} · {new Date(alert.created_at).toLocaleString("pt-BR")}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => resolveMutation.mutate(alert.id)}
                        disabled={pendingAlertId === alert.id}
                        className="shrink-0 rounded-full bg-lovable-success px-3 py-1 text-xs font-semibold uppercase text-white hover:opacity-90 disabled:opacity-60"
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
      </div>

      {timelineMember ? <MemberTimeline member={timelineMember} onClose={() => setTimelineMember(null)} /> : null}
    </section>
  );
}
