import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  MessageSquare,
  RefreshCw,
  Send,
  Settings2,
  UserPlus,
} from "lucide-react";
import toast from "react-hot-toast";

import { Badge, Button, Checkbox, Input, Select, Textarea, cn } from "../../components/ui2";
import { methodOsService } from "../../services/methodOsService";
import { buildWhatsAppHref, formatPhoneDisplay } from "../../utils/whatsapp";
import type {
  MethodActionResult,
  MethodActionType,
  MethodOperationalEventCreate,
  MethodPersonCreate,
  MethodPersonType,
  MethodPillar,
  MethodWeeklyReport,
} from "../../types";

const PILLARS: Array<{ key: MethodPillar; label: string }> = [
  { key: "acquisition", label: "Aquisicao" },
  { key: "sales", label: "Vendas" },
  { key: "post_sale", label: "Pos-venda" },
];

const EVENT_OPTIONS: Record<MethodPillar, Array<{ value: string; label: string }>> = {
  acquisition: [
    { value: "new_contact", label: "Novo contato" },
    { value: "qualification_pending", label: "Qualificacao pendente" },
  ],
  sales: [
    { value: "proposal_no_response", label: "Proposta sem resposta" },
    { value: "followup_due", label: "Follow-up vencendo" },
    { value: "simulation_no_response", label: "Simulacao sem resposta" },
  ],
  post_sale: [
    { value: "low_frequency", label: "Baixa frequencia" },
    { value: "payment_overdue", label: "Pendencia de pagamento" },
    { value: "inactive_customer", label: "Cliente inativo" },
    { value: "plan_expiring", label: "Renovacao proxima" },
  ],
};

const ACTION_TYPES: Array<{ value: MethodActionType; label: string }> = [
  { value: "whatsapp", label: "WhatsApp" },
  { value: "call", label: "Ligacao" },
  { value: "email", label: "Email" },
  { value: "in_person", label: "Presencial" },
  { value: "internal_note", label: "Nota interna" },
];

const ACTION_RESULTS: Array<{ value: MethodActionResult; label: string }> = [
  { value: "responded", label: "Respondeu" },
  { value: "scheduled", label: "Agendado" },
  { value: "bought", label: "Comprou" },
  { value: "returned", label: "Retornou" },
  { value: "renewed", label: "Renovou" },
  { value: "no_response", label: "Sem resposta" },
  { value: "lost", label: "Perdido" },
];

const OUTCOME_OPTIONS = [
  { value: "", label: "Sem resultado medido" },
  { value: "closed_sale", label: "Venda/fechamento" },
  { value: "recovered_customer", label: "Cliente recuperado" },
  { value: "scheduled", label: "Agendamento" },
  { value: "lost", label: "Perda" },
];

