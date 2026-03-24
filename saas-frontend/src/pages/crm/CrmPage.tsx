import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Users } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";

import { EmptyState, FilterBar, KPIStrip, PageHeader, SectionHeader, SkeletonList, StatusBadge } from "../../components/ui";
import { Badge, Button, Card, CardContent, Dialog, Drawer, FormField, Input, Select, Textarea } from "../../components/ui2";
import { crmService } from "../../services/crmService";
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

const LEAD_STAGE_VALUES = [
  "new",
  "contact",
  "visit",
  "trial",
  "proposal",
  "meeting_scheduled",
  "proposal_sent",
  "won",
  "lost",
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

const STAGE_ORDER: Lead["stage"][] = [...LEAD_STAGE_VALUES];

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

const STAGE_BADGE_MAP: Record<Lead["stage"], { label: string; variant: "neutral" | "success" | "warning" | "danger" }> = {
  new: { label: "Novo", variant: "neutral" },
  contact: { label: "Contato", variant: "warning" },
  visit: { label: "Visita", variant: "warning" },
  trial: { label: "Experimental", variant: "warning" },
  proposal: { label: "Proposta", variant: "warning" },
  meeting_scheduled: { label: "Call agendada", variant: "warning" },
  proposal_sent: { label: "Proposta enviada", variant: "warning" },
  won: { label: "Fechado", variant: "success" },
  lost: { label: "Perdido", variant: "danger" },
};

type ContactFilter = "all" | "never_contacted" | "stale_3" | "stale_7" | "recent_3";

const CONTACT_FILTER_OPTIONS: { value: ContactFilter; label: string }[] = [
  { value: "all", label: "Todos" },
  { value: "never_contacted", label: "Nunca contatado" },
  { value: "stale_3", label: "Sem contato ha 3 dias" },
  { value: "stale_7", label: "Sem contato ha 7 dias" },
  { value: "recent_3", label: "Contato recente" },
];

const NEGOTIATION_STAGES = new Set<Lead["stage"]>(["trial", "proposal", "meeting_scheduled", "proposal_sent"]);

const leadSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  email: z.string().email("E-mail invalido").optional().or(z.literal("")),
  phone: z.string().optional(),
  source: z.string().optional(),
  stage: z.enum(LEAD_STAGE_VALUES),
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

function formatCurrency(value: number | null | undefined): string {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value ?? 0);
}

function buildLeadDefaults(lead?: Lead | null): LeadFormValues {
  return lead
    ? {
        full_name: lead.full_name,
        email: lead.email ?? "",
        phone: lead.phone ?? "",
        source: lead.source ?? "",
        stage: lead.stage,
        estimated_value: lead.estimated_value,
        notes: extractNotesValue(lead.notes),
        lost_reason: lead.lost_reason ?? "",
      }
    : {
        full_name: "",
        email: "",
        phone: "",
        source: "",
        stage: "new",
        estimated_value: 0,
        notes: "",
        lost_reason: "",
      };
}

function isInCurrentMonth(isoDate: string | null): boolean {
  if (!isoDate) return false;
  const parsed = new Date(isoDate);
  if (Number.isNaN(parsed.getTime())) return false;
  const now = new Date();
  return parsed.getMonth() === now.getMonth() && parsed.getFullYear() === now.getFullYear();
}

function getContactAlert(lead: Lead): { label: string; variant: "warning" | "danger" } | null {
  if (lead.stage === "won" || lead.stage === "lost") return null;

  const daysWithoutContact = daysSince(lead.last_contact_at);
  if (daysWithoutContact === null) {
    return { label: "Nunca contatado", variant: "danger" };
  }
  if (daysWithoutContact > 7) {
    return { label: `${daysWithoutContact}d sem contato`, variant: "danger" };
  }
  if (daysWithoutContact > 3) {
    return { label: `${daysWithoutContact}d sem contato`, variant: "warning" };
  }
  return null;
}

