import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowUpRight,
  Bot,
  CalendarClock,
  CheckCheck,
  Clock3,
  MessageCircle,
  PhoneCall,
  RefreshCw,
  ShieldAlert,
  UserSearch,
} from "lucide-react";
import { useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";

import { AIAssistantPanel } from "../../components/common/AIAssistantPanel";
import { AiInsightCard } from "../../components/common/AiInsightCard";
import { DashboardActions } from "../../components/common/DashboardActions";
import { MemberIntelligenceMiniCard } from "../../components/common/MemberIntelligenceMiniCard";
import { PreferredShiftBadge } from "../../components/common/PreferredShiftBadge";
import { QuickActions } from "../../components/common/QuickActions";
import { useAuth } from "../../hooks/useAuth";
import { useRetentionDashboard } from "../../hooks/useDashboard";
import { dashboardService, type RetentionQueueItem } from "../../services/dashboardService";
import { memberService } from "../../services/memberService";
import { riskAlertService } from "../../services/riskAlertService";
import { Badge, Button, Drawer, Pagination, Skeleton, cn } from "../../components/ui2";
import { EmptyState, FilterBar, KPIStrip, PageHeader, RiskBadge, SectionHeader, SkeletonList } from "../../components/ui";
import { getPermissionAwareMessage } from "../../utils/httpErrors";
import { getPreferredShiftKey, getPreferredShiftLabel } from "../../utils/preferredShift";
import { canResolveRetentionAlert } from "../../utils/roleAccess";
import { buildWhatsAppHref, formatPhoneDisplay, normalizeWhatsAppPhone } from "../../utils/whatsapp";

type QueueLevel = "all" | "red" | "yellow";
type QueuePreferredShift = "all" | "overnight" | "morning" | "afternoon" | "evening";
type QueueRetentionStage = "all" | "monitoring" | "attention" | "recovery" | "reactivation" | "manager_escalation" | "cold_base";

const CHURN_OPTIONS = [
  { value: "all", label: "Todos os churns" },
  { value: "early_dropout", label: "Onboarding frágil" },
  { value: "voluntary_dissatisfaction", label: "Insatisfação" },
  { value: "voluntary_financial", label: "Financeiro" },
  { value: "voluntary_relocation", label: "Mudança de rotina" },
  { value: "involuntary_inactivity", label: "Inatividade" },
  { value: "involuntary_seasonal", label: "Sazonal" },
  { value: "unknown", label: "Padrão misto" },
] as const;

const PLAN_CYCLE_OPTIONS = [
  { value: "all", label: "Todos os planos" },
  { value: "monthly", label: "Mensal" },
  { value: "semiannual", label: "Semestral" },
  { value: "annual", label: "Anual" },
] as const;

const PREFERRED_SHIFT_OPTIONS = [
  { value: "all", label: "Todos os turnos" },
  { value: "overnight", label: "Madrugada" },
  { value: "morning", label: "Manha" },
  { value: "afternoon", label: "Tarde" },
  { value: "evening", label: "Noite" },
] as const;

const RETENTION_STAGE_OPTIONS: Array<{ value: QueueRetentionStage; label: string; description: string }> = [
  { value: "all", label: "Todos os estagios", description: "Fila completa por risco e contexto." },
  { value: "attention", label: "Atencao agora", description: "7-13 dias sem check-in." },
  { value: "recovery", label: "Recuperar esta semana", description: "14-29 dias sem check-in." },
  { value: "reactivation", label: "Reativar 30+ dias", description: "30-44 dias sem check-in." },
  { value: "manager_escalation", label: "Escalar gerente", description: "45-59 dias sem check-in." },
  { value: "cold_base", label: "Base fria", description: "60+ dias sem check-in." },
  { value: "monitoring", label: "Monitoramento", description: "0-6 dias sem check-in." },
];

const CHURN_META: Record<string, { label: string; description: string }> = {
  early_dropout: {
    label: "Onboarding frágil",
    description: "Aluno novo com sinais de abandono precoce.",
  },
  voluntary_dissatisfaction: {
    label: "Insatisfação",
    description: "Percepção de valor ou experiência ruim.",
  },
  voluntary_financial: {
    label: "Financeiro",
    description: "Preço e orçamento viraram objeção.",
  },
  voluntary_relocation: {
    label: "Mudança de rotina",
    description: "Horário, cidade ou agenda mudaram.",
  },
  involuntary_inactivity: {
    label: "Inatividade",
    description: "A rotina quebrou e o treino saiu do radar.",
  },
  involuntary_seasonal: {
    label: "Sazonal",
    description: "Queda recorrente em períodos específicos.",
  },
  unknown: {
    label: "Padrão misto",
    description: "Sinal composto, ainda sem causa dominante.",
  },
};

const PLAYBOOK_PRIORITY_VARIANT: Record<string, "danger" | "warning" | "info" | "neutral"> = {
  urgent: "danger",
  high: "warning",
  medium: "info",
  low: "neutral",
};

const QUEUE_GRID_COLUMNS = "lg:grid-cols-[minmax(0,2.15fr)_150px_110px_145px_120px_130px_125px_220px]";

type SignalRow = {
  label: string;
  value: string;
  tone: "danger" | "warning" | "neutral";
  progressPct: number;
};

type ChurnHighlight = {
  key: string;
  label: string;
  description: string;
  count: number;
  pct: number;
};

function formatCurrency(value: number): string {
  return value.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

function formatChurnType(value: string | null): string {
  if (!value) return "Sem classificação";
  return CHURN_META[value]?.label ?? value.replace(/_/g, " ");
}

function formatRetentionStage(item: RetentionQueueItem): string {
  return item.retention_stage_label || RETENTION_STAGE_OPTIONS.find((option) => option.value === item.retention_stage)?.label || "Sem estagio";
}

function retentionStageVariant(stage: string | null | undefined): "danger" | "warning" | "info" | "success" | "neutral" {
  if (stage === "manager_escalation") return "danger";
  if (stage === "recovery" || stage === "reactivation") return "warning";
  if (stage === "attention") return "info";
  if (stage === "monitoring") return "success";
  return "neutral";
}

function formatOwnerRole(value: string | null | undefined): string {
  if (!value) return "Equipe";
  const normalized = value.toLowerCase();
  if (normalized === "manager") return "Gerente";
  if (normalized === "trainer" || normalized === "coach") return "Professor";
  if (normalized === "reception" || normalized === "receptionist") return "Recepcao";
  return value.replace(/_/g, " ");
}

function formatLastContact(value: string | null): string {
  if (!value) return "Sem contato";
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return "Sem contato";
  const diffDays = Math.floor((Date.now() - parsed) / 86_400_000);
  if (diffDays <= 0) return "Hoje";
  if (diffDays === 1) return "Há 1 dia";
  return `Há ${diffDays} dias`;
}

function formatDateTime(value: string | null): string {
  if (!value) return "Sem registro";
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return "Sem registro";
  return new Date(parsed).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDaysWithoutCheckin(value: number | null): string {
  if (typeof value !== "number") return "Sem check-in";
  if (value === 0) return "Hoje";
  if (value === 1) return "1 dia";
  return `${value} dias`;
}

function formatQueueRange(page: number, pageSize: number, total: number): string {
  if (total === 0) return "Mostrando 0 de 0";
  const start = (page - 1) * pageSize + 1;
  const end = Math.min(total, start + pageSize - 1);
  return `Mostrando ${start}-${end} de ${total}`;
}

function buildSignalRows(item: RetentionQueueItem): SignalRow[] {
  const reasons = item.reasons ?? {};
  const rows: SignalRow[] = [
    {
      label: "Dias sem check-in",
      value: formatDaysWithoutCheckin(item.days_without_checkin),
      tone: (item.days_without_checkin ?? 0) >= 14 ? "danger" : (item.days_without_checkin ?? 0) >= 7 ? "warning" : "neutral",
      progressPct: Math.min(100, Math.max(0, ((item.days_without_checkin ?? 0) / 30) * 100)),
    },
    {
      label: "Risk score",
      value: String(item.risk_score),
      tone: item.risk_score >= 70 ? "danger" : item.risk_score >= 40 ? "warning" : "neutral",
      progressPct: Math.min(100, Math.max(0, item.risk_score)),
    },
  ];

  if (typeof item.forecast_60d === "number") {
    rows.push({
      label: "Forecast 60d",
      value: `${item.forecast_60d}%`,
      tone: item.forecast_60d < 40 ? "danger" : item.forecast_60d < 60 ? "warning" : "neutral",
      progressPct: Math.min(100, Math.max(0, item.forecast_60d)),
    });
  }

  if (item.nps_last_score > 0) {
    rows.push({
      label: "Último NPS",
      value: String(item.nps_last_score),
      tone: item.nps_last_score <= 6 ? "danger" : item.nps_last_score === 7 ? "warning" : "neutral",
      progressPct: Math.min(100, Math.max(0, (item.nps_last_score / 10) * 100)),
    });
  }

  if (typeof reasons.frequency_drop_pct === "number") {
    rows.push({
      label: "Queda de frequência",
      value: `${Math.round(reasons.frequency_drop_pct)}%`,
      tone: reasons.frequency_drop_pct >= 50 ? "danger" : reasons.frequency_drop_pct >= 25 ? "warning" : "neutral",
      progressPct: Math.min(100, Math.max(0, reasons.frequency_drop_pct)),
    });
  }

  if (typeof reasons.shift_change_hours === "number" && reasons.shift_change_hours > 0) {
    rows.push({
      label: "Mudança de horário",
      value: `${Math.round(reasons.shift_change_hours)}h`,
      tone: reasons.shift_change_hours >= 4 ? "danger" : "warning",
      progressPct: Math.min(100, Math.max(0, (reasons.shift_change_hours / 8) * 100)),
    });
  }

  return rows;
}

function QueueSkeleton() {
  return (
    <div className="rounded-[24px] border border-lovable-border bg-lovable-surface/95 p-4 shadow-panel backdrop-blur-xl">
      <div className="mb-4 flex items-center justify-between gap-3">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-8 w-48 rounded-xl" />
      </div>
      <SkeletonList rows={8} cols={4} />
    </div>
  );
}

function SummarySkeleton() {
  return (
    <div className="space-y-4">
      <div className="rounded-[24px] border border-lovable-border bg-lovable-surface/95 p-5 shadow-panel backdrop-blur-xl">
        <Skeleton className="h-4 w-36" />
        <Skeleton className="mt-3 h-7 w-2/3" />
        <Skeleton className="mt-2 h-4 w-4/5" />
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-[22px] border border-lovable-border bg-lovable-surface/95 px-4 py-4 shadow-panel backdrop-blur-xl">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="mt-4 h-8 w-24" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={`highlight-${index}`} className="rounded-[22px] border border-lovable-border bg-lovable-surface/95 px-4 py-4 shadow-panel backdrop-blur-xl">
            <Skeleton className="h-3 w-24" />
            <Skeleton className="mt-3 h-8 w-16" />
            <Skeleton className="mt-2 h-4 w-28" />
          </div>
        ))}
      </div>
    </div>
  );
}

