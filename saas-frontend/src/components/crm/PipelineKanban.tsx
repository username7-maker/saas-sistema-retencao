import { useMemo } from "react";

import type { Lead } from "../../types";

interface PipelineKanbanProps {
  leads: Lead[];
  onMove: (leadId: string, stage: Lead["stage"]) => void;
  onCardClick?: (lead: Lead) => void;
}

const COLUMNS: Array<{ key: Lead["stage"]; label: string }> = [
  { key: "new", label: "Novo" },
  { key: "contact", label: "Contato" },
  { key: "visit", label: "Visita" },
  { key: "trial", label: "Experimental" },
  { key: "proposal", label: "Proposta" },
  { key: "meeting_scheduled", label: "Call agendada" },
  { key: "proposal_sent", label: "Proposta enviada" },
  { key: "won", label: "Fechado" },
  { key: "lost", label: "Perdido" },
];

const NEXT_STAGE: Record<Lead["stage"], Lead["stage"] | null> = {
  new: "contact",
  contact: "visit",
  visit: "trial",
  trial: "proposal",
  proposal: "meeting_scheduled",
  meeting_scheduled: "proposal_sent",
  proposal_sent: "won",
  won: null,
  lost: null,
};

const COLUMN_ACCENT: Record<Lead["stage"], string> = {
  new: "border-lovable-border",
  contact: "border-lovable-border",
  visit: "border-lovable-border",
  trial: "border-lovable-border",
  proposal: "border-lovable-warning/40",
  meeting_scheduled: "border-lovable-primary/40",
  proposal_sent: "border-lovable-primary/50",
  won: "border-lovable-success/40",
  lost: "border-lovable-danger/30",
};

const BRL = (value: number) =>
  new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 }).format(value);

function daysSince(isoDate: string | null | undefined): number | null {
  if (!isoDate) return null;
  return Math.floor((Date.now() - new Date(isoDate).getTime()) / 86_400_000);
}

export function PipelineKanban({ leads, onMove, onCardClick }: PipelineKanbanProps) {
  const grouped = useMemo(() => {
    return COLUMNS.reduce<Record<string, Lead[]>>((acc, column) => {
      acc[column.key] = leads.filter((lead) => lead.stage === column.key);
      return acc;
    }, {});
  }, [leads]);

  return (
    <div className="grid gap-4 overflow-x-auto pb-3 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-9">
      {COLUMNS.map((column) => {
        const colLeads = grouped[column.key];
        const totalValue = colLeads.reduce((sum, lead) => sum + (lead.estimated_value ?? 0), 0);

        return (
          <section
            key={column.key}
            className={`min-h-[260px] rounded-2xl border bg-lovable-surface p-3 shadow-panel ${COLUMN_ACCENT[column.key]}`}
          >
            <header className="mb-3 flex items-center justify-between gap-2">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">{column.label}</h3>
              <div className="flex flex-col items-end gap-0.5">
                <span className="rounded-full bg-lovable-surface-soft px-2 py-0.5 text-xs font-medium text-lovable-ink-muted">
                  {colLeads.length}
                </span>
                {totalValue > 0 && (
                  <span className="text-[10px] font-medium text-lovable-ink-muted">{BRL(totalValue)}</span>
                )}
              </div>
            </header>

            <div className="space-y-3">
              {colLeads.map((lead) => {
                const nextStage = NEXT_STAGE[lead.stage];
                const dias = daysSince(lead.last_contact_at);
                const isStale = dias !== null && dias > 3;

                return (
                  <article
                    key={lead.id}
                    className={`rounded-xl border border-lovable-border bg-lovable-surface-soft p-3 transition-colors ${
                      onCardClick ? "cursor-pointer hover:border-lovable-border-strong hover:bg-lovable-primary-soft/30" : ""
                    }`}
                    onClick={() => onCardClick?.(lead)}
                  >
                    <p className="text-sm font-semibold text-lovable-ink">{lead.full_name}</p>
                    {lead.phone && <p className="mt-1 text-xs text-lovable-ink-muted">{lead.phone}</p>}
                    <p className="mt-0.5 text-xs text-lovable-ink-muted">Origem: {lead.source ?? "—"}</p>
                    {(lead.estimated_value ?? 0) > 0 && (
                      <p className="mt-0.5 text-xs font-medium text-lovable-ink">
                        {BRL(lead.estimated_value ?? 0)}
                      </p>
                    )}
                    {dias !== null && (
                      <span
                        className={`mt-1.5 inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                          isStale
                            ? "bg-lovable-danger/15 text-lovable-danger"
                            : "bg-lovable-surface text-lovable-ink-muted"
                        }`}
                      >
                        {dias === 0 ? "Hoje" : `${dias}d sem contato`}
                      </span>
                    )}
                    {nextStage && (
                      <button
                        type="button"
                        onClick={(event) => { event.stopPropagation(); onMove(lead.id, nextStage); }}
                        className="mt-3 rounded-lg bg-lovable-primary px-2 py-1 text-xs font-semibold text-white hover:opacity-90"
                      >
                        Avançar
                      </button>
                    )}
                  </article>
                );
              })}
            </div>
          </section>
        );
      })}
    </div>
  );
}
