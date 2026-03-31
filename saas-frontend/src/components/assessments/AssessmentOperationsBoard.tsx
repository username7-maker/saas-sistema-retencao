import { useMemo } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { PreferredShiftBadge } from "../common/PreferredShiftBadge";
import {
  type AssessmentDashboard,
  type AssessmentQueueResolutionStatus,
  type AssessmentQueueResponse,
} from "../../services/assessmentService";
import { EmptyState, FilterBar, KPIStrip, PageHeader, RiskBadge, SectionHeader, SkeletonList, StatusBadge } from "../ui";
import { Badge, Button, Card, CardContent } from "../ui2";
import {
  ASSESSMENT_QUEUE_FILTER_OPTIONS,
  filterAttentionNowItems,
  getQueueRangeLabel,
  type AssessmentQueueBucket,
  type AssessmentQueueFilter,
  type AssessmentQueueItem,
  type PreferredShiftFilter,
} from "./assessmentOperationsUtils";

interface AssessmentOperationsBoardProps {
  dashboard: AssessmentDashboard;
  queue?: AssessmentQueueResponse;
  queueLoading: boolean;
  queueFetching: boolean;
  queueError: boolean;
  searchQuery: string;
  onSearchQueryChange: (value: string) => void;
  activeFilter: AssessmentQueueFilter;
  onActiveFilterChange: (value: AssessmentQueueFilter) => void;
  activeShift: PreferredShiftFilter;
  onActiveShiftChange: (value: PreferredShiftFilter) => void;
  page: number;
  onPageChange: (page: number) => void;
  onClearFilters: () => void;
  onRetryQueue: () => void;
  emptyStateIcon?: LucideIcon;
  queueResolutionPendingMemberId?: string | null;
  onQueueResolutionChange: (memberId: string, status: AssessmentQueueResolutionStatus) => void;
}

const BUCKET_STATUS_MAP: Record<
  AssessmentQueueBucket,
  { label: string; variant: "neutral" | "success" | "warning" | "danger" }
> = {
  overdue: { label: "Atrasada", variant: "danger" },
  never: { label: "Primeira avaliacao", variant: "warning" },
  week: { label: "Esta semana", variant: "warning" },
  upcoming: { label: "Proxima", variant: "neutral" },
  covered: { label: "Cobertura recente", variant: "success" },
};

function getQueueResolutionBadgeVariant(status: AssessmentQueueResolutionStatus): "neutral" | "success" | "warning" {
  if (status === "scheduled") return "success";
  if (status === "dismissed") return "warning";
  return "neutral";
}

function QueueActions({
  member,
  isPending,
  onQueueResolutionChange,
}: {
  member: AssessmentQueueItem;
  isPending: boolean;
  onQueueResolutionChange: (memberId: string, status: AssessmentQueueResolutionStatus) => void;
}) {
  const resolutionStatus = member.queue_resolution_status ?? "active";
  const canTriage = member.queue_bucket !== "covered";
  return (
    <div className="flex flex-wrap items-center gap-2 lg:justify-end">
      <Link
        to={`/assessments/members/${member.id}`}
        className="inline-flex h-8 items-center justify-center rounded-lg border border-lovable-border px-3 text-xs font-semibold text-lovable-ink hover:bg-lovable-surface-soft"
      >
        Abrir workspace
      </Link>
      <Link
        to={`/assessments/members/${member.id}?tab=registro`}
        className="inline-flex h-8 items-center justify-center rounded-lg bg-lovable-primary px-3 text-xs font-semibold text-white hover:brightness-105"
      >
        Registrar avaliacao
      </Link>
      {!canTriage ? null : resolutionStatus === "active" ? (
        <>
          <Button size="sm" variant="secondary" disabled={isPending} onClick={() => onQueueResolutionChange(member.id, "scheduled")}>
            Ja foi marcada
          </Button>
          <Button size="sm" variant="ghost" disabled={isPending} onClick={() => onQueueResolutionChange(member.id, "dismissed")}>
            Ocultar
          </Button>
        </>
      ) : (
        <Button size="sm" variant="secondary" disabled={isPending} onClick={() => onQueueResolutionChange(member.id, "active")}>
          Reabrir fila
        </Button>
      )}
    </div>
  );
}

