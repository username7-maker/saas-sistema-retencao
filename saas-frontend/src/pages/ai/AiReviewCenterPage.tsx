import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, Bot, CheckCircle2, ShieldAlert, Sparkles, Video, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { useNavigate } from "react-router-dom";

import { PageHeader, SkeletonList } from "../../components/ui";
import { Badge, Button, Input, Select, cn } from "../../components/ui2";
import { aiReviewCenterService } from "../../services/aiReviewCenterService";
import type { AiReviewCenterItem } from "../../types";

const sourceOptions = [
  { value: "all", label: "Todas as origens" },
  { value: "ai_service_agent", label: "Atendimento" },
  { value: "personal_ai", label: "Personal IA" },
  { value: "student_personal_ai", label: "Aluno Kommo" },
  { value: "movement_video", label: "Video aprovado" },
  { value: "movement_video_review", label: "Review de video" },
];

const statusOptions = [
  { value: "all", label: "Todos os status" },
  { value: "draft_ready", label: "Rascunho pronto" },
  { value: "blocked", label: "Bloqueado" },
  { value: "escalated", label: "Escalado" },
  { value: "awaiting_outcome", label: "Aguardando" },
  { value: "pending_review", label: "Video pendente" },
  { value: "needs_coach_review", label: "Revisao coach" },
  { value: "approved", label: "Aprovado" },
  { value: "cancelled", label: "Rejeitado" },
];

function sourceLabel(source: string): string {
  return sourceOptions.find((item) => item.value === source)?.label ?? source;
}

function statusVariant(status: string): "neutral" | "success" | "warning" | "danger" | "info" {
  if (status === "blocked" || status === "escalated" || status === "failed") return "danger";
  if (status === "draft_ready" || status === "approved") return "success";
  if (status === "awaiting_outcome") return "info";
  if (status === "pending_review" || status === "needs_coach_review") return "warning";
  return "neutral";
}

function sourceIcon(source: string) {
  if (source.includes("video")) return Video;
  if (source === "personal_ai" || source === "student_personal_ai") return Sparkles;
  return Bot;
}

function formatDate(value: string): string {
  try {
    return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
  } catch {
    return value;
  }
}

function humanizeStatus(value: string): string {
  return value.replace(/_/g, " ");
}

