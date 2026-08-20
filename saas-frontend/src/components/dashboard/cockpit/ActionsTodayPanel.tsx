import { ArrowRight, CheckSquare, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type { CockpitActionToday } from "../../../types/cockpit";
import { PremiumEmptyState, SectionHeader, StatusPill, cn } from "../../ui2";

const PRIORITY_LABELS: Record<string, string> = {
  urgent: "Urgente",
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

export interface ActionsTodayPanelProps {
  items: CockpitActionToday[];
  total: number;
  triagePendingCount: number;
}

export function ActionsTodayPanel({ items, total, triagePendingCount }: ActionsTodayPanelProps) {
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col rounded-[24px] border border-lovable-border/70 bg-lovable-surface/62 p-4">
      <SectionHeader
        title="Ações do dia"
        count={total}
        className="mb-3"
        actions={
          triagePendingCount > 0 ? (
            <button type="button" onClick={() => navigate("/ai/triage")} title="Abrir Central Cordex">
              <StatusPill tone="ai" dot>
                <Sparkles size={11} className="mr-1 inline" />
                Central Cordex: {triagePendingCount}
              </StatusPill>
            </button>
          ) : undefined
        }
      />
      {items.length === 0 ? (
        <PremiumEmptyState icon={CheckSquare} title="Nenhuma ação pendente pra hoje" className="min-h-[140px] flex-1" />
      ) : (
        <div className="flex flex-1 flex-col divide-y divide-lovable-border/50">
          {items.map((item) => (
            <button
              key={item.task_id}
              type="button"
              onClick={() => navigate(item.href)}
              className="flex w-full items-start justify-between gap-3 py-2.5 text-left transition first:pt-0 last:pb-0 hover:bg-lovable-surface-soft/50"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-lovable-ink">{item.title}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-lovable-ink-muted">
                  {item.target_name ? `${item.target_name} · ` : ""}
                  Prioridade {PRIORITY_LABELS[item.priority] ?? item.priority}
                </span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <StatusPill
                  tone={item.overdue ? "critical" : "normal"}
                  dot={item.overdue}
                  className={cn(item.overdue && "animate-pi-pulse")}
                >
                  {item.overdue ? "Atrasada" : "Hoje"}
                </StatusPill>
                <ArrowRight size={14} className="text-lovable-ink-muted" />
              </span>
            </button>
          ))}
          {total > items.length ? (
            <button
              type="button"
              onClick={() => navigate("/tasks")}
              className="mt-auto pt-1 text-left text-xs font-semibold text-blue-300 transition hover:text-blue-200"
            >
              Ver todas ({total})
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}