function AssessmentQueueRow({
  member,
  isPending,
  onQueueResolutionChange,
}: {
  member: AssessmentQueueItem;
  isPending: boolean;
  onQueueResolutionChange: (memberId: string, status: AssessmentQueueResolutionStatus) => void;
}) {
  const resolutionStatus = member.queue_resolution_status ?? "active";
  return (
    <li className="grid gap-3 px-4 py-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(180px,0.9fr)_minmax(240px,1fr)_auto] lg:items-center">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-lovable-ink">{member.full_name}</p>
        <p className="mt-1 truncate text-xs text-lovable-ink-muted">{member.email || "Sem e-mail cadastrado"}</p>
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <PreferredShiftBadge preferredShift={member.preferred_shift} prefix />
        </div>
      </div>

      <div className="min-w-0 space-y-2">
        <p className="truncate text-xs font-medium text-lovable-ink-muted">{member.plan_name || "Plano nao informado"}</p>
        <div className="flex flex-wrap items-center gap-2">
          <RiskBadge risk={member.risk_level} />
          <StatusBadge status={member.queue_bucket} map={BUCKET_STATUS_MAP} />
        </div>
      </div>

      <div className="min-w-0 space-y-1">
        <p className="truncate text-sm font-medium text-lovable-ink">{member.coverage_label}</p>
        <p className="truncate text-xs text-lovable-ink-muted">{member.due_label}</p>
        {resolutionStatus !== "active" ? (
          <div className="flex flex-wrap items-center gap-2 pt-1">
            <Badge variant={getQueueResolutionBadgeVariant(resolutionStatus)} size="sm" className="normal-case tracking-normal">
              {member.queue_resolution_label || "Fora da fila"}
            </Badge>
            {member.queue_resolution_note ? (
              <span className="truncate text-[11px] text-lovable-ink-muted">{member.queue_resolution_note}</span>
            ) : null}
          </div>
        ) : null}
      </div>

      <QueueActions member={member} isPending={isPending} onQueueResolutionChange={onQueueResolutionChange} />
    </li>
  );
}