function matchesContactFilter(lead: Lead, contactFilter: ContactFilter): boolean {
  const parsedLastContact = lead.last_contact_at ? Date.parse(lead.last_contact_at) : Number.NaN;
  const hasLastContact = Number.isFinite(parsedLastContact);
  const daysWithoutContact = hasLastContact ? (Date.now() - parsedLastContact) / (1000 * 60 * 60 * 24) : null;
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
    watch,
    formState: { errors, isSubmitting },
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadSchema),
    defaultValues: buildLeadDefaults(lead),
  });

  const watchedStage = watch("stage");

  useEffect(() => {
    reset(buildLeadDefaults(lead));
  }, [lead, reset]);

  const createMutation = useMutation({
    mutationFn: crmService.createLead,
    onSuccess: () => {
      toast.success("Lead criado com sucesso!");
      reset(buildLeadDefaults(null));
      onSaved();
      onClose();
    },
    onError: () => toast.error("Erro ao criar lead. Tente novamente."),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: LeadFormValues }) =>
      crmService.updateLead(id, {
        full_name: data.full_name,
        email: data.email || undefined,
        phone: data.phone || undefined,
        source: data.source || undefined,
        stage: data.stage,
        estimated_value: data.estimated_value,
        notes: data.notes || undefined,
        lost_reason: data.stage === "lost" ? data.lost_reason || undefined : undefined,
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
      phone: values.phone || undefined,
      source: values.source || undefined,
      estimated_value: values.estimated_value,
      notes: values.notes || undefined,
    });
  }

  const isPending = isSubmitting || createMutation.isPending || updateMutation.isPending;

  return (
    <>
      <Drawer open={open} onClose={onClose} title={isEditing ? "Editar Lead" : "Novo Lead"}>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 p-4">
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

          <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft/35 p-4">
            <SectionHeader title="Dados do lead" subtitle="Informacoes principais e origem do contato." />
            <div className="grid gap-4">
              <FormField label="Nome" required error={errors.full_name?.message}>
                <Input {...register("full_name")} placeholder="Nome completo" />
              </FormField>

              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="E-mail" error={errors.email?.message}>
                  <Input {...register("email")} type="email" placeholder="email@exemplo.com" />
                </FormField>

                <FormField label="Telefone">
                  <Input {...register("phone")} placeholder="(11) 99999-9999" />
                </FormField>
              </div>

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
            </div>
          </div>

          <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft/35 p-4">
            <SectionHeader title="Pipeline" subtitle="Estagio atual e valor estimado da oportunidade." />
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Estagio">
                <Select {...register("stage")} disabled={!isEditing}>
                  {STAGE_ORDER.map((stage) => (
                    <option key={stage} value={stage}>
                      {STAGE_LABELS[stage]}
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField label="Valor estimado (R$)" error={errors.estimated_value?.message}>
                <Input {...register("estimated_value")} type="number" min={0} step={0.01} placeholder="0,00" />
              </FormField>
            </div>
          </div>

          <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft/35 p-4">
            <SectionHeader title="Notas" subtitle="Contexto comercial, observacoes e anotacoes relevantes." />
            <div className="grid gap-4">
              <FormField label="Notas">
                <Textarea
                  {...register("notes")}
                  placeholder="Ex: cliente busca plano para casal, melhor horario noturno."
                  rows={4}
                />
              </FormField>

              {watchedStage === "lost" ? (
                <FormField label="Motivo da perda">
                  <Input {...register("lost_reason")} placeholder="Descreva o motivo..." />
                </FormField>
              ) : null}
            </div>
          </div>

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
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStage, setSelectedStage] = useState<"all" | Lead["stage"]>("all");
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
  }, [leadsQuery.data, searchParams]);

  const allLeads = useMemo(() => leadsQuery.data?.items ?? [], [leadsQuery.data?.items]);

  const leadsAfterBaseFilters = useMemo(() => {
    const normalizedQuery = normalizeText(searchQuery);

    return allLeads.filter((lead) => {
      if (normalizedQuery) {
        const haystack = normalizeText([lead.full_name, lead.email ?? "", lead.phone ?? "", lead.source ?? ""].join(" "));
        if (!haystack.includes(normalizedQuery)) {
          return false;
        }
      }

      return matchesContactFilter(lead, contactFilter);
    });
  }, [allLeads, contactFilter, searchQuery]);

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
      .filter((lead) => selectedStage === "all" || lead.stage === selectedStage)
      .sort((a, b) => {
        const aTime = a.last_contact_at ? Date.parse(a.last_contact_at) : Number.NaN;
        const bTime = b.last_contact_at ? Date.parse(b.last_contact_at) : Number.NaN;
        const parsedA = Number.isNaN(aTime) ? Date.parse(a.updated_at) : aTime;
        const parsedB = Number.isNaN(bTime) ? Date.parse(b.updated_at) : bTime;
        return parsedB - parsedA;
      });
  }, [leadsAfterBaseFilters, selectedStage]);

  const activeFiltersCount = useMemo(() => {
    return (searchQuery.trim() ? 1 : 0) + (selectedStage !== "all" ? 1 : 0) + (contactFilter !== "all" ? 1 : 0);
  }, [contactFilter, searchQuery, selectedStage]);

  const kpiItems = useMemo(() => {
    const total = allLeads.length;
    const totalActive = allLeads.filter((lead) => lead.stage !== "won" && lead.stage !== "lost").length;
    const negotiation = allLeads.filter((lead) => NEGOTIATION_STAGES.has(lead.stage)).length;
    const wonThisMonth = allLeads.filter((lead) => lead.stage === "won" && isInCurrentMonth(lead.updated_at)).length;
    const conversionRate = total > 0 ? (allLeads.filter((lead) => lead.stage === "won").length / total) * 100 : 0;

    return [
      { label: "Total ativos", value: totalActive, tone: "neutral" as const },
      { label: "Em negociacao", value: negotiation, tone: "warning" as const },
      { label: "Fechados no mes", value: wonThisMonth, tone: "success" as const },
      { label: "Taxa de conversao", value: `${conversionRate.toFixed(1)}%`, tone: "success" as const },
    ];
  }, [allLeads]);

  const stageSummarySubtitle =
    selectedStage === "all"
      ? "Leitura rapida do pipeline com base nos filtros atuais."
      : `Filtro principal em ${STAGE_LABELS[selectedStage]}.`;

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
    setSelectedStage("all");
    setContactFilter("all");
  }

  function handleRowKeyDown(event: React.KeyboardEvent<HTMLDivElement>, lead: Lead) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      handleCardClick(lead);
    }
  }

  if (leadsQuery.isLoading) {
    return (
      <section className="space-y-6">
        <PageHeader title="CRM" subtitle="Pipeline de conversao e gestao de leads" />
        <Card>
          <CardContent className="pt-5">
            <SkeletonList rows={1} cols={4} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-5">
            <SkeletonList rows={8} cols={5} />
          </CardContent>
        </Card>
      </section>
    );
  }

  if (!leadsQuery.data) {
    return (
      <section className="space-y-6">
        <PageHeader title="CRM" subtitle="Pipeline de conversao e gestao de leads" />
        <Card>
          <CardContent className="pt-5">
            <EmptyState
              icon={AlertTriangle}
              title="Nao foi possivel carregar os leads"
              description="Atualize a pagina e tente novamente."
            />
          </CardContent>
        </Card>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <PageHeader
        title="CRM"
        subtitle="Pipeline de conversao e gestao de leads"
        actions={
          <Button variant="primary" onClick={handleNewLead}>
            Novo Lead
          </Button>
        }
      />

      <KPIStrip items={kpiItems} />

      <div className="space-y-4">
        <FilterBar
          search={{
            value: searchQuery,
            onChange: setSearchQuery,
            placeholder: "Buscar por nome, email, telefone ou origem",
          }}
          filters={[
            {
              key: "stage",
              label: "Estagio",
              value: selectedStage,
              onChange: (value) => setSelectedStage(value as "all" | Lead["stage"]),
              options: [
                { value: "all", label: "Todos os estagios" },
                ...STAGE_ORDER.map((stage) => ({ value: stage, label: STAGE_LABELS[stage] })),
              ],
            },
            {
              key: "contact",
              label: "Contato",
              value: contactFilter,
              onChange: (value) => setContactFilter(value as ContactFilter),
              options: CONTACT_FILTER_OPTIONS,
            },
          ]}
          activeCount={activeFiltersCount}
          onClear={clearFilters}
        />

        <Card>
          <CardContent className="pt-5">
            <SectionHeader title="Resumo por estagio" subtitle={stageSummarySubtitle} count={leadsAfterBaseFilters.length} />
            <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
              {STAGE_ORDER.map((stage) => (
                <div
                  key={stage}
                  className={`rounded-xl border px-3 py-3 ${
                    selectedStage === stage
                      ? "border-lovable-primary bg-lovable-primary-soft/60"
                      : "border-lovable-border bg-lovable-surface-soft/35"
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="text-sm font-semibold text-lovable-ink">{STAGE_LABELS[stage]}</p>
                    <Badge variant="neutral" className="px-2 py-0.5 text-[11px] normal-case tracking-normal">
                      {stageCounts[stage]}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {moveMutation.isPending ? (
        <p className="rounded-lg bg-lovable-primary-soft px-3 py-2 text-xs text-lovable-primary">Atualizando estagio...</p>
      ) : null}

      <Card>
        <CardContent className="pt-5">
          <SectionHeader
            title="Leads"
            subtitle={
              selectedStage === "all"
                ? `${filteredLeads.length} lead(s) visiveis com os filtros atuais.`
                : `${filteredLeads.length} lead(s) em ${STAGE_LABELS[selectedStage]}.`
            }
            count={filteredLeads.length}
          />

          {filteredLeads.length === 0 ? (
            <EmptyState
              icon={Users}
              title="Nenhum lead encontrado"
              description="Tente ajustar os filtros ou adicione um novo lead"
              action={{ label: "Novo Lead", onClick: handleNewLead }}
            />
          ) : (
            <div className="space-y-2">
              {filteredLeads.map((lead) => {
                const nextStage = NEXT_STAGE[lead.stage];
                const contactAlert = getContactAlert(lead);
                const advancingThisLead = moveMutation.isPending && moveMutation.variables?.leadId === lead.id;

                return (
                  <div
                    key={lead.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => handleCardClick(lead)}
                    onKeyDown={(event) => handleRowKeyDown(event, lead)}
                    className="grid cursor-pointer gap-4 rounded-xl border border-lovable-border bg-lovable-surface-soft/30 px-4 py-3 transition hover:border-lovable-border-strong hover:bg-lovable-surface-soft/60 lg:grid-cols-[minmax(0,2.2fr)_1.1fr_1.2fr_auto]"
                  >
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <p className="truncate text-sm font-semibold text-lovable-ink">{lead.full_name}</p>
                        <Badge variant="neutral" className="px-2 py-0.5 text-[11px] normal-case tracking-normal">
                          {lead.source || "Sem origem"}
                        </Badge>
                        <StatusBadge status={lead.stage} map={STAGE_BADGE_MAP} />
                      </div>
                      <p className="mt-1 truncate text-xs text-lovable-ink-muted">{lead.email ?? lead.phone ?? "Sem contato principal"}</p>
                    </div>

                    <div className="space-y-1">
                      <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">Ultimo contato</p>
                      <p className="text-sm text-lovable-ink">{formatDateTime(lead.last_contact_at)}</p>
                      {contactAlert ? (
                        <Badge variant={contactAlert.variant} className="px-2 py-0.5 text-[11px] normal-case tracking-normal">
                          {contactAlert.label}
                        </Badge>
                      ) : null}
                    </div>

                    <div className="space-y-1">
                      <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">Valor estimado</p>
                      <p className="text-sm font-semibold text-lovable-ink">{formatCurrency(lead.estimated_value)}</p>
                    </div>

                    <div className="flex items-center justify-start lg:justify-end" onClick={(event) => event.stopPropagation()}>
                      {nextStage ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => moveMutation.mutate({ leadId: lead.id, stage: nextStage })}
                          disabled={moveMutation.isPending}
                        >
                          {advancingThisLead ? "Avancando..." : "Avancar estagio"}
                          <ArrowRight size={14} />
                        </Button>
                      ) : null}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <LeadFormDrawer open={drawerOpen} onClose={handleDrawerClose} lead={selectedLead} onSaved={handleSaved} />
    </section>
  );
}
