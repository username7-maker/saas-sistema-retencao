import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, CalendarDays, Clock3, Megaphone, MessageSquareText, Target, Users } from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";

import { useAuth } from "../../hooks/useAuth";
import { MemberIntelligenceMiniCard } from "../../components/common/MemberIntelligenceMiniCard";
import { EmptyState, FilterBar, KPIStrip, PageHeader, SectionHeader, SkeletonList, StatusBadge } from "../../components/ui";
import { Badge, Button, Card, CardContent, Dialog, Drawer, FormField, Input, Select, Textarea } from "../../components/ui2";
import { crmService, normalizeLeadNotes } from "../../services/crmService";
import { memberService } from "../../services/memberService";
import type { AcquisitionLeadSummary, GrowthAudience, GrowthAudienceId, GrowthOpportunity, Lead, LeadNoteEntry } from "../../types";
import { canDeleteLead, canMutateCrm } from "../../utils/roleAccess";

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

const PREFERRED_SHIFT_OPTIONS = [
  { value: "manha", label: "Manha" },
  { value: "tarde", label: "Tarde" },
  { value: "noite", label: "Noite" },
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

const GROWTH_PRIORITY_BADGE: Record<GrowthOpportunity["priority"], { label: string; variant: "neutral" | "success" | "warning" | "danger" }> = {
  low: { label: "Baixa", variant: "neutral" },
  medium: { label: "Media", variant: "warning" },
  high: { label: "Alta", variant: "warning" },
  urgent: { label: "Urgente", variant: "danger" },
};

const GROWTH_CHANNEL_LABEL: Record<GrowthOpportunity["channel"], string> = {
  whatsapp: "WhatsApp",
  email: "E-mail",
  task: "Tarefa",
  crm_note: "Nota CRM",
  kommo: "Kommo",
};

const QUALIFICATION_BADGE_MAP: Record<string, { label: string; variant: "success" | "warning" | "neutral" }> = {
  hot: { label: "Quente", variant: "success" },
  warm: { label: "Morno", variant: "warning" },
  cold: { label: "Frio", variant: "neutral" },
};

const leadSchema = z.object({
  full_name: z.string().min(2, "Nome deve ter pelo menos 2 caracteres"),
  email: z.string().email("E-mail invalido").optional().or(z.literal("")),
  phone: z.string().optional(),
  source: z.string().optional(),
  channel: z.string().optional(),
  campaign: z.string().optional(),
  desired_goal: z.string().optional(),
  preferred_shift: z.string().optional(),
  trial_interest: z.boolean().default(false),
  scheduled_for: z.string().optional(),
  consent_lgpd: z.boolean().default(false),
  consent_communication: z.boolean().default(false),
  qualification_urgency: z.string().optional(),
  stage: z.enum(LEAD_STAGE_VALUES),
  estimated_value: z.coerce.number().min(0, "Valor nao pode ser negativo").optional(),
  notes: z.string().optional(),
  lost_reason: z.string().optional(),
  handoff_plan_name: z.string().optional(),
  handoff_join_date: z.string().optional(),
  handoff_notes: z.string().optional(),
  handoff_email_confirmed: z.boolean().default(false),
  handoff_phone_confirmed: z.boolean().default(false),
}).superRefine((data, ctx) => {
  if (data.stage !== "won") return;
  if (!data.handoff_plan_name?.trim()) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Informe o plano do membro convertido.",
      path: ["handoff_plan_name"],
    });
  }
  if (!data.handoff_join_date) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Informe a data de inicio/matricula.",
      path: ["handoff_join_date"],
    });
  }
});

type LeadFormValues = z.infer<typeof leadSchema>;

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

function leadNoteTypeLabel(note: LeadNoteEntry): string {
  if (note.type === "contact_log") return "Contato";
  if (note.type === "public_booking") return "Booking";
  if (note.type === "public_diagnosis_requested") return "Diagnostico";
  if (note.type === "acquisition_capture") return "Captura";
  if (note.type === "acquisition_qualification") return "Qualificacao";
  return "Observacao";
}

function leadNoteMeta(note: LeadNoteEntry): string {
  const parts = [leadNoteTypeLabel(note)];
  if (note.channel) parts.push(note.channel);
  if (note.outcome) parts.push(note.outcome);
  if (note.author_name) parts.push(note.author_name);
  return parts.join(" · ");
}

