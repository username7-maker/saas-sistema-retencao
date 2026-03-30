import { useMemo } from "react";
import type { LucideIcon } from "lucide-react";
import { AlertTriangle, ChevronLeft, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";

import { type AssessmentDashboard, type AssessmentQueueResponse } from "../../services/assessmentService";
import { EmptyState, FilterBar, KPIStrip, PageHeader, RiskBadge, SectionHeader, SkeletonList, StatusBadge } from "../ui";
import { Badge, Button, Card, CardContent } from "../ui2";
import {
  ASSESSMENT_QUEUE_FILTER_OPTIONS,
  filterAttentionNowItems,
  getQueueRangeLabel,
  type AssessmentQueueFilter,
  type AssessmentQueueItem,
  type AssessmentQueueBucket,
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
  page: number;
  onPageChange: (page: number) => void;
  onClearFilters: () => void;
  onRetryQueue: () => void;
  emptyStateIcon?: LucideIcon;
}

const BUCKET_STATUS_MAP: Record<AssessmentQueueBucket, { label: string; variant: "neutral" | "success" | "warning" | "danger" }> = {
  overdue: { label: "Atrasada", variant: "danger" },
  never: { label: "Primeira avaliação", variant: "warning" },
  week: { label: "Esta semana", variant: "warning" },
  upcoming: { label: "Próxima", variant: "neutral" },
  covered: { label: "Cobertura recente", variant: "success" },
};

function QueueActions({ memberId }: { memberId: string }) {
  return (
    <div className="flex flex-wrap items-center gap-2 lg:justify-end">
      <Link
        to={`/assessments/members/${memberId}`}
        className="inline-flex h-8 items-center justify-center rounded-lg border border-lovable-border px-3 text-xs font-semibold text-lovable-ink hover:bg-lovable-surface-soft"
      >
        Abrir workspace
      </Link>
      <Link
        to={`/assessments/members/${memberId}?tab=registro`}
        className="inline-flex h-8 items-center justify-center rounded-lg bg-lovable-primary px-3 text-xs font-semibold text-white hover:brightness-105"
      >
        Registrar avaliação
      </Link>
    </div>
  );
}

function AssessmentQueueRow({ member }: { member: AssessmentQueueItem }) {
  return (
    <li className="grid gap-3 px-4 py-4 lg:grid-cols-[minmax(0,1.5fr)_minmax(180px,0.9fr)_minmax(240px,1fr)_auto] lg:items-center">
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-lovable-ink">{member.full_name}</p>
        <p className="mt-1 truncate text-xs text-lovable-ink-muted">{member.email || "Sem e-mail cadastrado"}</p>
      </div>

      <div className="min-w-0 space-y-2">
        <p className="truncate text-xs font-medium text-lovable-ink-muted">{member.plan_name || "Plano não informado"}</p>
        <div className="flex flex-wrap items-center gap-2">
          <RiskBadge risk={member.risk_level} />
          <StatusBadge status={member.queue_bucket} map={BUCKET_STATUS_MAP} />
        </div>
      </div>

      <div className="min-w-0 space-y-1">
        <p className="truncate text-sm font-medium text-lovable-ink">{member.coverage_label}</p>
        <p className="truncate text-xs text-lovable-ink-muted">{member.due_label}</p>
      </div>

      <QueueActions memberId={member.id} />
    </li>
  );
}

function AttentionNowList({ items }: { items: AssessmentQueueItem[] }) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-lovable-border px-4 py-5 text-sm text-lovable-ink-muted">
        Sem casos críticos no filtro atual.
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
            </div>
            <div className="flex items-center gap-2">
              <RiskBadge risk={member.risk_level} />
              <Link to={`/assessments/members/${member.id}`} className="text-xs font-semibold text-lovable-primary hover:underline">
                Abrir workspace
              </Link>
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
  page,
  onPageChange,
  onClearFilters,
  onRetryQueue,
  emptyStateIcon,
}: AssessmentOperationsBoardProps) {
  const hasActiveFilters = searchQuery.trim().length > 0 || activeFilter !== "all";
  const totalPages = queue ? Math.max(1, Math.ceil(queue.total / queue.page_size)) : 1;
  const coverageRatio = dashboard.total_members > 0 ? Math.round((dashboard.assessed_last_90_days / dashboard.total_members) * 100) : 0;
  const overduePressure = dashboard.total_members > 0 ? Math.round((dashboard.overdue_assessments / dashboard.total_members) * 100) : 0;

  const attentionNow = useMemo(() => {
    const source = hasActiveFilters ? queue?.items ?? [] : dashboard.attention_now ?? [];
    return filterAttentionNowItems(source, searchQuery, activeFilter).slice(0, 6);
  }, [activeFilter, dashboard.attention_now, hasActiveFilters, queue?.items, searchQuery]);

  const executiveRead = [
    dashboard.overdue_assessments > 0
      ? `${dashboard.overdue_assessments} aluno(s) estão fora da janela ideal e puxam a fila de recuperação.`
      : "Não há atrasos abertos na janela de avaliação.",
    dashboard.never_assessed > 0
      ? `${dashboard.never_assessed} aluno(s) ainda não tiveram a primeira leitura estruturada.`
      : "Toda a base atual já tem ao menos uma avaliação registrada.",
    dashboard.upcoming_7_days > 0
      ? `${dashboard.upcoming_7_days} avaliação(ões) entram no radar dos próximos 7 dias.`
      : "Não há vencimentos imediatos para os próximos 7 dias.",
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Avaliações"
        subtitle="Priorize atrasos, primeiras leituras e próximas janelas sem perder a visão executiva da base."
        breadcrumb={[{ label: "Workspace" }, { label: "Avaliações" }]}
      />

      <div className="space-y-3">
        <FilterBar
          search={{
            value: searchQuery,
            onChange: onSearchQueryChange,
            placeholder: "Buscar por nome, e-mail, plano, telefone ou CPF...",
          }}
          activeCount={(searchQuery.trim() ? 1 : 0) + (activeFilter !== "all" ? 1 : 0)}
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
      </div>

      <KPIStrip
        items={[
          { label: "Atrasadas", value: dashboard.overdue_assessments, tone: "danger" },
          { label: "Vencem em breve", value: dashboard.upcoming_7_days, tone: "warning" },
          { label: "Nunca avaliados", value: dashboard.never_assessed, tone: "warning" },
          { label: "Cobertura recente", value: `${coverageRatio}%`, tone: coverageRatio >= 70 ? "success" : "neutral" },
        ]}
      />

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-lovable-primary/20 bg-lovable-primary-soft/70">
          <CardContent className="space-y-3 pt-5">
            <SectionHeader
              title="Leitura executiva enxuta"
              subtitle={`Pressão operacional atual: ${overduePressure}% da base com atraso ativo.`}
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
              title="Precisa de atenção agora"
              subtitle="Subconjunto curto para a equipe bater o olho e agir."
              count={attentionNow.length}
            />
            <AttentionNowList items={attentionNow} />
          </CardContent>
        </Card>
      </section>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <SectionHeader
            title="Fila operacional"
            subtitle={queue ? getQueueRangeLabel(queue.total, queue.page, queue.page_size) : "Carregando fila..."}
            actions={queueFetching && !queueLoading ? <Badge variant="neutral">Atualizando…</Badge> : undefined}
            count={queue?.total ?? 0}
          />

          {queueLoading ? (
            <SkeletonList rows={8} cols={4} />
          ) : queueError ? (
            <EmptyState
              icon={AlertTriangle}
              title="Não foi possível carregar a fila"
              description="Tente novamente para recuperar a lista completa de alunos da operação."
              action={{ label: "Tentar novamente", onClick: onRetryQueue }}
            />
          ) : !queue || queue.items.length === 0 ? (
            <EmptyState
              icon={emptyStateIcon}
              title="Nenhum aluno encontrado"
              description={
                hasActiveFilters
                  ? "Ajuste a busca ou limpe os filtros para voltar a enxergar a fila operacional."
                  : "Ainda não há alunos disponíveis na fila operacional."
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
                  <span className="lg:text-right">Ações</span>
                </div>
                <ul className="divide-y divide-lovable-border">
                  {queue.items.map((member) => (
                    <AssessmentQueueRow key={member.id} member={member} />
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
                    Página {page} de {totalPages}
                  </Badge>
                  <Button size="sm" variant="secondary" onClick={() => onPageChange(page + 1)} disabled={page >= totalPages}>
                    Próxima
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
