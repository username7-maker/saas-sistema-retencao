import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { PipelineKanban } from "../../components/crm/PipelineKanban";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { crmService } from "../../services/crmService";
import type { Lead } from "../../types";

export function CrmPage() {
  const queryClient = useQueryClient();
  const leadsQuery = useQuery({
    queryKey: ["crm", "leads"],
    queryFn: crmService.listLeads,
    staleTime: 5 * 60 * 1000,
  });

  const moveMutation = useMutation({
    mutationFn: ({ leadId, stage }: { leadId: string; stage: Lead["stage"] }) => crmService.updateLeadStage(leadId, stage),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["crm", "leads"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "commercial"] });
    },
  });

  if (leadsQuery.isLoading) {
    return <LoadingPanel text="Carregando CRM..." />;
  }

  if (!leadsQuery.data) {
    return <LoadingPanel text="Nao foi possivel carregar leads." />;
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-slate-900">CRM - Pipeline Kanban</h2>
        <p className="text-sm text-slate-500">Novo, Contato, Visita, Experimental, Proposta, Fechado/Perdido.</p>
      </header>

      {moveMutation.isPending && (
        <p className="rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700">Atualizando estagio...</p>
      )}

      <PipelineKanban
        leads={leadsQuery.data.items}
        onMove={(leadId, stage) => {
          moveMutation.mutate({ leadId, stage });
        }}
      />
    </section>
  );
}