export default function AiReviewCenterPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [source, setSource] = useState("all");
  const [status, setStatus] = useState("all");
  const [q, setQ] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const reviewQuery = useQuery({
    queryKey: ["ai-review-center", { source, status, q }],
    queryFn: () =>
      aiReviewCenterService.listItems({
        source: source === "all" ? undefined : source,
        status: status === "all" ? undefined : status,
        q: q.trim() || undefined,
        limit: 120,
      }),
    staleTime: 30_000,
  });

  const items = reviewQuery.data?.items ?? [];
  const selectedItem = useMemo(() => items.find((item) => item.source_id === selectedId) ?? items[0] ?? null, [items, selectedId]);

  useEffect(() => {
    if (!selectedId && items[0]) {
      setSelectedId(items[0].source_id);
    }
    if (selectedId && items.length > 0 && !items.some((item) => item.source_id === selectedId)) {
      setSelectedId(items[0].source_id);
    }
  }, [items, selectedId]);

  const prepareMutation = useMutation({
    mutationFn: (item: AiReviewCenterItem) => aiReviewCenterService.prepareKommo(item.source_type, item.source_id),
    onSuccess: (result) => {
      toast.success(result.detail || "Item preparado na Kommo.");
      void queryClient.invalidateQueries({ queryKey: ["ai-review-center"] });
    },
    onError: () => toast.error("Nao foi possivel preparar na Kommo."),
  });

  const feedbackMutation = useMutation({
    mutationFn: ({
      item,
      decision,
      reason,
      editedReply,
    }: {
      item: AiReviewCenterItem;
      decision: "approved" | "edited" | "rejected" | "escalated";
      reason?: string;
      editedReply?: string;
    }) =>
      aiReviewCenterService.recordFeedback(item.source_type, item.source_id, {
        decision,
        reason,
        edited_reply: editedReply,
      }),
    onSuccess: () => {
      toast.success("Feedback registrado.");
      void queryClient.invalidateQueries({ queryKey: ["ai-review-center"] });
    },
    onError: () => toast.error("Nao foi possivel registrar o feedback."),
  });

  function rejectItem(item: AiReviewCenterItem) {
    const reason = window.prompt("Motivo da rejeicao", "Rascunho nao aprovado pela equipe.");
    if (!reason?.trim()) return;
    feedbackMutation.mutate({ item, decision: "rejected", reason: reason.trim() });
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Central de Revisao IA"
        subtitle="Rascunhos e reviews gerados pela IA para revisao humana antes de qualquer envio."
      />

      <section className="grid gap-3 md:grid-cols-4 xl:grid-cols-8">
        <MetricCard label="Total" value={reviewQuery.data?.metrics.total ?? 0} />
        <MetricCard label="Prontos" value={reviewQuery.data?.metrics.ready ?? 0} tone="success" />
        <MetricCard label="Bloqueados" value={reviewQuery.data?.metrics.blocked ?? 0} tone="danger" />
        <MetricCard label="Escalados" value={reviewQuery.data?.metrics.escalated ?? 0} tone="warning" />
        <MetricCard label="Aguardando" value={reviewQuery.data?.metrics.awaiting_outcome ?? 0} tone="info" />
        <MetricCard label="Revisados" value={reviewQuery.data?.metrics.reviewed ?? 0} tone="info" />
        <MetricCard label="Editados" value={reviewQuery.data?.metrics.edited ?? 0} tone="warning" />
        <MetricCard label="Uso" value={Math.round((reviewQuery.data?.metrics.utilization_rate ?? 0) * 100)} suffix="%" tone="success" />
      </section>

      <section className="rounded-[28px] border border-lovable-border bg-lovable-surface/82 p-5 shadow-panel">
        <div className="grid gap-3 lg:grid-cols-[220px_220px_1fr]">
          <Select value={source} onChange={(event) => setSource(event.target.value)}>
            {sourceOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Select value={status} onChange={(event) => setStatus(event.target.value)}>
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
          <Input value={q} onChange={(event) => setQ(event.target.value)} placeholder="Buscar aluno, lead, intencao ou resumo..." />
        </div>
      </section>

      {reviewQuery.isLoading ? (
        <SkeletonList rows={5} />
      ) : reviewQuery.isError ? (
        <div className="rounded-[28px] border border-lovable-danger/40 bg-lovable-danger/10 p-8 text-center text-sm text-lovable-danger">
          Erro ao carregar a central de revisao IA.
        </div>
      ) : items.length === 0 ? (
        <div className="rounded-[28px] border border-lovable-border bg-lovable-surface/78 p-12 text-center">
          <CheckCircle2 className="mx-auto h-10 w-10 text-lovable-success" />
          <h2 className="mt-4 text-lg font-semibold text-lovable-ink">Nenhum rascunho aguardando revisao</h2>
          <p className="mt-2 text-sm text-lovable-ink-muted">Quando Atendimento IA, Personal IA ou Video gerarem itens, eles aparecem aqui.</p>
        </div>
      ) : (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,0.92fr)_minmax(420px,0.72fr)]">
          <div className="space-y-3">
            {items.map((item) => {
              const Icon = sourceIcon(item.source_type);
              const active = selectedItem?.source_id === item.source_id;
              return (
                <button
                  type="button"
                  key={`${item.source_type}-${item.source_id}`}
                  onClick={() => setSelectedId(item.source_id)}
                  className={cn(
                    "w-full rounded-[24px] border p-4 text-left transition",
                    active
                      ? "border-lovable-primary/70 bg-lovable-primary/12 shadow-[0_18px_44px_-28px_hsl(var(--lovable-primary)/0.85)]"
                      : "border-lovable-border bg-lovable-surface/78 hover:border-lovable-border-strong hover:bg-lovable-surface",
                  )}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="flex items-start gap-3">
                      <span className="mt-0.5 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-2 text-lovable-ink-muted">
                        <Icon size={16} />
                      </span>
                      <div>
                        <p className="font-semibold text-lovable-ink">{item.subject_name}</p>
                        <p className="mt-1 text-xs text-lovable-ink-muted">{sourceLabel(item.source_type)} · {formatDate(item.created_at)}</p>
                      </div>
                    </div>
                    <Badge variant={statusVariant(item.status)} size="sm">
                      {humanizeStatus(item.status)}
                    </Badge>
                  </div>
                  <p className="mt-3 line-clamp-2 text-sm text-lovable-ink">{item.summary ?? item.next_action ?? "Sem resumo."}</p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {(item.badges ?? []).slice(0, 4).map((badge) => (
                      <Badge key={badge} variant="neutral" size="sm">
                        {badge}
                      </Badge>
                    ))}
                  </div>
                </button>
              );
            })}
          </div>

          <ReviewInspector
            item={selectedItem}
            onPrepare={(item) => prepareMutation.mutate(item)}
            onFeedback={(item, decision, reason, editedReply) => feedbackMutation.mutate({ item, decision, reason, editedReply })}
            onReject={rejectItem}
            onOpenContext={(path) => navigate(path)}
            isPreparing={prepareMutation.isPending}
            isFeedbacking={feedbackMutation.isPending}
          />
        </div>
      )}
    </div>
  );
}

