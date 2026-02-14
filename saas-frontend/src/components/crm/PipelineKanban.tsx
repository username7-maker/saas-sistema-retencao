import { useMemo } from "react";

import type { Lead } from "../../types";

interface PipelineKanbanProps {
  leads: Lead[];
  onMove: (leadId: string, stage: Lead["stage"]) => void;
}

const COLUMNS: Array<{ key: Lead["stage"]; label: string }> = [
  { key: "new", label: "Novo" },
  { key: "contact", label: "Contato" },
  { key: "visit", label: "Visita" },
  { key: "trial", label: "Experimental" },
  { key: "proposal", label: "Proposta" },
  { key: "won", label: "Fechado" },
  { key: "lost", label: "Perdido" },
];

const NEXT_STAGE: Record<Lead["stage"], Lead["stage"] | null> = {
  new: "contact",
  contact: "visit",
  visit: "trial",
  trial: "proposal",
  proposal: "won",
  won: null,
  lost: null,
};

export function PipelineKanban({ leads, onMove }: PipelineKanbanProps) {
  const grouped = useMemo(() => {
    return COLUMNS.reduce<Record<string, Lead[]>>((acc, column) => {
      acc[column.key] = leads.filter((lead) => lead.stage === column.key);
      return acc;
    }, {});
  }, [leads]);

  return (
    <div className="grid gap-4 overflow-x-auto pb-3 md:grid-cols-2 xl:grid-cols-4 2xl:grid-cols-7">
      {COLUMNS.map((column) => (
        <section key={column.key} className="min-h-[260px] rounded-2xl border border-slate-200 bg-white p-3 shadow-panel">
          <header className="mb-3 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">{column.label}</h3>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-500">
              {grouped[column.key].length}
            </span>
          </header>
          <div className="space-y-3">
            {grouped[column.key].map((lead) => {
              const nextStage = NEXT_STAGE[lead.stage];
              return (
                <article key={lead.id} className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                  <p className="text-sm font-semibold text-slate-800">{lead.full_name}</p>
                  <p className="mt-1 text-xs text-slate-500">Origem: {lead.source}</p>
                  <p className="text-xs text-slate-500">Valor estimado: R$ {lead.estimated_value}</p>
                  {nextStage && (
                    <button
                      type="button"
                      onClick={() => onMove(lead.id, nextStage)}
                      className="mt-3 rounded-lg bg-brand-500 px-2 py-1 text-xs font-semibold text-white hover:bg-brand-700"
                    >
                      Avancar
                    </button>
                  )}
                </article>
              );
            })}
          </div>
        </section>
      ))}
    </div>
  );
}