function latestRawNoteByType(lead: Lead, type: string): Record<string, unknown> | null {
  if (!Array.isArray(lead.notes)) return null;
  for (const note of [...lead.notes].reverse()) {
    if (typeof note === "object" && note !== null && !Array.isArray(note) && note.type === type) {
      return note;
    }
  }
  return null;
}

function stringField(note: Record<string, unknown> | null, key: string): string | null {
  const value = note?.[key];
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function booleanField(note: Record<string, unknown> | null, key: string): boolean | null {
  const value = note?.[key];
  return typeof value === "boolean" ? value : null;
}

function numberField(note: Record<string, unknown> | null, key: string): number | null {
  const value = note?.[key];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() && !Number.isNaN(Number(value))) return Number(value);
  return null;
}

function stringArrayField(note: Record<string, unknown> | null, key: string): string[] {
  const value = note?.[key];
  if (!Array.isArray(value)) return [];
  return value.filter((item): item is string => typeof item === "string" && item.trim().length > 0);
}

function getAcquisitionSummaryFromLead(lead: Lead): AcquisitionLeadSummary | null {
  const capture = latestRawNoteByType(lead, "acquisition_capture");
  const qualification = latestRawNoteByType(lead, "acquisition_qualification");
  if (!capture && !qualification) return null;
  const scheduledFor = stringField(capture, "scheduled_for");

  return {
    lead_id: lead.id,
    full_name: lead.full_name,
    source: stringField(capture, "source") ?? lead.source ?? null,
    channel: stringField(capture, "channel"),
    campaign: stringField(capture, "campaign"),
    desired_goal: stringField(capture, "desired_goal"),
    preferred_shift: stringField(capture, "preferred_shift"),
    qualification_score: numberField(qualification, "score"),
    qualification_label: stringField(qualification, "label"),
    next_action: stringField(qualification, "next_action"),
    has_trial_booking: Boolean(scheduledFor),
    next_booking_at: scheduledFor,
    consent_lgpd: booleanField(capture, "consent_lgpd"),
    consent_communication: booleanField(capture, "consent_communication"),
    reasons: stringArrayField(qualification, "reasons"),
    missing_fields: stringArrayField(qualification, "missing_fields"),
  };
}

function qualificationBadge(summary: AcquisitionLeadSummary | null) {
  if (!summary?.qualification_label) return null;
  return QUALIFICATION_BADGE_MAP[summary.qualification_label] ?? { label: summary.qualification_label, variant: "neutral" as const };
}

function buildLeadDefaults(lead?: Lead | null): LeadFormValues {
  return lead
    ? {
        full_name: lead.full_name,
        email: lead.email ?? "",
        phone: lead.phone ?? "",
        source: lead.source ?? "",
        channel: "",
        campaign: "",
        desired_goal: "",
        preferred_shift: "",
        trial_interest: false,
        scheduled_for: "",
        consent_lgpd: false,
        consent_communication: false,
        qualification_urgency: "",
        stage: lead.stage,
        estimated_value: lead.estimated_value,
        notes: "",
        lost_reason: lead.lost_reason ?? "",
        handoff_plan_name: "",
        handoff_join_date: "",
        handoff_notes: "",
        handoff_email_confirmed: Boolean(lead.email),
        handoff_phone_confirmed: Boolean(lead.phone),
      }
    : {
        full_name: "",
        email: "",
        phone: "",
        source: "",
        channel: "",
        campaign: "",
        desired_goal: "",
        preferred_shift: "",
        trial_interest: false,
        scheduled_for: "",
        consent_lgpd: false,
        consent_communication: false,
        qualification_urgency: "",
        stage: "new",
        estimated_value: 0,
        notes: "",
        lost_reason: "",
        handoff_plan_name: "",
        handoff_join_date: "",
        handoff_notes: "",
        handoff_email_confirmed: false,
        handoff_phone_confirmed: false,
      };
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
  readOnly: boolean;
  onSaved: () => void;
}