function MetricCard({
  label,
  value,
  suffix = "",
  tone = "neutral",
}: {
  label: string;
  value: number;
  suffix?: string;
  tone?: "neutral" | "success" | "danger" | "warning" | "info";
}) {
  return (
    <div className="rounded-[24px] border border-lovable-border bg-lovable-surface/82 p-4 shadow-panel">
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">{label}</p>
      <p className={cn("mt-3 text-3xl font-black text-lovable-ink", tone === "success" && "text-lovable-success", tone === "danger" && "text-lovable-danger", tone === "warning" && "text-lovable-warning", tone === "info" && "text-blue-400")}>
        {value}{suffix}
      </p>
    </div>
  );
}

function ReviewInspector({
  item,
  onPrepare,
  onFeedback,
  onReject,
  onOpenContext,
  isPreparing,
  isFeedbacking,
}: {
  item: AiReviewCenterItem | null;
  onPrepare: (item: AiReviewCenterItem) => void;
  onFeedback: (
    item: AiReviewCenterItem,
    decision: "approved" | "edited" | "rejected" | "escalated",
    reason?: string,
    editedReply?: string,
  ) => void;
  onReject: (item: AiReviewCenterItem) => void;
  onOpenContext: (path: string) => void;
  isPreparing: boolean;
  isFeedbacking: boolean;
}) {
  const [editedReply, setEditedReply] = useState("");
  const [reviewReason, setReviewReason] = useState("");

  useEffect(() => {
    setEditedReply(item?.draft_reply ?? "");
    setReviewReason(item?.review_notes ?? "");
  }, [item?.source_id, item?.draft_reply, item?.review_notes]);

  if (!item) return null;
  const blocked = item.blocked_reasons.length > 0 || item.status === "blocked" || item.status === "escalated";
  const hasEditedReply = editedReply.trim().length > 0 && editedReply.trim() !== (item.draft_reply ?? "").trim();

  return (
    <aside className="rounded-[28px] border border-lovable-border bg-lovable-surface/88 p-5 shadow-panel xl:sticky xl:top-24 xl:self-start">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.28em] text-lovable-ink-muted">{sourceLabel(item.source_type)}</p>
          <h2 className="mt-2 text-2xl font-black text-lovable-ink">{item.subject_name}</h2>
          <p className="mt-1 text-sm text-lovable-ink-muted">{item.intent ?? item.domain} · {formatDate(item.created_at)}</p>
        </div>
        <Badge variant={statusVariant(item.status)}>{humanizeStatus(item.status)}</Badge>
      </div>

      {blocked ? (
        <div className="mt-5 rounded-2xl border border-lovable-danger/40 bg-lovable-danger/10 p-4">
          <div className="flex items-center gap-2 text-sm font-semibold text-lovable-danger">
            <ShieldAlert size={16} />
            Revisao com bloqueio ou escalonamento
          </div>
          <p className="mt-2 text-sm text-lovable-ink-muted">
            Este item nao deve ser enviado sem decisao humana. Motivos: {item.blocked_reasons.join(", ") || "estado sensivel"}.
          </p>
        </div>
      ) : null}

      <InfoBlock title="Resumo" body={item.summary ?? "Sem resumo."} />
      {item.received_message ? <InfoBlock title="Mensagem recebida" body={item.received_message} /> : null}
      {item.draft_reply ? <InfoBlock title="Rascunho sugerido" body={item.draft_reply} highlighted /> : null}
      <InfoBlock title="Proxima acao" body={item.next_action ?? "Revisar e decidir proximo passo."} />

      <div className="mt-5 rounded-2xl border border-lovable-border bg-lovable-bg-muted/45 p-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">Feedback do revisor</p>
          {item.review_decision ? (
            <Badge variant={item.review_decision === "rejected" || item.review_decision === "escalated" ? "danger" : "success"} size="sm">
              {humanizeStatus(item.review_decision)}
            </Badge>
          ) : (
            <Badge variant="neutral" size="sm">Nao revisado</Badge>
          )}
        </div>
        {item.reviewed_at ? (
          <p className="mt-2 text-xs text-lovable-ink-muted">
            Revisado em {formatDate(item.reviewed_at)}
            {item.review_latency_minutes !== null ? ` - ${item.review_latency_minutes} min ate revisao` : ""}
          </p>
        ) : null}
        <textarea
          value={editedReply}
          onChange={(event) => setEditedReply(event.target.value)}
          rows={5}
          className="mt-3 w-full rounded-2xl border border-lovable-border bg-lovable-bg px-3 py-2 text-sm text-lovable-ink outline-none transition focus:border-lovable-primary"
          placeholder="Ajuste o rascunho antes de preparar na Kommo..."
        />
        <Input
          value={reviewReason}
          onChange={(event) => setReviewReason(event.target.value)}
          className="mt-3"
          placeholder="Nota curta, motivo de escalonamento ou rejeicao..."
        />
        <div className="mt-3 flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="secondary"
            disabled={isFeedbacking}
            onClick={() => onFeedback(item, "approved", reviewReason.trim() || "Aprovado pela equipe.")}
          >
            Aprovar
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={!hasEditedReply || isFeedbacking}
            onClick={() => onFeedback(item, "edited", reviewReason.trim() || "Rascunho editado pela equipe.", editedReply.trim())}
          >
            Salvar edicao
          </Button>
          <Button
            size="sm"
            variant="secondary"
            disabled={reviewReason.trim().length < 3 || isFeedbacking}
            onClick={() => onFeedback(item, "escalated", reviewReason.trim())}
          >
            Escalar
          </Button>
        </div>
      </div>

      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/45 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Responsavel</p>
          <p className="mt-2 text-sm font-semibold text-lovable-ink">{item.recommended_owner_role ?? "equipe"}</p>
        </div>
        <div className="rounded-2xl border border-lovable-border bg-lovable-bg-muted/45 p-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Kommo</p>
          <p className="mt-2 text-sm font-semibold text-lovable-ink">{item.kommo_task_id ? "Preparado" : "Nao preparado"}</p>
        </div>
      </div>

      {item.evidence.length > 0 ? (
        <div className="mt-5">
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">Evidencias</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {item.evidence.map((evidence) => (
              <Badge key={evidence} variant="info" size="sm">
                {evidence}
              </Badge>
            ))}
          </div>
        </div>
      ) : null}

      <div className="mt-6 flex flex-wrap gap-2">
        <Button
          disabled={!item.can_prepare_kommo || blocked || isPreparing}
          onClick={() => onPrepare(item)}
        >
          Preparar na Kommo
        </Button>
        <Button variant="secondary" disabled={!item.context_path} onClick={() => item.context_path && onOpenContext(item.context_path)}>
          <ArrowUpRight size={14} />
          Abrir contexto
        </Button>
        <Button variant="danger" disabled={!item.can_reject || isFeedbacking} onClick={() => onReject(item)}>
          <XCircle size={14} />
          Rejeitar
        </Button>
      </div>
    </aside>
  );
}

function InfoBlock({ title, body, highlighted = false }: { title: string; body: string; highlighted?: boolean }) {
  return (
    <div className={cn("mt-5 rounded-2xl border p-4", highlighted ? "border-lovable-primary/45 bg-lovable-primary/10" : "border-lovable-border bg-lovable-bg-muted/45")}>
      <p className="text-xs font-semibold uppercase tracking-[0.22em] text-lovable-ink-muted">{title}</p>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-lovable-ink">{body}</p>
    </div>
  );
}
