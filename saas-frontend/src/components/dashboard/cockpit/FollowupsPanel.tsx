import { ArrowRight, UserPlus } from "lucide-react";
import { useNavigate } from "react-router-dom";

import type { CockpitLeadFollowup } from "../../../types/cockpit";
import { PremiumEmptyState, SectionHeader, StatusPill } from "../../ui2";

const STAGE_LABELS: Record<string, string> = {
  new: "Novo",
  contact: "Em contato",
  visit: "Visita",
  trial: "Experimental",
  proposal: "Proposta",
  meeting_scheduled: "Reunião marcada",
  proposal_sent: "Proposta enviada",
};

export interface FollowupsPanelProps {
  items: CockpitLeadFollowup[];
  total: number;
}

export function FollowupsPanel({ items, total }: FollowupsPanelProps) {
  const navigate = useNavigate();

  return (
    <div className="flex h-full flex-col rounded-[24px] border border-lovable-border/70 bg-lovable-surface/62 p-4">
      <SectionHeader title="Follow-ups de leads" count={total} className="mb-3" />
      {items.length === 0 ? (
        <PremiumEmptyState icon={UserPlus} title="Nenhum lead esperando resposta" className="min-h-[140px] flex-1" />
      ) : (
        <div className="flex flex-1 flex-col divide-y divide-lovable-border/50">
          {items.map((item) => (
            <button
              key={item.lead_id}
              type="button"
              onClick={() => navigate(item.href)}
              className="flex w-full items-start justify-between gap-3 py-2.5 text-left transition first:pt-0 last:pb-0 hover:bg-lovable-surface-soft/50"
            >
              <span className="min-w-0">
                <span className="block truncate text-sm font-semibold text-lovable-ink">{item.full_name}</span>
                <span className="mt-0.5 block text-xs leading-relaxed text-lovable-ink-muted">{item.reason}</span>
              </span>
              <span className="flex shrink-0 items-center gap-2">
                <StatusPill tone="sync">{STAGE_LABELS[item.stage] ?? item.stage}</StatusPill>
                <ArrowRight size={14} className="text-lovable-ink-muted" />
              </span>
            </button>
          ))}
          {total > items.length ? (
            <button
              type="button"
              onClick={() => navigate("/crm")}
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
