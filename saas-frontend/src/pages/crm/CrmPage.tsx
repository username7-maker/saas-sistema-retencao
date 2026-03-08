import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { crmService } from "../../services/crmService";
import { Badge, Button, Card, CardContent, Dialog, Drawer, FormField, Input, Select, Textarea } from "../../components/ui2";
import type { Lead } from "../../types";

const LEAD_SOURCES = [
  "Instagram",
  "Facebook",
  "Google",
  "Indicação",
  "Site",
  "Telefone",
  "Presencial",
  "Outro",
] as const;

const STAGE_LABELS: Record<Lead["stage"], string> = {
  new: "Novo",
  contact: "Contato",
  visit: "Visita",
  trial: "Experimental",
  proposal: "Proposta",
  meeting_scheduled: "Call agendada",
  proposal_sent: "Proposta enviada",
  won: "Fechado",
  lost: "Perdido",
};

const STAGE_ORDER: Lead["stage"][] = [
  "new",
  "contact",
  "visit",
  "trial",
  "proposal",
  "meeting_scheduled",
  "proposal_sent",
  "won",
  "lost",
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

type ContactFilter = "all" | "never_contacted" | "stale_3" | "stale_7" | "recent_3";

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

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function daysSince(isoDate: string | null): number | null {
  if (!isoDate) return null;
  const parsed = Date.parse(isoDate);
  if (Number.isNaN(parsed)) return null;
  return Math.floor((Date.now() - parsed) / (1000 * 60 * 60 * 24));
}

function formatDateTime(isoDate: string | null): string {
  if (!isoDate) return "Nunca";
  const parsed = Date.parse(isoDate);
  if (Number.isNaN(parsed)) return "Nunca";
  return new Date(parsed).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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
  const navigate = useNavigate();

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
          {isEditing && lead ? (
            <div className="grid gap-2 md:grid-cols-2">
              <Button
                variant="secondary"
                onClick={() => {
                  onClose();
                  navigate(`/vendas/briefing/${lead.id}`);
                }}
              >
                Abrir briefing
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  onClose();
                  navigate(`/vendas/script/${lead.id}`);
                }}
              >
                Abrir script
              </Button>
            </div>
          ) : null}

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
              placeholder="Ex: cliente busca plano para casal, melhor horário noturno."
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
              {isPending ? "Salvando..." : isEditing ? "Salvar alterações" : "Criar Lead"}
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
            ? `Tem certeza que deseja excluir ${lead.full_name}? Esta ação não pode ser desfeita.`
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
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStage, setSelectedStage] = useState<Lead["stage"]>("new");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [contactFilter, setContactFilter] = useState<ContactFilter>("all");

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
    onError: () => toast.error("Não foi possível mover o lead."),
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
  }, [leadsQuery.data, searchParams]);

  const sourceOptions = useMemo(() => {
    const items = leadsQuery.data?.items ?? [];
    const unique = Array.from(
      new Set(items.map((lead) => lead.source?.trim()).filter((value): value is string => Boolean(value))),
    );
    return unique.sort((a, b) => a.localeCompare(b, "pt-BR", { sensitivity: "base" }));
  }, [leadsQuery.data]);

  const leadsAfterBaseFilters = useMemo(() => {
    const items = leadsQuery.data?.items ?? [];
    const normalizedQuery = normalizeText(searchQuery);
    const now = Date.now();

    return items.filter((lead) => {
      if (sourceFilter !== "all" && lead.source !== sourceFilter) {
        return false;
      }

      if (normalizedQuery) {
        const haystack = normalizeText([lead.full_name, lead.email ?? "", lead.phone ?? "", lead.source ?? ""].join(" "));
        if (!haystack.includes(normalizedQuery)) {
          return false;
        }
      }

      const parsedLastContact = lead.last_contact_at ? Date.parse(lead.last_contact_at) : Number.NaN;
      const hasLastContact = Number.isFinite(parsedLastContact);
      const daysWithoutContact = hasLastContact ? (now - parsedLastContact) / (1000 * 60 * 60 * 24) : null;
      const isOpenStage = lead.stage !== "won" && lead.stage !== "lost";

      if (contactFilter === "never_contacted") {
        return !hasLastContact;
      }

      if (contactFilter === "stale_3") {
        return isOpenStage && (!hasLastContact || (daysWithoutContact ?? 0) > 3);
      }

      if (contactFilter === "stale_7") {
        return isOpenStage && (!hasLastContact || (daysWithoutContact ?? 0) > 7);
      }

      if (contactFilter === "recent_3") {
        return isOpenStage && hasLastContact && (daysWithoutContact ?? Infinity) <= 3;
      }

      return true;
    });
  }, [contactFilter, leadsQuery.data, searchQuery, sourceFilter]);

  const stageCounts = useMemo(() => {
    const counters = STAGE_ORDER.reduce<Record<Lead["stage"], number>>((acc, stage) => {
      acc[stage] = 0;
      return acc;
    }, {} as Record<Lead["stage"], number>);

    for (const lead of leadsAfterBaseFilters) {
      counters[lead.stage] += 1;
    }

    return counters;
  }, [leadsAfterBaseFilters]);

  const filteredLeads = useMemo(() => {
    return leadsAfterBaseFilters
      .filter((lead) => lead.stage === selectedStage)
      .sort((a, b) => {
        const aTime = a.last_contact_at ? Date.parse(a.last_contact_at) : Number.NaN;
        const bTime = b.last_contact_at ? Date.parse(b.last_contact_at) : Number.NaN;
        const parsedA = Number.isNaN(aTime) ? Date.parse(a.updated_at) : aTime;
        const parsedB = Number.isNaN(bTime) ? Date.parse(b.updated_at) : bTime;
        return parsedB - parsedA;
      });
  }, [leadsAfterBaseFilters, selectedStage]);

  const activeFiltersCount = useMemo(() => {
    return (
      (searchQuery.trim() ? 1 : 0) +
      (sourceFilter !== "all" ? 1 : 0) +
      (contactFilter !== "all" ? 1 : 0)
    );
  }, [contactFilter, searchQuery, sourceFilter]);

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

  function clearFilters() {
    setSearchQuery("");
    setSourceFilter("all");
    setContactFilter("all");
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
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">CRM - Pipeline por estagio</h2>
          <p className="text-sm text-lovable-ink-muted">
            Clique no estagio desejado para ver somente os leads dessa etapa em lista vertical.
          </p>
        </div>
        <Button variant="primary" onClick={handleNewLead}>
          + Novo Lead
        </Button>
      </header>

      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="min-w-[260px] flex-1">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Buscar</label>
              <Input
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Nome, email, telefone ou origem..."
              />
            </div>

            <div className="w-full md:w-52">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Origem</label>
              <Select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value)}>
                <option value="all">Todas as origens</option>
                {sourceOptions.map((source) => (
                  <option key={source} value={source}>
                    {source}
                  </option>
                ))}
              </Select>
            </div>

            <div className="w-full md:w-64">
              <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Contato</label>
              <Select value={contactFilter} onChange={(event) => setContactFilter(event.target.value as ContactFilter)}>
                <option value="all">Todos</option>
                <option value="never_contacted">Nunca contatados</option>
                <option value="stale_3">Sem contato 3+ dias</option>
                <option value="stale_7">Sem contato 7+ dias</option>
                <option value="recent_3">Contato recente (ate 3 dias)</option>
              </Select>
            </div>

            <div className="w-full md:w-auto">
              <Button variant="ghost" onClick={clearFilters} disabled={activeFiltersCount === 0}>
                Limpar filtros
              </Button>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            {STAGE_ORDER.map((stage) => (
              <button
                key={stage}
                type="button"
                onClick={() => setSelectedStage(stage)}
                className={`inline-flex items-center gap-2 rounded-xl border px-3 py-2 text-xs font-semibold uppercase tracking-wide transition ${
                  selectedStage === stage
                    ? "border-lovable-primary bg-lovable-primary-soft text-lovable-primary"
                    : "border-lovable-border bg-lovable-surface-soft text-lovable-ink-muted hover:border-lovable-border-strong hover:text-lovable-ink"
                }`}
              >
                <span>{STAGE_LABELS[stage]}</span>
                <span className="rounded-full bg-lovable-surface px-2 py-0.5 text-[10px] text-lovable-ink-muted">
                  {stageCounts[stage]}
                </span>
              </button>
            ))}
          </div>

          <p className="mt-3 text-xs text-lovable-ink-muted">
            {filteredLeads.length} lead(s) no estagio <strong>{STAGE_LABELS[selectedStage]}</strong> de {leadsAfterBaseFilters.length} lead(s) apos filtros base
            {activeFiltersCount > 0 ? ` (${activeFiltersCount} filtro(s) ativo(s))` : ""}.
          </p>
        </CardContent>
      </Card>

      {moveMutation.isPending ? (
        <p className="rounded-lg bg-lovable-primary-soft px-3 py-2 text-xs text-lovable-primary">Atualizando estágio...</p>
      ) : null}

      <Card>
        <CardContent className="p-0">
          {filteredLeads.length === 0 ? (
            <div className="flex items-center justify-center px-4 py-12 text-sm text-lovable-ink-muted">
              Nenhum lead encontrado no estagio selecionado com os filtros atuais.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-lovable-border bg-lovable-surface-soft">
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Nome</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Origem</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Ultimo contato</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Valor estimado</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Status contato</th>
                    <th className="px-4 py-3 text-left font-semibold text-lovable-ink-muted">Acoes</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredLeads.map((lead) => {
                    const daysWithoutContact = daysSince(lead.last_contact_at);
                    const nextStage = NEXT_STAGE[lead.stage];
                    const statusVariant =
                      daysWithoutContact === null ? "danger" : daysWithoutContact > 7 ? "danger" : daysWithoutContact > 3 ? "warning" : "success";
                    const statusLabel =
                      daysWithoutContact === null
                        ? "Nunca contatado"
                        : daysWithoutContact === 0
                          ? "Contato hoje"
                          : `${daysWithoutContact}d sem contato`;

                    return (
                      <tr
                        key={lead.id}
                        className="cursor-pointer border-b border-lovable-border/50 transition hover:bg-lovable-surface-soft/40"
                        onClick={() => handleCardClick(lead)}
                      >
                        <td className="px-4 py-3">
                          <div>
                            <p className="font-semibold text-lovable-ink">{lead.full_name}</p>
                            <p className="text-xs text-lovable-ink-muted">{lead.email ?? lead.phone ?? "Sem contato principal"}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-lovable-ink-muted">{lead.source || "Nao informado"}</td>
                        <td className="px-4 py-3 text-lovable-ink-muted">{formatDateTime(lead.last_contact_at)}</td>
                        <td className="px-4 py-3 text-lovable-ink">
                          {(lead.estimated_value ?? 0).toLocaleString("pt-BR", {
                            style: "currency",
                            currency: "BRL",
                            maximumFractionDigits: 0,
                          })}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={statusVariant}>{statusLabel}</Badge>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2" onClick={(event) => event.stopPropagation()}>
                            <Button size="sm" variant="ghost" onClick={() => handleCardClick(lead)}>
                              Editar
                            </Button>
                            {nextStage ? (
                              <Button
                                size="sm"
                                variant="secondary"
                                onClick={() => moveMutation.mutate({ leadId: lead.id, stage: nextStage })}
                              >
                                Avancar
                              </Button>
                            ) : null}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      <LeadFormDrawer open={drawerOpen} onClose={handleDrawerClose} lead={selectedLead} onSaved={handleSaved} />
    </section>
  );
}