function parsePayload(text: string): Record<string, unknown> {
  const trimmed = text.trim();
  if (!trimmed) return {};
  try {
    const parsed = JSON.parse(trimmed);
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : { value: parsed };
  } catch {
    return { notes: trimmed };
  }
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function priorityVariant(priority: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (priority === "critical") return "danger";
  if (priority === "high") return "warning";
  if (priority === "medium") return "info";
  return "neutral";
}

function metricCard(label: string, value: number, Icon: typeof Activity, tone: string) {
  return (
    <div className="rounded-2xl border border-lovable-border/70 bg-lovable-surface/72 p-4 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <span className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">{label}</span>
        <span className={cn("flex h-9 w-9 items-center justify-center rounded-xl border", tone)}>
          <Icon size={17} />
        </span>
      </div>
      <p className="mt-4 text-3xl font-bold text-lovable-ink">{value}</p>
    </div>
  );
}

export function MethodOsPage() {
  const queryClient = useQueryClient();
  const [selectedSegmentId, setSelectedSegmentId] = useState("");
  const [activePillars, setActivePillars] = useState<Record<string, boolean>>({
    acquisition: true,
    sales: true,
    post_sale: true,
  });
  const [personForm, setPersonForm] = useState<MethodPersonCreate>({
    name: "",
    phone: "",
    person_type: "lead",
    source_channel: "whatsapp",
  });
  const [eventForm, setEventForm] = useState<MethodOperationalEventCreate>({
    person_id: "",
    pillar: "post_sale",
    event_type: "low_frequency",
    event_source: "manual",
    event_payload: {},
  });
  const [payloadText, setPayloadText] = useState("");
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [messageDraft, setMessageDraft] = useState("");
  const [actionSummary, setActionSummary] = useState("");
  const [actionType, setActionType] = useState<MethodActionType>("whatsapp");
  const [actionResult, setActionResult] = useState<MethodActionResult>("responded");
  const [outcomeType, setOutcomeType] = useState("");
  const [outcomeValue, setOutcomeValue] = useState("");
  const [weeklyReport, setWeeklyReport] = useState<MethodWeeklyReport | null>(null);

  const profileQuery = useQuery({
    queryKey: ["method-os", "profile"],
    queryFn: methodOsService.getClientProfile,
    staleTime: 2 * 60 * 1000,
  });
  const segmentsQuery = useQuery({
    queryKey: ["method-os", "segments"],
    queryFn: methodOsService.listSegments,
    staleTime: 10 * 60 * 1000,
  });
  const dashboardQuery = useQuery({
    queryKey: ["method-os", "dashboard"],
    queryFn: methodOsService.getDashboard,
    staleTime: 60_000,
  });
  const peopleQuery = useQuery({
    queryKey: ["method-os", "people"],
    queryFn: methodOsService.listPeople,
    staleTime: 60_000,
  });
  const tasksQuery = useQuery({
    queryKey: ["method-os", "tasks"],
    queryFn: () => methodOsService.listTasks(),
    staleTime: 30_000,
  });

  const profile = profileQuery.data;
  const segments = segmentsQuery.data ?? [];
  const people = peopleQuery.data ?? [];
  const tasks = tasksQuery.data ?? [];
  const openTasks = tasks.filter((task) => task.status === "open" || task.status === "in_progress");
  const selectedTask = tasks.find((task) => task.id === selectedTaskId) ?? openTasks[0] ?? tasks[0] ?? null;
  const currentMessage = messageDraft.trim();
  const whatsappHref = selectedTask
    ? buildWhatsAppHref(selectedTask.person_phone, currentMessage || selectedTask.suggested_message, selectedTask.person_name)
    : null;

  const selectedSegment = useMemo(
    () => segments.find((segment) => segment.id === selectedSegmentId) ?? profile?.segment ?? null,
    [profile?.segment, segments, selectedSegmentId],
  );

  useEffect(() => {
    if (!profile) return;
    setSelectedSegmentId(profile.config.segment_id ?? profile.client.segment_id ?? "");
    setActivePillars({
      acquisition: Boolean(profile.config.active_pillars.acquisition),
      sales: Boolean(profile.config.active_pillars.sales),
      post_sale: Boolean(profile.config.active_pillars.post_sale),
    });
  }, [profile]);

  useEffect(() => {
    if (!selectedTask) return;
    setSelectedTaskId(selectedTask.id);
    setMessageDraft(selectedTask.suggested_message ?? "");
    setActionSummary("");
    setOutcomeType("");
    setOutcomeValue("");
    setActionType("whatsapp");
    setActionResult("responded");
  }, [selectedTask?.id]);

  const invalidateMethodOs = () => {
    void queryClient.invalidateQueries({ queryKey: ["method-os"] });
  };

  const saveConfigMutation = useMutation({
    mutationFn: () =>
      methodOsService.updateClientConfig({
        segment_id: selectedSegmentId || null,
        active_pillars: activePillars,
      }),
    onSuccess: () => {
      invalidateMethodOs();
      toast.success("Configuracao Method OS salva.");
    },
    onError: () => toast.error("Erro ao salvar configuracao Method OS."),
  });

  const copyPlaybookMutation = useMutation({
    mutationFn: () => methodOsService.copyPlaybookToClient(selectedSegmentId),
    onSuccess: () => {
      invalidateMethodOs();
      toast.success("Playbook copiado para o cliente.");
    },
    onError: () => toast.error("Erro ao copiar playbook."),
  });

  const createPersonMutation = useMutation({
    mutationFn: (payload: MethodPersonCreate) => methodOsService.createPerson(payload),
    onSuccess: (person) => {
      setPersonForm({ name: "", phone: "", person_type: "lead", source_channel: "whatsapp" });
      setEventForm((current) => ({ ...current, person_id: person.id }));
      invalidateMethodOs();
      toast.success("Pessoa criada.");
    },
    onError: () => toast.error("Erro ao criar pessoa."),
  });

  const createEventTaskMutation = useMutation({
    mutationFn: async (payload: MethodOperationalEventCreate) => {
      const event = await methodOsService.createEvent(payload);
      return methodOsService.generateTaskFromEvent(event.id);
    },
    onSuccess: (task) => {
      setSelectedTaskId(task.id);
      setPayloadText("");
      invalidateMethodOs();
      toast.success("Evento registrado e tarefa gerada.");
    },
    onError: () => toast.error("Erro ao gerar tarefa do evento."),
  });

  const openWhatsappMutation = useMutation({
    mutationFn: async () => {
      if (!selectedTask) return null;
      const updated = await methodOsService.updateTaskMessage(selectedTask.id, currentMessage || null);
      return updated.wa_me_link;
    },
    onSuccess: (link) => {
      invalidateMethodOs();
      const href = link || whatsappHref;
      if (href) {
        window.open(href, "_blank", "noopener,noreferrer");
      }
    },
    onError: () => toast.error("Erro ao preparar link do WhatsApp."),
  });

  const actionMutation = useMutation({
    mutationFn: async () => {
      if (!selectedTask) return null;
      const action = await methodOsService.createAction(selectedTask.id, {
        action_type: actionType,
        action_summary: actionSummary || "Acao humana registrada.",
        result: actionResult,
        notes: currentMessage ? `Mensagem revisada: ${currentMessage}` : null,
        mark_task_status: ["bought", "returned", "renewed", "lost"].includes(actionResult)
          ? actionResult === "lost"
            ? "dismissed"
            : "done"
          : null,
      });
      if (outcomeType) {
        await methodOsService.createOutcome({
          task_id: selectedTask.id,
          action_id: action.id,
          outcome_type: outcomeType,
          value_numeric: outcomeValue ? Number(outcomeValue) : null,
          value_text: outcomeValue && Number.isNaN(Number(outcomeValue)) ? outcomeValue : null,
        });
      }
      return action;
    },
    onSuccess: () => {
      invalidateMethodOs();
      toast.success("Acao registrada.");
    },
    onError: () => toast.error("Erro ao registrar acao."),
  });

  const weeklyReportMutation = useMutation({
    mutationFn: () => methodOsService.generateWeeklyReport(),
    onSuccess: (report) => {
      setWeeklyReport(report);
      invalidateMethodOs();
      toast.success("Relatorio semanal gerado.");
    },
    onError: () => toast.error("Erro ao gerar relatorio semanal."),
  });

  function submitPerson() {
    if (!personForm.name.trim()) return;
    createPersonMutation.mutate({
      ...personForm,
      phone: personForm.phone?.trim() || null,
      source_channel: personForm.source_channel?.trim() || null,
      metadata: {},
    });
  }

  function submitEvent() {
    createEventTaskMutation.mutate({
      ...eventForm,
      person_id: eventForm.person_id || null,
      event_payload: parsePayload(payloadText),
      occurred_at: new Date().toISOString(),
    });
  }

  function changePillar(nextPillar: MethodPillar) {
    setEventForm((current) => ({
      ...current,
      pillar: nextPillar,
      event_type: EVENT_OPTIONS[nextPillar][0]?.value ?? "manual_event",
    }));
  }

  const dashboard = dashboardQuery.data;
  const report = weeklyReport ?? null;
  const isLoading = profileQuery.isLoading || dashboardQuery.isLoading || tasksQuery.isLoading;

  if (isLoading && !profile) {
    return (
      <div className="rounded-2xl border border-lovable-border bg-lovable-surface/72 p-6 text-sm text-lovable-ink-muted shadow-panel">
        Carregando Method OS...
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <section className="rounded-2xl border border-lovable-border/70 bg-lovable-surface/72 p-5 shadow-panel">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="info">Method OS</Badge>
              {selectedSegment ? <Badge variant="neutral">{selectedSegment.name}</Badge> : null}
            </div>
            <h2 className="mt-3 font-heading text-2xl font-bold text-lovable-ink md:text-3xl">
              {profile?.client.name ?? "Cordex client"}
            </h2>
            <p className="mt-1 text-sm text-lovable-ink-muted">
              {profile?.client.city || profile?.client.state ? `${profile.client.city ?? ""} ${profile.client.state ?? ""}`.trim() : profile?.client.slug}
            </p>
          </div>

          <div className="grid w-full gap-3 xl:max-w-3xl xl:grid-cols-[minmax(180px,1fr)_auto]">
            <Select value={selectedSegmentId} onChange={(event) => setSelectedSegmentId(event.target.value)} aria-label="Segmento">
              <option value="">Selecionar segmento</option>
              {segments.map((segment) => (
                <option key={segment.id} value={segment.id}>
                  {segment.name}
                </option>
              ))}
            </Select>
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => saveConfigMutation.mutate()} disabled={saveConfigMutation.isPending}>
                <Settings2 size={15} />
                Salvar
              </Button>
              <Button
                variant="ghost"
                onClick={() => copyPlaybookMutation.mutate()}
                disabled={!selectedSegmentId || copyPlaybookMutation.isPending}
              >
                <RefreshCw size={15} />
                Copiar playbook
              </Button>
            </div>
            <div className="flex flex-wrap gap-3 xl:col-span-2">
              {PILLARS.map((pillar) => (
                <label key={pillar.key} className="inline-flex items-center gap-2 rounded-xl border border-lovable-border/70 px-3 py-2 text-sm text-lovable-ink-muted">
                  <Checkbox
                    checked={Boolean(activePillars[pillar.key])}
                    onChange={(event) => setActivePillars((current) => ({ ...current, [pillar.key]: event.target.checked }))}
                  />
                  {pillar.label}
                </label>
              ))}
            </div>
          </div>
        </div>

        {profile?.playbook ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            <div className="rounded-2xl border border-lovable-border/70 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Canais</p>
              <p className="mt-2 text-sm text-lovable-ink">{profile.playbook.channels.join(", ") || "-"}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border/70 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Sinais</p>
              <p className="mt-2 text-sm text-lovable-ink">{profile.playbook.risk_opportunity_signals.slice(0, 4).join(", ") || "-"}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border/70 p-3">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Metricas</p>
              <p className="mt-2 text-sm text-lovable-ink">{profile.playbook.success_metrics.join(", ") || "-"}</p>
            </div>
          </div>
        ) : null}
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
        {metricCard("Abertas", dashboard?.open_tasks ?? 0, Activity, "border-[hsl(var(--lovable-primary)/0.24)] text-[hsl(var(--lovable-info))]")}
        {metricCard("Vencidas", dashboard?.overdue_tasks ?? 0, AlertTriangle, "border-[hsl(var(--lovable-danger)/0.32)] text-[hsl(var(--lovable-danger))]")}
        {metricCard("7 dias", dashboard?.completed_7d ?? 0, CheckCircle2, "border-[hsl(var(--lovable-success)/0.32)] text-[hsl(var(--lovable-success))]")}
        {metricCard("Oportunidades", dashboard?.opportunities ?? 0, ClipboardCheck, "border-[hsl(var(--lovable-warning)/0.32)] text-[hsl(var(--lovable-warning))]")}
        {metricCard("Risco", dashboard?.risk_customers ?? 0, AlertTriangle, "border-[hsl(var(--lovable-danger)/0.32)] text-[hsl(var(--lovable-danger))]")}
        {metricCard("Recuperados", dashboard?.recovered_customers ?? 0, CheckCircle2, "border-[hsl(var(--lovable-success)/0.32)] text-[hsl(var(--lovable-success))]")}
      </section>

      <section className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(360px,0.9fr)]">
        <div className="space-y-5">
          <div className="rounded-2xl border border-lovable-border/70 bg-lovable-surface/72 p-4 shadow-panel">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <h3 className="font-heading text-xl font-bold text-lovable-ink">Tarefas de hoje</h3>
                <p className="mt-1 text-sm text-lovable-ink-muted">{openTasks.length} abertas no Method OS</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => void tasksQuery.refetch()}>
                <RefreshCw size={14} />
                Atualizar
              </Button>
            </div>
            <div className="mt-4 space-y-2">
              {openTasks.length ? (
                openTasks.slice(0, 12).map((task) => (
                  <button
                    key={task.id}
                    type="button"
                    onClick={() => setSelectedTaskId(task.id)}
                    className={cn(
                      "flex w-full items-start justify-between gap-3 rounded-2xl border p-3 text-left transition",
                      selectedTask?.id === task.id
                        ? "border-[hsl(var(--lovable-primary)/0.55)] bg-[hsl(var(--lovable-primary)/0.10)]"
                        : "border-lovable-border/70 bg-lovable-bg-muted/36 hover:bg-lovable-surface-soft/70",
                    )}
                  >
                    <span className="min-w-0">
                      <span className="block truncate font-semibold text-lovable-ink">{task.title}</span>
                      <span className="mt-1 block text-xs text-lovable-ink-muted">
                        {task.person_name ?? "Sem pessoa"} | {formatDateTime(task.due_date)}
                      </span>
                    </span>
                    <span className="flex shrink-0 flex-col items-end gap-2">
                      <Badge size="sm" variant={priorityVariant(task.priority)}>
                        {task.priority}
                      </Badge>
                      <Badge size="sm" variant="neutral">
                        {task.pillar}
                      </Badge>
                    </span>
                  </button>
                ))
              ) : (
                <p className="rounded-2xl border border-dashed border-lovable-border/70 p-4 text-sm text-lovable-ink-muted">
                  Nenhuma tarefa aberta.
                </p>
              )}
            </div>
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-lovable-border/70 bg-lovable-surface/72 p-4 shadow-panel">
              <div className="mb-4 flex items-center gap-2">
                <UserPlus size={18} className="text-lovable-ink-muted" />
                <h3 className="font-heading text-lg font-bold text-lovable-ink">Pessoa</h3>
              </div>
              <div className="space-y-3">
                <Input
                  value={personForm.name}
                  onChange={(event) => setPersonForm((current) => ({ ...current, name: event.target.value }))}
                  placeholder="Nome"
                />
                <Input
                  value={personForm.phone ?? ""}
                  onChange={(event) => setPersonForm((current) => ({ ...current, phone: event.target.value }))}
                  placeholder="WhatsApp"
                />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select
                    value={personForm.person_type}
                    onChange={(event) => setPersonForm((current) => ({ ...current, person_type: event.target.value as MethodPersonType }))}
                    aria-label="Tipo de pessoa"
                  >
                    <option value="lead">Lead</option>
                    <option value="prospect">Prospect</option>
                    <option value="customer">Cliente</option>
                    <option value="inactive_customer">Cliente inativo</option>
                  </Select>
                  <Input
                    value={personForm.source_channel ?? ""}
                    onChange={(event) => setPersonForm((current) => ({ ...current, source_channel: event.target.value }))}
                    placeholder="Canal"
                  />
                </div>
                <Button className="w-full" onClick={submitPerson} disabled={!personForm.name.trim() || createPersonMutation.isPending}>
                  Criar pessoa
                </Button>
              </div>
            </div>

            <div className="rounded-2xl border border-lovable-border/70 bg-lovable-surface/72 p-4 shadow-panel">
              <div className="mb-4 flex items-center gap-2">
                <ClipboardCheck size={18} className="text-lovable-ink-muted" />
                <h3 className="font-heading text-lg font-bold text-lovable-ink">Evento</h3>
              </div>
              <div className="space-y-3">
                <Select
                  value={eventForm.person_id ?? ""}
                  onChange={(event) => setEventForm((current) => ({ ...current, person_id: event.target.value || null }))}
                  aria-label="Pessoa do evento"
                >
                  <option value="">Sem pessoa</option>
                  {people.map((person) => (
                    <option key={person.id} value={person.id}>
                      {person.name}
                    </option>
                  ))}
                </Select>
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select value={eventForm.pillar} onChange={(event) => changePillar(event.target.value as MethodPillar)} aria-label="Pilar">
                    {PILLARS.map((pillar) => (
                      <option key={pillar.key} value={pillar.key}>
                        {pillar.label}
                      </option>
                    ))}
                  </Select>
                  <Select
                    value={eventForm.event_type}
                    onChange={(event) => setEventForm((current) => ({ ...current, event_type: event.target.value }))}
                    aria-label="Tipo de evento"
                  >
                    {EVENT_OPTIONS[eventForm.pillar].map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </div>
                <Textarea value={payloadText} onChange={(event) => setPayloadText(event.target.value)} placeholder="Dados ou observacao" rows={4} />
                <Button className="w-full" onClick={submitEvent} disabled={createEventTaskMutation.isPending}>
                  Gerar tarefa
                </Button>
              </div>
            </div>
          </div>
        </div>

        <aside className="space-y-5">
          <div className="rounded-2xl border border-lovable-border/70 bg-lovable-surface/72 p-4 shadow-panel">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-heading text-xl font-bold text-lovable-ink">Acao da tarefa</h3>
                <p className="mt-1 text-sm text-lovable-ink-muted">{selectedTask?.person_name ?? "Selecione uma tarefa"}</p>
              </div>
              {selectedTask ? <Badge variant={priorityVariant(selectedTask.priority)}>{selectedTask.priority}</Badge> : null}
            </div>

            {selectedTask ? (
              <div className="mt-4 space-y-4">
                <div className="rounded-2xl border border-lovable-border/70 p-3">
                  <p className="font-semibold text-lovable-ink">{selectedTask.title}</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">
                    {formatPhoneDisplay(selectedTask.person_phone) ?? "Telefone indisponivel"} | {selectedTask.pillar}
                  </p>
                </div>

                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">
                    Mensagem editavel
                  </label>
                  <Textarea value={messageDraft} onChange={(event) => setMessageDraft(event.target.value)} rows={6} />
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <Badge variant={selectedTask.requires_human_approval ? "warning" : "neutral"}>Revisao humana</Badge>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => openWhatsappMutation.mutate()}
                      disabled={!whatsappHref || openWhatsappMutation.isPending}
                    >
                      <Send size={14} />
                      Abrir WhatsApp
                    </Button>
                  </div>
                </div>

                <div className="grid gap-3 sm:grid-cols-2">
                  <Select value={actionType} onChange={(event) => setActionType(event.target.value as MethodActionType)} aria-label="Canal da acao">
                    {ACTION_TYPES.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                  <Select value={actionResult} onChange={(event) => setActionResult(event.target.value as MethodActionResult)} aria-label="Resultado da acao">
                    {ACTION_RESULTS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                </div>
                <Textarea value={actionSummary} onChange={(event) => setActionSummary(event.target.value)} placeholder="Resumo da acao humana" rows={3} />
                <div className="grid gap-3 sm:grid-cols-2">
                  <Select value={outcomeType} onChange={(event) => setOutcomeType(event.target.value)} aria-label="Resultado medido">
                    {OUTCOME_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </Select>
                  <Input value={outcomeValue} onChange={(event) => setOutcomeValue(event.target.value)} placeholder="Valor" />
                </div>
                <Button className="w-full" variant="secondary" onClick={() => actionMutation.mutate()} disabled={actionMutation.isPending}>
                  <MessageSquare size={15} />
                  Registrar acao
                </Button>
              </div>
            ) : (
              <p className="mt-4 rounded-2xl border border-dashed border-lovable-border/70 p-4 text-sm text-lovable-ink-muted">
                Nenhuma tarefa selecionada.
              </p>
            )}
          </div>

          <div className="rounded-2xl border border-lovable-border/70 bg-lovable-surface/72 p-4 shadow-panel">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <FileText size={18} className="text-lovable-ink-muted" />
                <h3 className="font-heading text-lg font-bold text-lovable-ink">Relatorio semanal</h3>
              </div>
              <Button variant="ghost" size="sm" onClick={() => weeklyReportMutation.mutate()} disabled={weeklyReportMutation.isPending}>
                Gerar
              </Button>
            </div>
            <pre className="mt-4 max-h-80 overflow-auto whitespace-pre-wrap rounded-2xl border border-lovable-border/70 bg-lovable-bg-muted/56 p-3 text-xs leading-relaxed text-lovable-ink-muted">
              {report?.markdown ?? "Sem relatorio gerado nesta visualizacao."}
            </pre>
          </div>
        </aside>
      </section>
    </div>
  );
}