function RetentionQueueDrawer({
  item,
  onClose,
  onOpenProfile,
  onResolve,
  resolving,
  canResolve,
}: {
  item: RetentionQueueItem | null;
  onClose: () => void;
  onOpenProfile: (memberId: string) => void;
  onResolve: (alertId: string) => void;
  resolving: boolean;
  canResolve: boolean;
}) {
  const normalizedPhone = normalizeWhatsAppPhone(item?.phone);
  const phoneDisplay = formatPhoneDisplay(item?.phone);
  const whatsappHref = item ? buildWhatsAppHref(item.phone, item.assistant?.suggested_message, item.full_name) : null;
  const intelligenceContextQuery = useQuery({
    queryKey: ["members", "intelligence-context", item?.member_id],
    queryFn: async () => {
      if (!item?.member_id) {
        throw new Error("MEMBRO_INVALIDO");
      }
      return memberService.getIntelligenceContext(item.member_id);
    },
    enabled: Boolean(item?.member_id),
    staleTime: 60_000,
  });

  return (
    <Drawer
      open={Boolean(item)}
      onClose={onClose}
      side="right"
      widthClassName="sm:w-[30rem] sm:max-w-[92vw] lg:w-[38rem] xl:w-[44rem]"
      title={item ? `Playbook · ${item.full_name}` : "Playbook"}
    >
      {item ? (
        <div className="min-w-0 space-y-6 p-4">
          <section className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="text-sm font-semibold text-lovable-ink">{item.full_name}</p>
                <p className="mt-1 text-xs text-lovable-ink-muted">
                  {item.plan_name}
                  {item.email ? ` · ${item.email}` : ""}
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  <PreferredShiftBadge preferredShift={item.preferred_shift} prefix />
                  {normalizedPhone && phoneDisplay ? (
                    <a
                      href={`tel:${normalizedPhone}`}
                      className="inline-flex items-center gap-2 rounded-full border border-lovable-border bg-lovable-surface px-3 py-1.5 text-xs font-medium text-lovable-ink transition hover:border-lovable-primary/40 hover:text-lovable-primary"
                    >
                      <PhoneCall size={12} />
                      {phoneDisplay}
                    </a>
                  ) : (
                    <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-lovable-border px-3 py-1.5 text-xs text-lovable-ink-muted">
                      <PhoneCall size={12} />
                      Telefone nao informado
                    </span>
                  )}
                  {whatsappHref ? (
                    <a
                      href={whatsappHref}
                      target="_blank"
                      rel="noreferrer"
                      className="inline-flex items-center gap-2 rounded-full border border-lovable-primary/30 bg-lovable-primary/12 px-3 py-1.5 text-xs font-semibold text-lovable-primary transition hover:bg-lovable-primary/18"
                    >
                      <MessageCircle size={12} />
                      WhatsApp
                    </a>
                  ) : (
                    <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-lovable-border px-3 py-1.5 text-xs text-lovable-ink-muted">
                      <MessageCircle size={12} />
                      WhatsApp indisponivel
                    </span>
                  )}
                </div>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={retentionStageVariant(item.retention_stage)} size="sm" className="normal-case tracking-normal">
                  {formatRetentionStage(item)}
                </Badge>
                <RiskBadge risk={item.risk_level} />
                <Badge variant="info" size="sm" className="normal-case tracking-normal">
                  {formatChurnType(item.churn_type)}
                </Badge>
              </div>
            </div>
            <p className="mt-4 text-sm text-lovable-ink-muted">{item.signals_summary}</p>
            <div className="mt-4 grid gap-2 text-xs text-lovable-ink-muted sm:grid-cols-2">
              <div className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2">
                <span className="font-semibold text-lovable-ink">Último contato:</span> {formatDateTime(item.last_contact_at)}
              </div>
              <div className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2">
                <span className="font-semibold text-lovable-ink">Automação:</span> {item.automation_stage ?? "Sem estágio"}
              </div>
              <div className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2">
                <span className="font-semibold text-lovable-ink">Estagio:</span> {formatRetentionStage(item)}
              </div>
              <div className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2">
                <span className="font-semibold text-lovable-ink">Responsavel sugerido:</span> {formatOwnerRole(item.recommended_owner_role)}
              </div>
              {item.cooldown_until ? (
                <div className="rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 sm:col-span-2">
                  <span className="font-semibold text-lovable-ink">Cooldown:</span> volta para fila em {formatDateTime(item.cooldown_until)}
                </div>
              ) : null}
            </div>
          </section>

          <MemberIntelligenceMiniCard
            context={intelligenceContextQuery.data ?? null}
            isLoading={intelligenceContextQuery.isLoading}
            isError={intelligenceContextQuery.isError}
            onRetry={() => void intelligenceContextQuery.refetch()}
            title="Contexto canonico para retencao"
          />

          <AIAssistantPanel
            assistant={item.assistant}
            compact
            title="Copiloto de retenção"
            subtitle="Explicação curta, canal sugerido e abordagem inicial para este aluno."
          />

          <section>
            <SectionHeader
              title="Sinais captados"
              subtitle="Leitura rápida dos gatilhos ativos que colocaram o aluno na fila."
            />
            <div className="space-y-3">
              {buildSignalRows(item).map((signal) => (
                <article
                  key={signal.label}
                  className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-3"
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm text-lovable-ink">{signal.label}</span>
                    <span
                      className={cn(
                        "text-sm font-semibold",
                        signal.tone === "danger"
                          ? "text-lovable-danger"
                          : signal.tone === "warning"
                            ? "text-lovable-warning"
                            : "text-lovable-ink",
                      )}
                    >
                      {signal.value}
                    </span>
                  </div>
                  <div className="mt-2 h-2 overflow-hidden rounded-full bg-lovable-border">
                    <div
                      className={cn(
                        "h-full rounded-full transition-all",
                        signal.tone === "danger"
                          ? "bg-lovable-danger"
                          : signal.tone === "warning"
                            ? "bg-lovable-warning"
                            : "bg-lovable-primary",
                      )}
                      style={{ width: `${signal.progressPct}%` }}
                    />
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section>
            <SectionHeader
              title="Playbook sugerido"
              subtitle={
                item.retention_stage === "reactivation"
                  ? "Aluno 30+ dias: oferecer retorno guiado com professor, nao lembrete simples."
                  : item.retention_stage === "manager_escalation"
                    ? "Aluno 45+ dias: gerente revisa permanencia, plano, trancamento ou cancelamento."
                    : item.retention_stage === "cold_base"
                      ? "Aluno 60+ dias: tratar como campanha de winback, fora da fila diaria comum."
                      : item.next_action
                        ? `Próxima ação recomendada: ${item.next_action}`
                        : "Sem playbook configurado."
              }
              count={item.playbook_steps.length}
            />
            {item.playbook_steps.length === 0 ? (
              <div className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface-soft p-4 text-sm text-lovable-ink-muted">
                Nenhum playbook sugerido para este alerta.
              </div>
            ) : (
              <div className="space-y-3">
                {item.playbook_steps.map((step, index) => (
                  <article key={`${step.title}-${index}`} className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-lovable-ink">{step.title}</p>
                        <p className="mt-1 text-sm text-lovable-ink-muted">{step.message}</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          variant={PLAYBOOK_PRIORITY_VARIANT[step.priority] ?? "neutral"}
                          size="sm"
                          className="normal-case tracking-normal"
                        >
                          {step.priority}
                        </Badge>
                        <Badge variant="neutral" size="sm" className="normal-case tracking-normal">
                          {step.owner}
                        </Badge>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-lovable-ink-muted">
                      <span>D+{step.due_days}</span>
                      <span className="inline-flex items-center gap-1">
                        <Bot size={12} />
                        {step.action}
                      </span>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section>
            <SectionHeader
              title="Ações rápidas"
              subtitle="Acione o playbook sem sair da fila."
            />
            <div className="flex flex-wrap gap-2">
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  if (!whatsappHref) return;
                  window.open(whatsappHref, "_blank", "noopener,noreferrer");
                }}
                disabled={!whatsappHref}
              >
                <MessageCircle size={14} />
                WhatsApp
              </Button>
              <Button size="sm" variant="secondary" onClick={() => onOpenProfile(item.member_id)}>
                <ArrowUpRight size={14} />
                Abrir perfil 360
              </Button>
              {canResolve ? (
                <Button size="sm" variant="ghost" onClick={() => onResolve(item.alert_id)} disabled={resolving}>
                  <CheckCheck size={14} />
                  {resolving ? "Resolvendo..." : "Marcar resolvido"}
                </Button>
              ) : null}
            </div>
            <div className="mt-4">
              <QuickActions
                member={{
                  id: item.member_id,
                  full_name: item.full_name,
                  phone: item.phone,
                  risk_level: item.risk_level,
                  risk_score: item.risk_score,
                }}
              />
            </div>
          </section>
        </div>
      ) : null}
    </Drawer>
  );
}

export function RetentionDashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const summaryQuery = useRetentionDashboard();
  const searchParamValue = searchParams.get("search") ?? "";

  const [searchInput, setSearchInput] = useState(searchParamValue);
  const [search, setSearch] = useState(searchParamValue.trim());
  const [level, setLevel] = useState<QueueLevel>("all");
  const [churnType, setChurnType] = useState("all");
  const [planCycle, setPlanCycle] = useState("all");
  const [preferredShift, setPreferredShift] = useState<QueuePreferredShift>("all");
  const [retentionStage, setRetentionStage] = useState<QueueRetentionStage>("all");
  const [useCurrentShift, setUseCurrentShift] = useState(false);
  const [shiftPreferenceTouched, setShiftPreferenceTouched] = useState(false);
  const [page, setPage] = useState(1);
  const [selectedItem, setSelectedItem] = useState<RetentionQueueItem | null>(null);
  const currentUserShift = getPreferredShiftKey(user?.work_shift);
  const currentShiftLabel = getPreferredShiftLabel(currentUserShift);
  const effectivePreferredShift =
    useCurrentShift && currentUserShift ? currentUserShift : preferredShift === "all" ? undefined : preferredShift;

  useEffect(() => {
    if (shiftPreferenceTouched) return;
    setUseCurrentShift(Boolean(currentUserShift));
    setPreferredShift("all");
  }, [currentUserShift, shiftPreferenceTouched]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setSearch(searchInput.trim());
    }, 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  useEffect(() => {
    if (searchParamValue === searchInput) return;
    setSearchInput(searchParamValue);
  }, [searchInput, searchParamValue]);

  useEffect(() => {
    setPage(1);
  }, [search, level, churnType, planCycle, effectivePreferredShift, retentionStage]);

  const queueQuery = useQuery({
    queryKey: ["dashboard", "retention", "queue", { page, search, level, churnType, planCycle, effectivePreferredShift, retentionStage }],
    queryFn: () =>
      dashboardService.retentionQueue({
        page,
        page_size: 50,
        search: search || undefined,
        level,
        churn_type: churnType === "all" ? undefined : churnType,
        plan_cycle: planCycle === "all" ? undefined : (planCycle as "monthly" | "semiannual" | "annual"),
        preferred_shift: effectivePreferredShift,
        retention_stage: retentionStage === "all" ? undefined : retentionStage,
      }),
    staleTime: 60_000,
    placeholderData: (previous, previousQuery) => {
      const previousParams = previousQuery?.queryKey?.[3] as
        | { page?: number; search?: string; level?: string; churnType?: string; planCycle?: string; effectivePreferredShift?: string; retentionStage?: string }
        | undefined;
      if (!previousParams) return previous;
      const filtersChanged =
        previousParams.search !== search ||
        previousParams.level !== level ||
        previousParams.churnType !== churnType ||
        previousParams.planCycle !== planCycle ||
        previousParams.effectivePreferredShift !== effectivePreferredShift ||
        previousParams.retentionStage !== retentionStage;
      return filtersChanged ? undefined : previous;
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (alertId: string) => riskAlertService.resolve(alertId, "Resolvido no dashboard de retenção"),
    onSuccess: (_, alertId) => {
      if (selectedItem?.alert_id === alertId) {
        setSelectedItem(null);
      }
      void queryClient.invalidateQueries({ queryKey: ["dashboard", "retention", "queue"] });
      toast.success("Alerta marcado como resolvido.");
    },
    onError: () => toast.error("Falha ao resolver alerta."),
  });

  const activeFilterCount = [
    searchInput.trim().length > 0,
    level !== "all",
    churnType !== "all",
    planCycle !== "all",
    preferredShift !== "all",
    retentionStage !== "all",
  ].filter(Boolean).length;
  const canResolveAlerts = canResolveRetentionAlert(user?.role);

  const kpis = useMemo(() => {
    const data = summaryQuery.data;
    if (!data) return [];
    const totalAlerts = Number(data.red.total ?? 0) + Number(data.yellow.total ?? 0);
    const hasFinancialBase = Number(data.mrr_at_risk ?? 0) > 0;
    return [
      { label: "Alertas vermelhos", value: data.red.total, tone: "danger" as const },
      { label: "Alertas amarelos", value: data.yellow.total, tone: "warning" as const },
      {
        label: "MRR em risco",
        value: hasFinancialBase ? formatCurrency(Number(data.mrr_at_risk ?? 0)) : totalAlerts > 0 ? "Sem base" : formatCurrency(0),
        tone: hasFinancialBase ? ("warning" as const) : ("neutral" as const),
      },
      {
        label: "Score médio crítico",
        value: data.red.total > 0 ? `${Math.round(Number(data.avg_red_score ?? 0))}` : "—",
        tone: "danger" as const,
      },
    ];
  }, [summaryQuery.data]);

  const retentionDataNotes = useMemo(() => {
    const data = summaryQuery.data;
    if (!data) return [] as string[];

    const notes: string[] = [];
    const totalAlerts = Number(data.red.total ?? 0) + Number(data.yellow.total ?? 0);

    if ((data.nps_trend?.length ?? 0) === 0) {
      notes.push("NPS ainda sem respostas suficientes para formar a curva histórica deste painel.");
    }
    if (totalAlerts > 0 && Number(data.mrr_at_risk ?? 0) <= 0) {
      notes.push("MRR em risco ainda sem base financeira útil porque as mensalidades dessa base não estão consolidadas.");
    }

    return notes;
  }, [summaryQuery.data]);

  const churnHighlights = useMemo(() => {
    const distribution = summaryQuery.data?.churn_distribution ?? {};
    const total = Object.values(distribution).reduce((sum, count) => sum + count, 0);
    if (total === 0) return [] as ChurnHighlight[];

    return Object.entries(distribution)
      .filter(([, count]) => count > 0)
      .sort(([, left], [, right]) => right - left)
      .slice(0, 4)
      .map(([key, count]) => ({
        key,
        label: CHURN_META[key]?.label ?? formatChurnType(key),
        description: CHURN_META[key]?.description ?? "Sem classificação dominante.",
        count,
        pct: Math.round((count / total) * 100),
      }));
  }, [summaryQuery.data]);

  const queueItems = queueQuery.data?.items ?? [];
  const queueTotal = queueQuery.data?.total ?? 0;
  const queuePage = queueQuery.data?.page ?? page;
  const queuePageSize = queueQuery.data?.page_size ?? 50;
  const stageCounts = queueQuery.data?.stage_counts ?? {};
  const laneOptions = RETENTION_STAGE_OPTIONS.filter((option) =>
    ["attention", "recovery", "reactivation", "manager_escalation", "cold_base"].includes(option.value),
  );

  const handleOpenProfile = (memberId: string) => {
    setSelectedItem(null);
    navigate(`/assessments/members/${memberId}`);
  };

  const handleSearchChange = (value: string) => {
    setSearchInput(value);
    const trimmedValue = value.trim();
    const nextParams = new URLSearchParams(searchParams);
    if (trimmedValue) {
      nextParams.set("search", trimmedValue);
    } else {
      nextParams.delete("search");
    }
    setSearchParams(nextParams, { replace: true });
  };

  const handleClearFilters = () => {
    handleSearchChange("");
    setLevel("all");
    setChurnType("all");
    setPlanCycle("all");
    setRetentionStage("all");
    setPreferredShift("all");
    setShiftPreferenceTouched(false);
    setUseCurrentShift(Boolean(currentUserShift));
    setPage(1);
  };

  if (summaryQuery.isError) {
    return (
      <section className="space-y-6">
        <PageHeader
          title="Retenção"
          subtitle="Fila operacional de alunos com aviso ativo e playbooks sugeridos."
          actions={<DashboardActions dashboard="retention" theme="dark" />}
        />
        <EmptyState
          icon={AlertTriangle}
          title="Não foi possível carregar a visão de retenção"
          description={getPermissionAwareMessage(summaryQuery.error, "Tente novamente para recuperar as metricas e a fila operacional.")}
          action={{ label: "Tentar novamente", onClick: () => void summaryQuery.refetch() }}
        />
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <PageHeader
        title="Retenção"
        subtitle="Fila operacional de alunos com aviso ativo e playbooks sugeridos."
        actions={<DashboardActions dashboard="retention" theme="dark" />}
        breadcrumb={[{ label: "Dashboards", href: "/dashboard/executive" }, { label: "Retenção" }]}
      />

      {summaryQuery.isLoading ? (
        <SummarySkeleton />
      ) : (
        <div className="space-y-4">
          <AiInsightCard dashboard="retention" />
          <KPIStrip items={kpis} />
          {retentionDataNotes.length > 0 ? (
            <div className="rounded-[22px] border border-dashed border-lovable-border bg-lovable-surface/92 px-4 py-4 text-sm text-lovable-ink-muted shadow-panel backdrop-blur-xl">
              <p className="font-medium text-lovable-ink">Leitura do painel</p>
              <ul className="mt-2 space-y-1">
                {retentionDataNotes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </div>
          ) : null}
          {churnHighlights.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {churnHighlights.map((item) => (
                <article
                  key={item.key}
                  className="rounded-[22px] border border-lovable-border bg-lovable-surface/95 px-4 py-4 shadow-panel backdrop-blur-xl"
                >
                  <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">
                    {item.label}
                  </p>
                  <div className="mt-3 flex items-end justify-between gap-3">
                    <p className="text-3xl font-bold text-lovable-ink">{item.pct}%</p>
                    <p className="text-sm font-semibold text-lovable-ink-muted">{item.count} alunos</p>
                  </div>
                  <p className="mt-2 text-sm text-lovable-ink-muted">{item.description}</p>
                </article>
              ))}
            </div>
          ) : null}
        </div>
      )}

      <section className="rounded-[24px] border border-lovable-border bg-lovable-surface/95 p-4 shadow-panel backdrop-blur-xl">
        <SectionHeader
          title="Fila operacional"
          subtitle="Todos os avisos ativos ficam acessíveis por busca e paginação, sem truncamento escondido."
          count={queueTotal}
          actions={
            queueQuery.isFetching ? (
              <span className="inline-flex items-center gap-2 text-xs text-lovable-ink-muted">
                <RefreshCw size={12} className="animate-spin" />
                Atualizando fila...
              </span>
            ) : undefined
          }
        />

        <FilterBar
          search={{
            value: searchInput,
            onChange: handleSearchChange,
            placeholder: "Buscar por nome, e-mail ou plano do aluno...",
          }}
          filters={[
            {
              key: "level",
              label: "Severidade",
              value: level,
              onChange: (value) => setLevel(value as QueueLevel),
              options: [
                { value: "all", label: "Todos os níveis" },
                { value: "red", label: "Somente vermelho" },
                { value: "yellow", label: "Somente amarelo" },
              ],
            },
            {
              key: "retention_stage",
              label: "Estagio",
              value: retentionStage,
              onChange: (value) => setRetentionStage((value || "all") as QueueRetentionStage),
              options: RETENTION_STAGE_OPTIONS.map((option) => ({ value: option.value, label: option.label })),
            },
            {
              key: "churn_type",
              label: "Churn",
              value: churnType,
              onChange: setChurnType,
              options: CHURN_OPTIONS.map((option) => ({ value: option.value, label: option.label })),
            },
            {
              key: "plan_cycle",
              label: "Plano",
              value: planCycle,
              onChange: setPlanCycle,
              options: PLAN_CYCLE_OPTIONS.map((option) => ({ value: option.value, label: option.label })),
            },
            {
              key: "preferred_shift",
              label: "Turno",
              value: useCurrentShift && currentUserShift ? currentUserShift : preferredShift,
              onChange: (value) => {
                setShiftPreferenceTouched(true);
                setUseCurrentShift(false);
                setPreferredShift((value || "all") as QueuePreferredShift);
              },
              options: PREFERRED_SHIFT_OPTIONS.map((option) => ({ value: option.value, label: option.label })),
            },
          ]}
          activeCount={activeFilterCount}
          onClear={handleClearFilters}
        />
        {currentUserShift && currentShiftLabel ? (
          <div className="mt-3 flex flex-wrap items-center gap-2 px-1">
            <Button
              size="sm"
              variant={useCurrentShift ? "primary" : "secondary"}
              onClick={() => {
                setShiftPreferenceTouched(true);
                setUseCurrentShift((value) => !value);
                setPreferredShift("all");
              }}
            >
              {useCurrentShift ? `Meu turno: ${currentShiftLabel}` : "Todos os turnos"}
            </Button>
            <span className="text-xs text-lovable-ink-muted">
              A fila usa o turno preferido do aluno calculado pelos check-ins.
            </span>
          </div>
        ) : null}

        <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-5">
          {laneOptions.map((option) => {
            const isActive = retentionStage === option.value;
            const count = stageCounts[option.value] ?? 0;
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => setRetentionStage(isActive ? "all" : option.value)}
                className={cn(
                  "rounded-2xl border px-4 py-3 text-left transition",
                  isActive
                    ? "border-lovable-primary/60 bg-lovable-primary/12 text-lovable-ink shadow-panel"
                    : "border-lovable-border bg-lovable-surface-soft text-lovable-ink hover:border-lovable-primary/35",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold">{option.label}</p>
                    <p className="mt-1 text-xs text-lovable-ink-muted">{option.description}</p>
                  </div>
                  <Badge variant={retentionStageVariant(option.value)} size="sm">
                    {count}
                  </Badge>
                </div>
              </button>
            );
          })}
        </div>

        <div className="mt-4">
          {queueQuery.isLoading ? (
            <QueueSkeleton />
          ) : queueQuery.isError ? (
            <div className="rounded-[24px] border border-lovable-border bg-lovable-surface-soft p-6">
              <EmptyState
                icon={AlertTriangle}
                title="Não foi possível carregar a fila"
                description="Tente novamente para recuperar a lista completa de alunos com alerta."
                action={{ label: "Tentar novamente", onClick: () => void queueQuery.refetch() }}
              />
            </div>
          ) : queueItems.length === 0 ? (
            <div className="rounded-[24px] border border-lovable-border bg-lovable-surface-soft p-6">
              <EmptyState
                icon={UserSearch}
                title="Nenhum alerta encontrado"
                description="Ajuste a busca ou os filtros para voltar a enxergar a fila operacional."
                action={activeFilterCount > 0 ? { label: "Limpar filtros", onClick: handleClearFilters } : undefined}
              />
            </div>
          ) : (
            <div className="overflow-hidden rounded-[24px] border border-lovable-border bg-lovable-surface-soft">
              <div
                className={cn(
                  "hidden gap-4 border-b border-lovable-border px-4 py-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted lg:grid",
                  QUEUE_GRID_COLUMNS,
                )}
              >
                <span>Aluno</span>
                <span>Estagio</span>
                <span>Severidade</span>
                <span>Churn</span>
                <span>Inatividade</span>
                <span>Último contato</span>
                <span>Score / Forecast</span>
                <span className="text-right">Ações</span>
              </div>

              <div className="divide-y divide-lovable-border">
                {queueItems.map((item) => (
                  <div
                    key={item.alert_id}
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedItem(item)}
                    onKeyDown={(event) => {
                      if (event.key === "Enter" || event.key === " ") {
                        event.preventDefault();
                        setSelectedItem(item);
                      }
                    }}
                    className={cn(
                      "grid w-full gap-4 px-4 py-4 text-left transition hover:bg-lovable-surface lg:items-center",
                      QUEUE_GRID_COLUMNS,
                    )}
                  >
                    <div className="min-w-0">
                      <div className="flex items-start gap-3">
                        <div className="mt-1 rounded-full bg-lovable-primary/12 p-2 text-lovable-primary">
                          <ShieldAlert size={14} />
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-semibold text-lovable-ink">{item.full_name}</p>
                          <p className="mt-1 truncate text-xs text-lovable-ink-muted">
                            {item.plan_name}
                            {item.email ? ` · ${item.email}` : ""}
                          </p>
                          <div className="mt-2">
                            <PreferredShiftBadge preferredShift={item.preferred_shift} prefix />
                          </div>
                          <p className="mt-1 text-xs text-lovable-ink-muted">{item.signals_summary}</p>
                        </div>
                      </div>
                    </div>

                    <div className="flex min-w-0 flex-col items-start gap-1">
                      <Badge variant={retentionStageVariant(item.retention_stage)} size="sm" className="normal-case tracking-normal">
                        {formatRetentionStage(item)}
                      </Badge>
                      <span className="text-xs text-lovable-ink-muted">
                        {formatOwnerRole(item.recommended_owner_role)}
                      </span>
                    </div>

                    <div className="flex min-w-0 items-center lg:items-start">
                      <RiskBadge risk={item.risk_level} />
                    </div>

                    <div className="flex min-w-0 items-center lg:items-start">
                      <Badge variant="info" size="sm" className="normal-case tracking-normal">
                        {formatChurnType(item.churn_type)}
                      </Badge>
                    </div>

                    <div className="flex min-w-0 items-center gap-2 text-sm text-lovable-ink">
                      <Clock3 size={14} className="text-lovable-ink-muted" />
                      {formatDaysWithoutCheckin(item.days_without_checkin)}
                    </div>

                    <div className="flex min-w-0 items-center gap-2 text-sm text-lovable-ink">
                      <PhoneCall size={14} className="text-lovable-ink-muted" />
                      {formatLastContact(item.last_contact_at)}
                    </div>

                    <div className="flex min-w-0 items-center gap-2">
                      <div>
                        <p className="text-sm font-semibold text-lovable-ink">{item.risk_score}</p>
                        <p className="text-xs text-lovable-ink-muted">
                          {typeof item.forecast_60d === "number" ? `${item.forecast_60d}% forecast` : "Sem forecast"}
                        </p>
                      </div>
                    </div>

                    <div
                      className="flex min-w-0 flex-wrap items-center justify-start gap-2 lg:justify-end"
                      onClick={(event) => event.stopPropagation()}
                    >
                      <Button size="sm" variant="ghost" onClick={() => handleOpenProfile(item.member_id)}>
                        <ArrowUpRight size={14} />
                        Abrir perfil
                      </Button>
                      <Button size="sm" variant="secondary" onClick={() => setSelectedItem(item)}>
                        <CalendarClock size={14} />
                        Ver playbook
                      </Button>
                      {canResolveAlerts ? (
                        <Button
                          size="sm"
                          variant="ghost"
                          disabled={resolveMutation.isPending && resolveMutation.variables === item.alert_id}
                          onClick={() => resolveMutation.mutate(item.alert_id)}
                        >
                          <CheckCheck size={14} />
                          Resolver
                        </Button>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex flex-col gap-3 border-t border-lovable-border px-4 py-4 md:flex-row md:items-center md:justify-between">
                <div className="text-sm text-lovable-ink-muted">{formatQueueRange(queuePage, queuePageSize, queueTotal)}</div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-lovable-ink-muted">
                    Página {queuePage} de {Math.max(1, Math.ceil(queueTotal / queuePageSize))}
                  </span>
                  <Pagination
                    page={queuePage}
                    pageSize={queuePageSize}
                    total={queueTotal}
                    onPageChange={setPage}
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </section>

      <RetentionQueueDrawer
        item={selectedItem}
        onClose={() => setSelectedItem(null)}
        onOpenProfile={handleOpenProfile}
        onResolve={(alertId) => resolveMutation.mutate(alertId)}
        resolving={resolveMutation.isPending && resolveMutation.variables === selectedItem?.alert_id}
        canResolve={canResolveAlerts}
      />
    </section>
  );
}
