import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { PipelineKanban } from "../../components/crm/PipelineKanban";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { crmService } from "../../services/crmService";
import { Button, Drawer, Input } from "../../components/ui2";
import type { Lead } from "../../types";

// ─── Validation schema ────────────────────────────────────────────────────────

const leadSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  email: z.string().email("E-mail inválido").optional().or(z.literal("")),
  phone: z.string().optional(),
  source: z.string().optional(),
  estimated_value: z.coerce.number().min(0, "Valor não pode ser negativo").optional(),
  notes: z.string().optional(),
  lost_reason: z.string().optional(),
});

type LeadFormValues = z.infer<typeof leadSchema>;

// ─── Lead form drawer ─────────────────────────────────────────────────────────

interface LeadFormDrawerProps {
  open: boolean;
  onClose: () => void;
  lead?: Lead | null;
  onSaved: () => void;
}

function LeadFormDrawer({ open, onClose, lead, onSaved }: LeadFormDrawerProps) {
  const isEditing = Boolean(lead);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadSchema),
    defaultValues: lead
      ? {
          full_name: lead.full_name,
          email: lead.email ?? "",
          phone: lead.phone ?? "",
          source: lead.source ?? "",
          estimated_value: lead.estimated_value,
          lost_reason: lead.lost_reason ?? "",
        }
      : {},
  });

  const createMutation = useMutation({
    mutationFn: crmService.createLead,
    onSuccess: () => {
      toast.success("Lead criado com sucesso!");
      reset();
      onSaved();
      onClose();
    },
    onError: () => toast.error("Erro ao criar lead. Tente novamente."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: LeadFormValues }) =>
      crmService.updateLead(id, {
        ...data,
        email: data.email || undefined,
      }),
    onSuccess: () => {
      toast.success("Lead atualizado com sucesso!");
      onSaved();
      onClose();
    },
    onError: () => toast.error("Erro ao atualizar lead. Tente novamente."),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => crmService.deleteLead(id),
    onSuccess: () => {
      toast.success("Lead removido.");
      onSaved();
      onClose();
    },
    onError: () => toast.error("Erro ao remover lead."),
  });

  function onSubmit(values: LeadFormValues) {
    if (isEditing && lead) {
      updateMutation.mutate({ id: lead.id, data: values });
    } else {
      createMutation.mutate({
        full_name: values.full_name,
        email: values.email || undefined,
        phone: values.phone,
        source: values.source,
        estimated_value: values.estimated_value,
      });
    }
  }

  const isPending = isSubmitting || createMutation.isPending || updateMutation.isPending;

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={isEditing ? "Editar Lead" : "Novo Lead"}
    >
      <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 p-1">
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Nome *
          </label>
          <Input {...register("full_name")} placeholder="Nome completo" />
          {errors.full_name && (
            <p className="mt-1 text-xs text-red-500">{errors.full_name.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Telefone
          </label>
          <Input {...register("phone")} placeholder="(11) 99999-9999" />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            E-mail
          </label>
          <Input {...register("email")} type="email" placeholder="email@exemplo.com" />
          {errors.email && (
            <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>
          )}
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Origem
          </label>
          <Input {...register("source")} placeholder="Instagram, Indicação, etc." />
        </div>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
            Valor Estimado (R$)
          </label>
          <Input {...register("estimated_value")} type="number" min={0} step={0.01} placeholder="0,00" />
          {errors.estimated_value && (
            <p className="mt-1 text-xs text-red-500">{errors.estimated_value.message}</p>
          )}
        </div>

        {isEditing && lead?.stage === "lost" && (
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-lovable-ink-muted">
              Motivo da Perda
            </label>
            <Input {...register("lost_reason")} placeholder="Descreva o motivo..." />
          </div>
        )}

        <div className="flex gap-2 pt-2">
          <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
            {isPending ? "Salvando..." : isEditing ? "Salvar alterações" : "Criar Lead"}
          </Button>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancelar
          </Button>
        </div>

        {isEditing && lead && (
          <div className="border-t border-lovable-border pt-4">
            <Button
              type="button"
              variant="danger"
              onClick={() => {
                if (confirm(`Remover o lead "${lead.full_name}"?`)) {
                  deleteMutation.mutate(lead.id);
                }
              }}
              disabled={deleteMutation.isPending}
              className="w-full"
            >
              {deleteMutation.isPending ? "Removendo..." : "Remover Lead"}
            </Button>
          </div>
        )}
      </form>
    </Drawer>
  );
}

// ─── CRM page ─────────────────────────────────────────────────────────────────

export function CrmPage() {
  const queryClient = useQueryClient();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

  const leadsQuery = useQuery({
    queryKey: ["crm", "leads"],
    queryFn: crmService.listLeads,
    staleTime: 5 * 60 * 1000,
  });

  const moveMutation = useMutation({
    mutationFn: ({ leadId, stage }: { leadId: string; stage: Lead["stage"] }) =>
      crmService.updateLeadStage(leadId, stage),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["crm", "leads"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "commercial"] });
    },
    onError: () => toast.error("Não foi possível mover o lead."),
  });

  function handleNewLead() {
    setSelectedLead(null);
    setDrawerOpen(true);
  }

  function handleCardClick(lead: Lead) {
    setSelectedLead(lead);
    setDrawerOpen(true);
  }

  function handleDrawerClose() {
    setDrawerOpen(false);
    setSelectedLead(null);
  }

  function handleSaved() {
    void queryClient.invalidateQueries({ queryKey: ["crm", "leads"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "commercial"] });
  }

  if (leadsQuery.isLoading) {
    return <LoadingPanel text="Carregando CRM..." />;
  }

  if (!leadsQuery.data) {
    return <LoadingPanel text="Não foi possível carregar leads." />;
  }

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">CRM — Pipeline Kanban</h2>
          <p className="text-sm text-lovable-ink-muted">
            Novo → Contato → Visita → Experimental → Proposta → Fechado / Perdido
          </p>
        </div>
        <Button variant="primary" onClick={handleNewLead}>
          + Novo Lead
        </Button>
      </header>

      {moveMutation.isPending && (
        <p className="rounded-lg bg-brand-50 px-3 py-2 text-xs text-brand-700">
          Atualizando estágio...
        </p>
      )}

      <PipelineKanban
        leads={leadsQuery.data.items}
        onMove={(leadId, stage) => moveMutation.mutate({ leadId, stage })}
        onCardClick={handleCardClick}
      />

      <LeadFormDrawer
        open={drawerOpen}
        onClose={handleDrawerClose}
        lead={selectedLead}
        onSaved={handleSaved}
      />
    </section>
  );
}