function AttentionNowList({
  items,
  pendingMemberId,
  onQueueResolutionChange,
}: {
  items: AssessmentQueueItem[];
  pendingMemberId?: string | null;
  onQueueResolutionChange: (memberId: string, status: AssessmentQueueResolutionStatus) => void;
}) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-lovable-border px-4 py-5 text-sm text-lovable-ink-muted">
        Sem casos criticos no filtro atual.
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {items.map((member) => (
        <li key={member.id} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
          <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold text-lovable-ink">{member.full_name}</p>
              <p className="truncate text-xs text-lovable-ink-muted">{member.due_label}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <PreferredShiftBadge preferredShift={member.preferred_shift} prefix />
              </div>
              {(member.queue_resolution_status ?? "active") !== "active" ? (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge
                    variant={getQueueResolutionBadgeVariant(member.queue_resolution_status ?? "active")}
                    size="sm"
                    className="normal-case tracking-normal"
                  >
                    {member.queue_resolution_label || "Fora da fila"}
                  </Badge>
                  {member.queue_resolution_note ? (
                    <span className="truncate text-[11px] text-lovable-ink-muted">{member.queue_resolution_note}</span>
                  ) : null}
                </div>
              ) : null}
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <RiskBadge risk={member.risk_level} />
              <Link to={`/assessments/members/${member.id}`} className="text-xs font-semibold text-lovable-primary hover:underline">
                Abrir workspace
              </Link>
              {member.queue_bucket === "covered" ? null : (member.queue_resolution_status ?? "active") === "active" ? (
                <>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={pendingMemberId === member.id}
                    onClick={() => onQueueResolutionChange(member.id, "scheduled")}
                  >
                    Ja foi marcada
                  </Button>
                  <Button
                    size="sm"
                    variant="ghost"
                    disabled={pendingMemberId === member.id}
                    onClick={() => onQueueResolutionChange(member.id, "dismissed")}
                  >
                    Ocultar
                  </Button>
                </>
              ) : (
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={pendingMemberId === member.id}
                  onClick={() => onQueueResolutionChange(member.id, "active")}
                >
                  Reabrir fila
                </Button>
              )}
            </div>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function AssessmentOperationsBoard({
  dashboard,
  queue,
  queueLoading,
  queueFetching,
  queueError,
  searchQuery,
  onSearchQueryChange,
  activeFilter,
  onActiveFilterChange,
  activeShift,
  onActiveShiftChange,
  page,
  onPageChange,
  onClearFilters,
  onRetryQueue,
  emptyStateIcon,
  queueResolutionPendingMemberId,
  onQueueResolutionChange,
}: AssessmentOperationsBoardProps) {
  const hasActiveFilters = searchQuery.trim().length > 0 || activeFilter !== "all" || activeShift !== "all";
  const totalPages = queue ? Math.max(1, Math.ceil(queue.total / queue.page_size)) : 1;
  const coverageRatio = dashboard.total_members > 0 ? Math.round((dashboard.assessed_last_90_days / dashboard.total_members) * 100) : 0;
  const overduePressure = dashboard.total_members > 0 ? Math.round((dashboard.overdue_assessments / dashboard.total_members) * 100) : 0;
  const activeBaseLabel = `${dashboard.total_members} aluno(s) ativos na base`;
  const hasHistoricalBacklog = dashboard.historical_backlog_total > 0;

  const attentionNow = useMemo(() => {
    const source = hasActiveFilters ? queue?.items ?? [] : dashboard.attention_now ?? [];
    return filterAttentionNowItems(source, searchQuery, activeFilter, activeShift).slice(0, 6);
  }, [activeFilter, activeShift, dashboard.attention_now, hasActiveFilters, queue?.items, searchQuery]);

  const executiveRead = [
    dashboard.overdue_assessments > 0
      ? `${dashboard.overdue_assessments} aluno(s) ativos estao fora da janela ideal e puxam a fila de recuperacao.`
      : "Nao ha atrasos abertos na janela de avaliacao.",
    dashboard.never_assessed > 0
      ? `${dashboard.never_assessed} aluno(s) ativos entram agora na fila de primeira avaliacao.`
      : "Toda a base ativa ja tem ao menos uma avaliacao registrada.",
    dashboard.upcoming_7_days > 0
      ? `${dashboard.upcoming_7_days} avaliacao(oes) entram no radar dos proximos 7 dias.`
      : "Nao ha vencimentos imediatos para os proximos 7 dias.",
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Avaliacoes"
        subtitle="Priorize atrasos, primeiras leituras e proximas janelas sem perder a visao executiva da base ativa."
        breadcrumb={[{ label: "Workspace" }, { label: "Avaliacoes" }]}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="success">Base ativa</Badge>
            <Badge variant="neutral">{activeBaseLabel}</Badge>
          </div>
        }
      />

      <div className="space-y-3">
        <FilterBar
          search={{
            value: searchQuery,
            onChange: onSearchQueryChange,
            placeholder: "Buscar qualquer aluno ativo por nome, e-mail ou plano...",
          }}
          filters={[
            {
              key: "preferred_shift",
              label: "Turno",
              value: activeShift,
              onChange: (value) => onActiveShiftChange(value as PreferredShiftFilter),
              options: [
                { value: "all", label: "Todos os turnos" },
                { value: "morning", label: "Manha" },
                { value: "afternoon", label: "Tarde" },
                { value: "evening", label: "Noite" },
              ],
            },
          ]}
          activeCount={(searchQuery.trim() ? 1 : 0) + (activeFilter !== "all" ? 1 : 0) + (activeShift !== "all" ? 1 : 0)}
          onClear={onClearFilters}
        />

        <div className="flex flex-wrap gap-2">
          {ASSESSMENT_QUEUE_FILTER_OPTIONS.map((option) => (
            <Button
              key={option.key}
              size="sm"
              variant={activeFilter === option.key ? "primary" : "secondary"}
              onClick={() => onActiveFilterChange(option.key)}
            >
              {option.label}
            </Button>
          ))}
        </div>

        <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3 text-sm text-lovable-ink-muted">
          Esta tela considera apenas alunos com status ativo. Cancelados e pausados ficam fora da fila operacional de avaliacoes.
        </div>

        {hasHistoricalBacklog ? (
          <div className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100">
            {dashboard.historical_backlog_total} aluno(s) ficaram fora da fila do dia por serem backlog historico.
            {" "}Sao {dashboard.historical_never_assessed} sem primeira avaliacao recente e {dashboard.historical_overdue_assessments} reavaliacoes antigas sem engajamento recente.
          </div>
        ) : null}
      </div>

      <KPIStrip
        items={[
          { label: "Atrasadas", value: dashboard.overdue_assessments, tone: "danger" },
          { label: "Vencem em breve", value: dashboard.upcoming_7_days, tone: "warning" },
          { label: "Primeira avaliacao", value: dashboard.never_assessed, tone: "warning" },
          { label: "Cobertura recente", value: `${coverageRatio}%`, tone: coverageRatio >= 70 ? "success" : "neutral" },
        ]}
      />

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-lovable-primary/20 bg-lovable-primary-soft/70">
          <CardContent className="space-y-3 pt-5">
            <SectionHeader
              title="Resumo do dia"
              subtitle={`Pressao operacional atual: ${overduePressure}% da base ativa com atraso em avaliacao.`}
            />
            <ul className="space-y-2 text-sm text-lovable-ink">
              {executiveRead.map((line) => (
                <li key={line} className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
                  {line}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="space-y-3 pt-5">
            <SectionHeader
              title="Precisa de atencao agora"
              subtitle="Subconjunto curto para a equipe agir sem varrer a fila inteira."
              count={attentionNow.length}
            />
            <AttentionNowList
              items={attentionNow}
              pendingMemberId={queueResolutionPendingMemberId}
              onQueueResolutionChange={onQueueResolutionChange}
            />
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <SectionHeader
            title="Fila operacional"
            subtitle={queue ? `${getQueueRangeLabel(queue.total, queue.page, queue.page_size)} na base ativa.` : "Carregando fila..."}
            actions={queueFetching && !queueLoading ? <Badge variant="neutral">Atualizando...</Badge> : undefined}
            count={queue?.total ?? 0}
          />

          {queueLoading ? (
            <SkeletonList rows={8} cols={4} />
          ) : queueError ? (
            <EmptyState
              icon={AlertTriangle}
              title="Nao foi possivel carregar a fila"
              description="Tente novamente para recuperar a lista completa de alunos da operacao."
              action={{ label: "Tentar novamente", onClick: onRetryQueue }}
            />
          ) : !queue || queue.items.length === 0 ? (
            <EmptyState
              icon={emptyStateIcon}
              title="Nenhum aluno encontrado"
              description={
                hasActiveFilters
                  ? "Ajuste a busca ou limpe os filtros para voltar a enxergar a fila operacional."
                  : "Ainda nao ha alunos disponiveis na fila operacional."
              }
              action={hasActiveFilters ? { label: "Limpar filtros", onClick: onClearFilters } : undefined}
            />
          ) : (
            <>
              <div className="overflow-hidden rounded-2xl border border-lovable-border bg-lovable-surface">
                <div className="grid gap-3 border-b border-lovable-border bg-lovable-surface-soft px-4 py-3 text-[11px] font-semibold uppercase tracking-widest text-lovable-ink-muted lg:grid-cols-[minmax(0,1.5fr)_minmax(180px,0.9fr)_minmax(240px,1fr)_auto]">
                  <span>Aluno</span>
                  <span>Risco e cobertura</span>
                  <span>Status operacional</span>
                  <span className="lg:text-right">Acoes</span>
                </div>
                <ul className="divide-y divide-lovable-border">
                  {queue.items.map((member) => (
                    <AssessmentQueueRow
                      key={member.id}
                      member={member}
                      isPending={queueResolutionPendingMemberId === member.id}
                      onQueueResolutionChange={onQueueResolutionChange}
                    />
                  ))}
                </ul>
              </div>

              <div className="flex flex-col gap-3 border-t border-lovable-border pt-4 sm:flex-row sm:items-center sm:justify-between">
                <p className="text-sm text-lovable-ink-muted">{getQueueRangeLabel(queue.total, queue.page, queue.page_size)}</p>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="secondary" onClick={() => onPageChange(page - 1)} disabled={page <= 1}>
                    <ChevronLeft size={14} />
                    Anterior
                  </Button>
                  <Badge variant="neutral">
                    Pagina {page} de {totalPages}
                  </Badge>
                  <Button size="sm" variant="secondary" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>
                    Proxima
                    <ChevronRight size={14} />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
