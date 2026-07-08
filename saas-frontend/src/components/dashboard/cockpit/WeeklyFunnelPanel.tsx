import { BarChart3, Minus, TrendingDown, TrendingUp } from "lucide-react";

import type { WeeklyFunnelResponse } from "../../../types/cockpit";
import { PremiumEmptyState, SectionHeader, cn } from "../../ui2";

export interface WeeklyFunnelPanelProps {
  funnel: WeeklyFunnelResponse;
}

function Delta({ value, previous }: { value: number; previous: number }) {
  const delta = value - previous;
  if (delta > 0) {
    return (
      <span className="flex items-center gap-1 text-xs font-semibold text-emerald-300">
        <TrendingUp size={13} /> +{delta}
      </span>
    );
  }
  if (delta < 0) {
    return (
      <span className="flex items-center gap-1 text-xs font-semibold text-rose-300">
        <TrendingDown size={13} /> {delta}
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-xs font-semibold text-lovable-ink-muted">
      <Minus size={13} /> 0
    </span>
  );
}

export function WeeklyFunnelPanel({ funnel }: WeeklyFunnelPanelProps) {
  const stages = [funnel.contacts, funnel.responses, funnel.conversions];
  const isEmpty = stages.every((stage) => stage.value === 0);
  const { leads_won, members_joined, risk_recovered } = funnel.conversion_breakdown;

  return (
    <div className="flex h-full flex-col rounded-[24px] border border-lovable-border/70 bg-lovable-surface/62 p-4">
      <SectionHeader title="Funil da semana" subtitle="vs. semana anterior" className="mb-3" />
      {isEmpty ? (
        <PremiumEmptyState icon={BarChart3} title="Sem atividade registrada nesta semana" className="min-h-[140px] flex-1" />
      ) : (
        <div className="flex flex-1 flex-col justify-center gap-3">
          {stages.map((stage, index) => (
            <div
              key={stage.key}
              className={cn(
                "flex items-center justify-between gap-3 rounded-2xl border border-lovable-border/65 bg-lovable-surface/58 px-3 py-2.5",
                index === 2 && "border-blue-400/25 bg-blue-400/[0.06]",
              )}
            >
              <span className="text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
                {stage.label}
              </span>
              <span className="flex items-center gap-3">
                <Delta value={stage.value} previous={stage.previous_value} />
                <span className="font-heading text-2xl font-extrabold tracking-tight text-lovable-ink">
                  {stage.value.toLocaleString("pt-BR")}
                </span>
              </span>
            </div>
          ))}
          <p className="text-xs leading-relaxed text-lovable-ink-muted">
            {leads_won} venda(s) · {members_joined} novo(s) aluno(s) · {risk_recovered} recuperado(s)
          </p>
        </div>
      )}
    </div>
  );
}