function AcquisitionSummaryCard({ lead }: { lead: Lead }) {
  const summary = getAcquisitionSummaryFromLead(lead);
  const badge = qualificationBadge(summary);
  if (!summary) return null;

  return (
    <div className="rounded-2xl border border-lovable-primary/25 bg-lovable-primary-soft/20 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <SectionHeader
          title="Acquisition OS"
          subtitle="Origem, qualificacao e proxima acao capturadas antes do CRM."
        />
        {badge ? <Badge variant={badge.variant}>Lead {badge.label}</Badge> : null}
      </div>
      <div className="grid gap-3 text-sm text-lovable-ink md:grid-cols-2">
        <div className="rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2">
          <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">Origem / campanha</p>
          <p className="mt-1 font-semibold">{[summary.channel, summary.campaign].filter(Boolean).join(" / ") || summary.source || "Sem rastreio"}</p>
        </div>
        <div className="rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2">
          <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">Score de propensao</p>
          <p className="mt-1 font-semibold">{summary.qualification_score ?? "--"} pts</p>
        </div>
        <div className="rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2">
          <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">Turno preferido</p>
          <p className="mt-1 font-semibold">{summary.preferred_shift || "Nao informado"}</p>
        </div>
        <div className="rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2">
          <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">Aula experimental</p>
          <p className="mt-1 font-semibold">{summary.next_booking_at ? formatDateTime(summary.next_booking_at) : "Nao agendada"}</p>
        </div>
      </div>
      {summary.next_action ? (
        <div className="mt-3 rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2 text-sm text-lovable-ink">
          <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">Proxima melhor acao</p>
          <p className="mt-1 font-semibold">{summary.next_action}</p>
        </div>
      ) : null}
    </div>
  );
}

interface GrowthOsPanelProps {
  audiences: GrowthAudience[];
  selectedAudienceId: GrowthAudienceId | "all";
  onSelectAudience: (audienceId: GrowthAudienceId | "all") => void;
  onPrepare: (opportunity: GrowthOpportunity) => void;
  preparingOpportunityId: string | null;
  canPrepare: boolean;
}

