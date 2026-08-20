import { ArrowRight, ShieldAlert } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type { CockpitMemberAttention } from "../../../types/cockpit";
import { PremiumEmptyState, SectionHeader, StatusPill } from "../../ui2";

export interface AttentionPanelProps {
  items: CockpitMemberAttention[];
  total: number;
}

export function AttentionPanel({ items, total }: AttentionPanelProps) {
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col rounded-[24px] border border-lovable-border/70 bg-lovable-surface/62 p-4">
      <SectionHeader title="Alunos em atenção" count={total} className="mb-3" />
      {items.length === 0 ? (
        <PremiumEmptyState icon={ShieldAlert} title="Nenhum aluno em atenção agora" className="min-h-[140px] flex-1" />
      ) : (
        <div className="flex flex-1 flex-col divide-y divide-lovable-border/50">
          {items.map((item) => (
            <button
              key={item.member_id}
              type="button"
              onClick={() => navigate(item.href)}
              className="flex w-full items-start justify-between gap-3 py-2.5 text-left transition first:pt-0 last:pb-0 hover:bg-lovable-surface-soft/50"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-lovable-ink">{item.full_name}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-lovable-ink-muted">{item.reason}</span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <StatusPill tone={item.risk_level === "red" ? "critical" : "warning"} dot>
                  {item.risk_level === "red" ? "Crítico" : "Atenção"}
                </StatusPill>
                <ArrowRight size={14} className="text-lovable-ink-muted" />
              </span>
            </button>
          ))}
          {total > items.length ? (
            <button
              type="button"
              onClick={() => navigate("/dashboard/retention")}
              className="mt-auto pt-1 text-left text-xs font-semibold text-blue-300 transition hover:text-blue-200"
            >
              Ver todos ({total})
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}
