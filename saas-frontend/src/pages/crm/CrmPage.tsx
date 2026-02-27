import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";

import { PipelineKanban } from "../../components/crm/PipelineKanban";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { crmService } from "../../services/crmService";
import { Button, Dialog, Drawer, FormField, Input, Select, Textarea } from "../../components/ui2";
import type { Lead } from "../../types";

const LEAD_SOURCES = [
  "Instagram",
  "Facebook",
  "Google",
  "Indicacao",
  "Site",
  "Telefone",
  "Presencial",
  "Outro",
] as const;

const leadSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  email: z.string().email("E-mail invalido").optional().or(z.literal("")),
  phone: z.string().optional(),
  source: z.string().optional(),
  estimated_value: z.coerce.number().min(0, "Valor nao pode ser negativo").optional(),
  notes: z.string().optional(),
  lost_reason: z.string().optional(),
});

type LeadFormValues = z.infer<typeof leadSchema>;

function extractNotesValue(notes: Lead["notes"]): string {
  if (!Array.isArray(notes) || notes.length === 0) {
    return "";
  }

  const lines = notes
    .map((item) => {
      if (typeof item === "string") {
        return item;
      }
      if (typeof item === "object" && item !== null && "note" in item) {
        const noteValue = (item as { note?: unknown }).note;
        return typeof noteValue === "string" ? noteValue : "";
      }
      return "";
    })
    .filter(Boolean);

  return lines.join("\n");
}

interface LeadFormDrawerProps {
  open: boolean;
  onClose: () => void;
  lead?: Lead | null;
  onSaved: () => void;
}

function LeadFormDrawer({ open, onClose, lead, onSaved }: LeadFormDrawerProps) {
  const isEditing = Boolean(lead);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);

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
          notes: extractNotesValue(lead.notes),
          lost_reason: lead.lost_reason ?? "",
        }
      : {
          source: "",
          notes: "",
        },
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
        notes: data.notes || undefined,
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
      setConfirmDeleteOpen(false);
      onSaved();
      onClose();
    },
    onError: () => toast.error("Erro ao remover lead."),
  });

  function onSubmit(values: LeadFormValues) {
    if (isEditing && lead) {
      updateMutation.mutate({ id: lead.id, data: values });
      return;
    }

    createMutation.mutate({
      full_name: values.full_name,
      email: values.email || undefined,
      phone: values.phone,
      source: values.source,
      estimated_value: values.estimated_value,
      notes: values.notes || undefined,
    });
  }

  const isPending = isSubmitting || createMutation.isPending || updateMutation.isPending;

  return (
    <>
      <Drawer open={open} onClose={onClose} title={isEditing ? "Editar Lead" : "Novo Lead"}>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 p-1">
          <FormField label="Nome" required error={errors.full_name?.message}>
            <Input {...register("full_name")} placeholder="Nome completo" />
          </FormField>

          <FormField label="Telefone">
            <Input {...register("phone")} placeholder="(11) 99999-9999" />
          </FormField>

          <FormField label="E-mail" error={errors.email?.message}>
            <Input {...register("email")} type="email" placeholder="email@exemplo.com" />
          </FormField>

          <FormField label="Origem">
            <Select {...register("source")}>
              <option value="">Selecione a origem</option>
              {LEAD_SOURCES.map((source) => (
                <option key={source} value={source}>
                  {source}
                </option>
              ))}
            </Select>
          </FormField>

          <FormField label="Valor Estimado (R$)" error={errors.estimated_value?.message}>
            <Input {...register("estimated_value")} type="number" min={0} step={0.01} placeholder="0,00" />
          </FormField>

          <FormField label="Notas">
            <Textarea
              {...register("notes")}
              placeholder="Ex: cliente busca plano para casal, melhor horario noturno."
              rows={4}
            />
          </FormField>

          {isEditing && lead?.stage === "lost" ? (
            <FormField label="Motivo da perda">
              <Input {...register("lost_reason")} placeholder="Descreva o motivo..." />
            </FormField>
          ) : null}

          <div className="flex gap-2 pt-2">
            <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
              {isPending ? "Salvando..." : isEditing ? "Salvar alteracoes" : "Criar Lead"}
            </Button>
            <Button type="button" variant="ghost" onClick={onClose}>
              Cancelar
            </Button>
          </div>

          {isEditing && lead ? (
            <div className="border-t border-lovable-border pt-4">
              <Button
                type="button"
                variant="danger"
                onClick={() => setConfirmDeleteOpen(true)}
                disabled={deleteMutation.isPending}
                className="w-full"
              >
                {deleteMutation.isPending ? "Removendo..." : "Remover Lead"}
              </Button>
            </div>
          ) : null}
        </form>
      </Drawer>

      <Dialog
        open={confirmDeleteOpen}
        onClose={() => setConfirmDeleteOpen(false)}
        title="Excluir lead"
        description={
          lead
            ? `Tem certeza que deseja excluir ${lead.full_name}? Esta acao nao pode ser desfeita.`
            : "Tem certeza que deseja excluir este lead?"
        }
      >
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={() => setConfirmDeleteOpen(false)}>
            Cancelar
          </Button>
          <Button
            variant="danger"
            onClick={() => {
              if (lead) {
                deleteMutation.mutate(lead.id);
              }
            }}
            disabled={deleteMutation.isPending}
          >
            {deleteMutation.isPending ? "Excluindo..." : "Excluir"}
          </Button>
        </div>
      </Dialog>
    </>
  );
}

export function CrmPage() {
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);

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
    onError: () => toast.error("Nao foi possivel mover o lead."),
  });

  useEffect(() => {
    const leadId = searchParams.get("leadId");
    if (!leadId || !leadsQuery.data?.items.length) {
      return;
    }
    const lead = leadsQuery.data.items.find((item) => item.id === leadId);
    if (!lead) {
      return;
    }
    setSelectedLead(lead);
    setDrawerOpen(true);
  }, [leadsQuery.data?.items, searchParams]);

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
    if (searchParams.has("leadId")) {
      const next = new URLSearchParams(searchParams);
      next.delete("leadId");
      setSearchParams(next, { replace: true });
    }
  }

  function handleSaved() {
    void queryClient.invalidateQueries({ queryKey: ["crm", "leads"] });
    void queryClient.invalidateQueries({ queryKey: ["dashboard", "commercial"] });
  }

  if (leadsQuery.isLoading) {
    return <LoadingPanel text="Carregando CRM..." />;
  }

  if (!leadsQuery.data) {
    return <LoadingPanel text="Nao foi possivel carregar leads." />;
  }

  return (
    <section className="space-y-6">
      <header className="flex items-center justify-between gap-4">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">CRM - Pipeline Kanban</h2>
          <p className="text-sm text-lovable-ink-muted">
            {"Novo -> Contato -> Visita -> Experimental -> Proposta -> Fechado / Perdido"}
          </p>
        </div>
        <Button variant="primary" onClick={handleNewLead}>
          + Novo Lead
        </Button>
      </header>

      {moveMutation.isPending ? (
        <p className="rounded-lg bg-lovable-primary-soft px-3 py-2 text-xs text-lovable-primary">Atualizando estagio...</p>
      ) : null}

      <PipelineKanban
        leads={leadsQuery.data.items}
        onMove={(leadId, stage) => moveMutation.mutate({ leadId, stage })}
        onCardClick={handleCardClick}
      />

      <LeadFormDrawer open={drawerOpen} onClose={handleDrawerClose} lead={selectedLead} onSaved={handleSaved} />
    </section>
  );
}