function GrowthOsPanel({
  audiences,
  selectedAudienceId,
  onSelectAudience,
  onPrepare,
  preparingOpportunityId,
  canPrepare,
}: GrowthOsPanelProps) {
  const total = audiences.reduce((sum, audience) => sum + audience.count, 0);
  const selectedAudiences =
    selectedAudienceId === "all"
      ? audiences
      : audiences.filter((audience) => audience.id === selectedAudienceId);
  const visibleItems = selectedAudiences.flatMap((audience) => audience.items).slice(0, 8);

  return (
    <Card>
      <CardContent className="pt-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <SectionHeader
            title="Growth OS"
            subtitle="Audiencias acionaveis para conversao, reativacao, renovacao, NPS e indicacao."
            count={total}
          />
          <Badge variant={total > 0 ? "warning" : "neutral"}>{total} oportunidade(s)</Badge>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Button
            type="button"
            size="sm"
            variant={selectedAudienceId === "all" ? "primary" : "secondary"}
            onClick={() => onSelectAudience("all")}
          >
            Todas
          </Button>
          {audiences.map((audience) => (
            <Button
              key={audience.id}
              type="button"
              size="sm"
              variant={selectedAudienceId === audience.id ? "primary" : "secondary"}
              onClick={() => onSelectAudience(audience.id)}
            >
              {audience.label}
              <span className="rounded-full bg-lovable-surface px-2 py-0.5 text-[11px]">{audience.count}</span>
            </Button>
          ))}
        </div>

        {selectedAudiences.length > 0 ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            {selectedAudiences.slice(0, 3).map((audience) => (
              <div key={audience.id} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft/35 p-4">
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-lovable-ink">{audience.label}</p>
                  <Badge variant={GROWTH_PRIORITY_BADGE[audience.priority].variant}>
                    {GROWTH_PRIORITY_BADGE[audience.priority].label}
                  </Badge>
                </div>
                <p className="mt-2 text-xs text-lovable-ink-muted">{audience.summary}</p>
                <p className="mt-3 text-[11px] uppercase tracking-widest text-lovable-ink-muted">Teste sugerido</p>
                <p className="mt-1 text-xs text-lovable-ink">{audience.experiment_hint}</p>
              </div>
            ))}
          </div>
        ) : null}

        <div className="mt-5 space-y-2">
          {visibleItems.length === 0 ? (
            <EmptyState
              icon={Megaphone}
              title="Nenhuma oportunidade de growth agora"
              description="Quando houver leads quentes, alunos inativos, NPS baixo ou promotores, eles aparecem aqui com a proxima acao."
            />
          ) : (
            visibleItems.map((item) => {
              const priority = GROWTH_PRIORITY_BADGE[item.priority];
              const isPreparing = preparingOpportunityId === item.id;
              return (
                <div
                  key={item.id}
                  className="grid gap-3 rounded-xl border border-lovable-border bg-lovable-surface-soft/30 px-4 py-3 lg:grid-cols-[minmax(0,2fr)_1fr_auto]"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="truncate text-sm font-semibold text-lovable-ink">{item.display_name}</p>
                      <Badge variant={priority.variant}>{priority.label}</Badge>
                      <Badge variant={item.consent_ok || !item.consent_required ? "success" : "warning"}>
                        {item.consent_ok || !item.consent_required ? "Contato liberado" : "Revisar consentimento"}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-lovable-ink">{item.action_label}</p>
                    <p className="mt-1 text-xs text-lovable-ink-muted">{item.reason}</p>
                  </div>
                  <div className="text-xs text-lovable-ink-muted">
                    <p>
                      <span className="font-semibold text-lovable-ink">Canal:</span> {GROWTH_CHANNEL_LABEL[item.channel]}
                    </p>
                    <p>
                      <span className="font-semibold text-lovable-ink">Turno:</span> {item.preferred_shift || "Nao informado"}
                    </p>
                    <p>
                      <span className="font-semibold text-lovable-ink">Score:</span> {item.score}
                    </p>
                  </div>
                  <div className="flex items-center justify-start lg:justify-end">
                    <Button
                      type="button"
                      size="sm"
                      variant="primary"
                      disabled={!canPrepare || isPreparing}
                      onClick={() => onPrepare(item)}
                    >
                      {isPreparing ? "Preparando..." : item.channel === "whatsapp" ? "Preparar WhatsApp" : "Criar tarefa"}
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </CardContent>
    </Card>
  );
}

function LeadFormDrawer({ open, onClose, lead, readOnly, onSaved }: LeadFormDrawerProps) {
  const isEditing = Boolean(lead);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [noteDraft, setNoteDraft] = useState("");
  const [noteHistory, setNoteHistory] = useState<LeadNoteEntry[]>([]);
  const navigate = useNavigate();
  const { user } = useAuth();
  const canRemoveLead = canDeleteLead(user?.role);

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

  const intelligenceContextQuery = useQuery({
    queryKey: ["members", "intelligence-context", lead?.converted_member_id],
    queryFn: async () => {
      if (!lead?.converted_member_id) {
        throw new Error("MEMBRO_INVALIDO");
      }
      return memberService.getIntelligenceContext(lead.converted_member_id);
    },
    enabled: open && Boolean(lead?.converted_member_id),
    staleTime: 60_000,
  });

  useEffect(() => {
    reset(buildLeadDefaults(lead));
    setNoteDraft("");
    setNoteHistory(lead ? normalizeLeadNotes(lead.notes) : []);
  }, [lead, reset]);

  const createMutation = useMutation({
    mutationFn: crmService.captureAcquisitionLead,
    onSuccess: () => {
      toast.success("Lead capturado e qualificado com sucesso!");
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
        lost_reason: data.stage === "lost" ? data.lost_reason || undefined : undefined,
        conversion_handoff: data.stage === "won"
          ? {
              plan_name: data.handoff_plan_name?.trim() || "",
              join_date: data.handoff_join_date || "",
              email_confirmed: data.handoff_email_confirmed,
              phone_confirmed: data.handoff_phone_confirmed,
              notes: data.handoff_notes?.trim() || undefined,
            }
          : undefined,
      }),
    onSuccess: () => {
      toast.success("Lead atualizado com sucesso!");
      onSaved();
      onClose();
    },
      onError: () => toast.error("Erro ao atualizar lead. Tente novamente."),
  });

  const appendNoteMutation = useMutation({
    mutationFn: (payload: { leadId: string; text: string }) =>
      crmService.appendLeadNote(payload.leadId, {
        text: payload.text,
        entry_type: "note",
      }),
    onSuccess: (updatedLead) => {
      setNoteHistory(normalizeLeadNotes(updatedLead.notes));
      setNoteDraft("");
      toast.success("Observacao adicionada ao historico.");
      onSaved();
    },
    onError: () => toast.error("Erro ao adicionar observacao ao historico."),
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
    if (readOnly) return;
    if (isEditing && lead) {
      updateMutation.mutate({ id: lead.id, data: values });
      return;
    }

    createMutation.mutate({
      full_name: values.full_name,
      email: values.email || undefined,
      phone: values.phone || undefined,
      source: values.source || "landing_page",
      channel: values.channel || undefined,
      campaign: values.campaign || undefined,
      desired_goal: values.desired_goal || undefined,
      preferred_shift: values.preferred_shift || undefined,
      trial_interest: values.trial_interest,
      scheduled_for: values.scheduled_for ? new Date(values.scheduled_for).toISOString() : undefined,
      consent_lgpd: values.consent_lgpd,
      consent_communication: values.consent_communication,
      operator_note: values.notes || undefined,
      qualification_answers: values.qualification_urgency ? { urgency: values.qualification_urgency } : undefined,
      estimated_value: values.estimated_value,
      acquisition_cost: 0,
    });
  }

  function handleAppendNote() {
    if (!lead || readOnly) return;
    const text = noteDraft.trim();
    if (!text) {
      toast.error("Digite uma observacao para adicionar ao historico.");
      return;
    }
    appendNoteMutation.mutate({ leadId: lead.id, text });
  }

  const isPending = isSubmitting || createMutation.isPending || updateMutation.isPending;

  return (
    <>
      <Drawer open={open} onClose={onClose} title={readOnly ? "Detalhes do Lead" : isEditing ? "Editar Lead" : "Novo Lead"}>
        <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-4 p-4">
          {isEditing && lead && !readOnly ? (
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
                <Input {...register("full_name")} placeholder="Nome completo" readOnly={readOnly} disabled={readOnly} />
              </FormField>

              <div className="grid gap-4 md:grid-cols-2">
                <FormField label="E-mail" error={errors.email?.message}>
                  <Input {...register("email")} type="email" placeholder="email@exemplo.com" readOnly={readOnly} disabled={readOnly} />
                </FormField>

                <FormField label="Telefone">
                  <Input {...register("phone")} placeholder="(11) 99999-9999" readOnly={readOnly} disabled={readOnly} />
                </FormField>
              </div>

              <FormField label="Origem">
                <Select {...register("source")} disabled={readOnly}>
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

          {isEditing && lead ? <AcquisitionSummaryCard lead={lead} /> : null}

          {!isEditing ? (
            <div className="rounded-2xl border border-lovable-primary/25 bg-lovable-primary-soft/20 p-4">
              <SectionHeader
                title="Captura AI-first"
                subtitle="Dados que ajudam a direcionar o lead certo para o responsavel certo."
              />
              <div className="grid gap-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <FormField label="Canal">
                    <Input {...register("channel")} placeholder="Ex: Instagram Ads, Google, recepcao" readOnly={readOnly} disabled={readOnly} />
                  </FormField>
                  <FormField label="Campanha">
                    <Input {...register("campaign")} placeholder="Ex: Desafio Verao, Indicacao, Aula gratis" readOnly={readOnly} disabled={readOnly} />
                  </FormField>
                </div>

                <FormField label="Objetivo declarado">
                  <Textarea
                    {...register("desired_goal")}
                    placeholder="Ex: emagrecer, ganhar massa, voltar a treinar, melhorar dor nas costas."
                    rows={2}
                    readOnly={readOnly}
                    disabled={readOnly}
                  />
                </FormField>

                <div className="grid gap-4 md:grid-cols-2">
                  <FormField label="Turno preferido">
                    <Select {...register("preferred_shift")} disabled={readOnly}>
                      <option value="">Nao informado</option>
                      {PREFERRED_SHIFT_OPTIONS.map((shift) => (
                        <option key={shift.value} value={shift.value}>
                          {shift.label}
                        </option>
                      ))}
                    </Select>
                  </FormField>
                  <FormField label="Aula experimental">
                    <Input {...register("scheduled_for")} type="datetime-local" readOnly={readOnly} disabled={readOnly} />
                  </FormField>
                </div>

                <FormField label="Urgencia / prazo">
                  <Input {...register("qualification_urgency")} placeholder="Ex: quer comecar essa semana" readOnly={readOnly} disabled={readOnly} />
                </FormField>

                <div className="grid gap-3 text-sm text-lovable-ink md:grid-cols-3">
                  <label className="flex items-center gap-2 rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2">
                    <input type="checkbox" {...register("trial_interest")} className="h-4 w-4 rounded border-lovable-border" disabled={readOnly} />
                    Quer aula experimental
                  </label>
                  <label className="flex items-center gap-2 rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2">
                    <input type="checkbox" {...register("consent_lgpd")} className="h-4 w-4 rounded border-lovable-border" disabled={readOnly} />
                    Consentiu LGPD
                  </label>
                  <label className="flex items-center gap-2 rounded-xl border border-lovable-border bg-lovable-surface/60 px-3 py-2">
                    <input type="checkbox" {...register("consent_communication")} className="h-4 w-4 rounded border-lovable-border" disabled={readOnly} />
                    Pode receber contato
                  </label>
                </div>
              </div>
            </div>
          ) : null}

          {isEditing && lead?.converted_member_id ? (
            <MemberIntelligenceMiniCard
              context={intelligenceContextQuery.data ?? null}
              isLoading={intelligenceContextQuery.isLoading}
              isError={intelligenceContextQuery.isError}
              onRetry={() => void intelligenceContextQuery.refetch()}
              title="Contexto canonico do membro convertido"
            />
          ) : null}

          <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft/35 p-4">
            <SectionHeader title="Pipeline" subtitle="Estagio atual e valor estimado da oportunidade." />
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Estagio">
                <Select {...register("stage")} disabled={readOnly || !isEditing}>
                  {STAGE_ORDER.map((stage) => (
                    <option key={stage} value={stage}>
                      {STAGE_LABELS[stage]}
                    </option>
                  ))}
                </Select>
              </FormField>

              <FormField label="Valor estimado (R$)" error={errors.estimated_value?.message}>
                <Input {...register("estimated_value")} type="number" min={0} step={0.01} placeholder="0,00" readOnly={readOnly} disabled={readOnly} />
              </FormField>
            </div>
          </div>

          <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft/35 p-4">
            <SectionHeader
              title={isEditing ? "Historico comercial" : "Notas"}
              subtitle={
                isEditing
                  ? "Timeline de contatos e observacoes. Novas notas entram por append, sem sobrescrever o historico."
                  : "Contexto comercial inicial e observacoes relevantes."
              }
            />
            <div className="grid gap-4">
              {isEditing ? (
                <>
                  {noteHistory.length > 0 ? (
                    <div className="space-y-3">
                      {noteHistory.map((note) => (
                        <div key={note.id} className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge variant={note.type === "contact_log" ? "info" : "neutral"}>{leadNoteTypeLabel(note)}</Badge>
                            <p className="text-xs text-lovable-ink-muted">{leadNoteMeta(note)}</p>
                          </div>
                          <p className="mt-2 text-sm text-lovable-ink">{note.text}</p>
                          <div className="mt-2 flex items-center gap-1 text-xs text-lovable-ink-muted">
                            <Clock3 size={12} />
                            {formatDateTime(note.created_at)}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-lovable-border px-4 py-4 text-sm text-lovable-ink-muted">
                      Nenhuma observacao registrada ainda para este lead.
                    </div>
                  )}

                  {!readOnly ? (
                    <FormField label="Adicionar observacao ao historico">
                      <Textarea
                        value={noteDraft}
                        onChange={(event) => setNoteDraft(event.target.value)}
                        placeholder="Ex: cliente pediu retorno na sexta, prefere horario noturno."
                        rows={3}
                      />
                    </FormField>
                  ) : null}
                  {!readOnly ? (
                    <div className="flex justify-end">
                      <Button
                        type="button"
                        variant="secondary"
                        disabled={appendNoteMutation.isPending}
                        onClick={handleAppendNote}
                      >
                        <MessageSquareText size={14} />
                        {appendNoteMutation.isPending ? "Adicionando..." : "Adicionar ao historico"}
                      </Button>
                    </div>
                  ) : null}
                </>
              ) : (
                <FormField label="Notas iniciais">
                  <Textarea
                    {...register("notes")}
                    placeholder="Ex: cliente busca plano para casal, melhor horario noturno."
                    rows={3}
                    readOnly={readOnly}
                    disabled={readOnly}
                  />
                </FormField>
              )}

              {watchedStage === "lost" ? (
                <FormField label="Motivo da perda">
                  <Input {...register("lost_reason")} placeholder="Descreva o motivo..." readOnly={readOnly} disabled={readOnly} />
                </FormField>
              ) : null}
              {watchedStage === "won" ? (
                <div className="grid gap-4 rounded-2xl border border-lovable-primary/20 bg-lovable-primary-soft/20 p-4 md:grid-cols-2">
                  <FormField label="Plano do membro" required error={errors.handoff_plan_name?.message}>
                    <Input {...register("handoff_plan_name")} placeholder="Ex: Plano Premium" readOnly={readOnly} disabled={readOnly} />
                  </FormField>
                  <FormField label="Data de inicio/matricula" required error={errors.handoff_join_date?.message}>
                    <Input {...register("handoff_join_date")} type="date" readOnly={readOnly} disabled={readOnly} />
                  </FormField>
                  <label className="flex items-center gap-2 text-sm text-lovable-ink">
                    <input type="checkbox" {...register("handoff_email_confirmed")} className="h-4 w-4 rounded border-lovable-border" disabled={readOnly} />
                    E-mail confirmado
                  </label>
                  <label className="flex items-center gap-2 text-sm text-lovable-ink">
                    <input type="checkbox" {...register("handoff_phone_confirmed")} className="h-4 w-4 rounded border-lovable-border" disabled={readOnly} />
                    Telefone confirmado
                  </label>
                  <div className="md:col-span-2">
                    <FormField label="Handoff para operacao e professor">
                      <Textarea
                        {...register("handoff_notes")}
                        rows={3}
                        placeholder="Ex: foco em emagrecimento, prefere horario noturno e chegou por indicacao."
                        readOnly={readOnly}
                        disabled={readOnly}
                      />
                    </FormField>
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          <div className="flex gap-2 pt-2">
            {!readOnly ? (
              <Button type="submit" variant="primary" disabled={isPending} className="flex-1">
                {isPending ? "Salvando..." : isEditing ? "Salvar alteracoes" : "Capturar e qualificar lead"}
              </Button>
            ) : null}
            <Button type="button" variant="ghost" onClick={onClose} className={readOnly ? "flex-1" : undefined}>
              {readOnly ? "Fechar" : "Cancelar"}
            </Button>
          </div>

          {isEditing && lead && canRemoveLead && !readOnly ? (
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
  const [selectedGrowthAudienceId, setSelectedGrowthAudienceId] = useState<GrowthAudienceId | "all">("all");
  const { user } = useAuth();
  const canMutate = canMutateCrm(user?.role);

  const leadsQuery = useQuery({
    queryKey: ["crm", "leads"],
    queryFn: crmService.listLeads,
    staleTime: 5 * 60 * 1000,
  });

  const growthAudiencesQuery = useQuery({
    queryKey: ["crm", "growth", "audiences"],
    queryFn: crmService.listGrowthAudiences,
    staleTime: 2 * 60 * 1000,
  });

  const moveMutation = useMutation({
    mutationFn: ({ leadId, stage }: { leadId: string; stage: Lead["stage"] }) => crmService.updateLeadStage(leadId, stage),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["crm", "leads"] });
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "commercial"] });
    },
    onError: () => toast.error("Nao foi possivel mover o lead."),
  });

  const prepareGrowthMutation = useMutation({
    mutationFn: (opportunity: GrowthOpportunity) =>
      crmService.prepareGrowthOpportunity(opportunity.id, {
        channel: opportunity.channel,
        create_task: opportunity.channel !== "whatsapp",
      }),
    onSuccess: (prepared) => {
      if (prepared.warnings.length > 0) {
        toast.error(prepared.warnings[0]);
      } else {
        toast.success(prepared.task_id ? "Tarefa criada para execucao." : "Acao preparada com sucesso.");
      }
      if (prepared.whatsapp_url) {
        window.open(prepared.whatsapp_url, "_blank", "noopener,noreferrer");
      }
      void queryClient.invalidateQueries({ queryKey: ["crm", "growth", "audiences"] });
      void queryClient.invalidateQueries({ queryKey: ["crm", "leads"] });
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => toast.error("Nao foi possivel preparar esta oportunidade."),
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
        const acquisition = getAcquisitionSummaryFromLead(lead);
        const haystack = normalizeText([
          lead.full_name,
          lead.email ?? "",
          lead.phone ?? "",
          lead.source ?? "",
          acquisition?.channel ?? "",
          acquisition?.campaign ?? "",
          acquisition?.desired_goal ?? "",
          acquisition?.preferred_shift ?? "",
        ].join(" "));
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
    const conversionRate = total > 0 ? (allLeads.filter((lead) => lead.stage === "won").length / total) * 100 : 0;
    const acquisitionSummaries = allLeads.map(getAcquisitionSummaryFromLead).filter((summary): summary is AcquisitionLeadSummary => summary !== null);
    const hotLeads = acquisitionSummaries.filter((summary) => summary.qualification_label === "hot").length;
    const trialScheduled = acquisitionSummaries.filter((summary) => summary.has_trial_booking).length;

    return [
      { label: "Total ativos", value: totalActive, tone: "neutral" as const },
      { label: "Leads quentes", value: hotLeads, tone: "success" as const },
      { label: "Aulas agendadas", value: trialScheduled, tone: "warning" as const },
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
        actions={canMutate ? (
          <Button variant="primary" onClick={handleNewLead}>
            Nova captura
          </Button>
        ) : undefined}
      />

      <KPIStrip items={kpiItems} />

      {growthAudiencesQuery.isError ? (
        <Card>
          <CardContent className="pt-5">
            <EmptyState
              icon={AlertTriangle}
              title="Growth OS indisponivel"
              description="O CRM continua funcionando, mas as audiencias de campanha nao carregaram agora."
            />
          </CardContent>
        </Card>
      ) : growthAudiencesQuery.isLoading ? (
        <Card>
          <CardContent className="pt-5">
            <SkeletonList rows={3} cols={3} />
          </CardContent>
        </Card>
      ) : (
        <GrowthOsPanel
          audiences={growthAudiencesQuery.data ?? []}
          selectedAudienceId={selectedGrowthAudienceId}
          onSelectAudience={setSelectedGrowthAudienceId}
          onPrepare={(opportunity) => prepareGrowthMutation.mutate(opportunity)}
          preparingOpportunityId={prepareGrowthMutation.variables?.id ?? null}
          canPrepare={canMutate}
        />
      )}

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
              description={canMutate ? "Tente ajustar os filtros ou adicione um novo lead" : "Tente ajustar os filtros para localizar um lead."}
              action={canMutate ? { label: "Nova captura", onClick: handleNewLead } : undefined}
            />
          ) : (
            <div className="space-y-2">
              {filteredLeads.map((lead) => {
                const nextStage = NEXT_STAGE[lead.stage];
                const contactAlert = getContactAlert(lead);
                const acquisition = getAcquisitionSummaryFromLead(lead);
                const acquisitionBadge = qualificationBadge(acquisition);
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
                        {acquisitionBadge ? (
                          <Badge variant={acquisitionBadge.variant} className="px-2 py-0.5 text-[11px] normal-case tracking-normal">
                            {acquisition?.qualification_score ?? "--"} pts
                          </Badge>
                        ) : null}
                      </div>
                      <p className="mt-1 truncate text-xs text-lovable-ink-muted">{lead.email ?? lead.phone ?? "Sem contato principal"}</p>
                      {acquisition ? (
                        <div className="mt-2 flex flex-wrap gap-2 text-[11px] text-lovable-ink-muted">
                          {acquisition.channel ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-lovable-surface px-2 py-1">
                              <Target size={12} />
                              {acquisition.channel}
                            </span>
                          ) : null}
                          {acquisition.preferred_shift ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-lovable-surface px-2 py-1">
                              Turno {acquisition.preferred_shift}
                            </span>
                          ) : null}
                          {acquisition.next_booking_at ? (
                            <span className="inline-flex items-center gap-1 rounded-full bg-lovable-surface px-2 py-1">
                              <CalendarDays size={12} />
                              Experimental agendada
                            </span>
                          ) : null}
                        </div>
                      ) : null}
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
                      {canMutate && nextStage ? (
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => {
                            if (nextStage === "won") {
                              setSelectedLead({ ...lead, stage: "won" });
                              setDrawerOpen(true);
                              return;
                            }
                            moveMutation.mutate({ leadId: lead.id, stage: nextStage });
                          }}
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

      <LeadFormDrawer
        open={drawerOpen}
        onClose={handleDrawerClose}
        lead={selectedLead}
        readOnly={!canMutate}
        onSaved={handleSaved}
      />
    </section>
  );
}
