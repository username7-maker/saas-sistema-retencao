import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { Badge, Button, Card, CardContent, Input } from "../ui2";
import type { AssessmentDashboard } from "../../services/assessmentService";
import {
  buildOperationalAssessmentMembers,
  filterOperationalAssessmentMembers,
  formatDate,
  getAttentionNowMembers,
  groupOperationalAssessmentMembers,
  type AssessmentQueueFilter,
  type OperationalAssessmentMember,
} from "./assessmentOperationsUtils";

interface AssessmentOperationsBoardProps {
  dashboard: AssessmentDashboard;
}

function getRiskVariant(level: OperationalAssessmentMember["risk_level"]): "success" | "warning" | "danger" {
  if (level === "red") return "danger";
  if (level === "yellow") return "warning";
  return "success";
}

function getBucketAccent(bucket: OperationalAssessmentMember["queueBucket"]): string {
  if (bucket === "overdue") return "border-l-lovable-danger";
  if (bucket === "never") return "border-l-lovable-warning";
  if (bucket === "week") return "border-l-lovable-primary";
  if (bucket === "upcoming") return "border-l-sky-500";
  return "border-l-emerald-500";
}

function getBucketLabel(bucket: OperationalAssessmentMember["queueBucket"]): string {
  if (bucket === "overdue") return "Atrasada";
  if (bucket === "never") return "Primeira avaliacao";
  if (bucket === "week") return "Janela da semana";
  if (bucket === "upcoming") return "Proxima janela";
  return "Cobertura recente";
}

function StatTile({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <Card>
      <CardContent className="space-y-2 pt-5">
        <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">{label}</p>
        <p className="text-2xl font-semibold text-lovable-ink">{value}</p>
        <p className="text-xs text-lovable-ink-muted">{helper}</p>
      </CardContent>
    </Card>
  );
}

function AssessmentRow({ member }: { member: OperationalAssessmentMember }) {
  return (
    <li
      className={`rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel transition hover:border-lovable-border-strong ${getBucketAccent(member.queueBucket)} border-l-4`}
    >
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <p className="text-base font-semibold text-lovable-ink">{member.full_name}</p>
            <Badge variant={getRiskVariant(member.risk_level)}>
              {member.risk_level.toUpperCase()} · {member.risk_score}
            </Badge>
            <Badge variant="neutral">{getBucketLabel(member.queueBucket)}</Badge>
          </div>

          <div className="flex flex-wrap gap-2 text-xs text-lovable-ink-muted">
            <span>{member.plan_name || "Plano nao informado"}</span>
            {member.email ? <span>{member.email}</span> : null}
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Status operacional</p>
              <p className="mt-1 text-sm font-medium text-lovable-ink">{member.coverageLabel}</p>
            </div>
            <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Prazo / janela</p>
              <p className="mt-1 text-sm font-medium text-lovable-ink">{member.dueLabel}</p>
            </div>
          </div>
        </div>

        <div className="flex shrink-0 flex-wrap gap-2">
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
        </div>
      </div>
    </li>
  );
}

export function AssessmentOperationsBoard({ dashboard }: AssessmentOperationsBoardProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeFilter, setActiveFilter] = useState<AssessmentQueueFilter>("all");

  const members = useMemo(() => buildOperationalAssessmentMembers(dashboard), [dashboard]);
  const filteredMembers = useMemo(
    () => filterOperationalAssessmentMembers(members, searchQuery, activeFilter),
    [activeFilter, members, searchQuery],
  );
  const attentionNow = useMemo(() => getAttentionNowMembers(filteredMembers), [filteredMembers]);
  const groups = useMemo(() => groupOperationalAssessmentMembers(filteredMembers), [filteredMembers]);

  const coverageRatio =
    dashboard.total_members > 0 ? Math.round((dashboard.assessed_last_90_days / dashboard.total_members) * 100) : 0;
  const overduePressure =
    dashboard.total_members > 0 ? Math.round((dashboard.overdue_assessments / dashboard.total_members) * 100) : 0;
  const hasActiveFilters = searchQuery.trim().length > 0 || activeFilter !== "all";

  const executiveRead = [
    dashboard.overdue_assessments > 0
      ? `${dashboard.overdue_assessments} aluno(s) estao fora da janela ideal e puxam a fila de recuperacao.`
      : "Nao ha atrasos abertos na janela de avaliacao.",
    dashboard.never_assessed > 0
      ? `${dashboard.never_assessed} aluno(s) ainda nao tiveram a primeira leitura estruturada.`
      : "Toda a base atual ja tem ao menos uma avaliacao registrada.",
    dashboard.upcoming_7_days > 0
      ? `${dashboard.upcoming_7_days} avaliacao(oes) entram no radar dos proximos 7 dias.`
      : "Nao ha vencimentos imediatos para os proximos 7 dias.",
  ];

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Central operacional</p>
          <div>
            <h2 className="font-heading text-3xl font-bold text-lovable-ink">Avaliacoes</h2>
            <p className="text-sm text-lovable-ink-muted">
              Priorize atrasos, primeiras leituras e proximas janelas sem perder a visao executiva da base.
            </p>
          </div>
        </div>
        <div className="flex w-full max-w-xl flex-col gap-3 lg:items-end">
          <div className="w-full">
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Buscar aluno</label>
            <Input
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              placeholder="Buscar por nome, email ou contexto da avaliacao..."
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="sm" variant={activeFilter === "all" ? "primary" : "secondary"} onClick={() => setActiveFilter("all")}>
              Tudo
            </Button>
            <Button size="sm" variant={activeFilter === "overdue" ? "primary" : "secondary"} onClick={() => setActiveFilter("overdue")}>
              Atrasadas
            </Button>
            <Button size="sm" variant={activeFilter === "never" ? "primary" : "secondary"} onClick={() => setActiveFilter("never")}>
              Nunca avaliados
            </Button>
            <Button size="sm" variant={activeFilter === "week" ? "primary" : "secondary"} onClick={() => setActiveFilter("week")}>
              Esta semana
            </Button>
            {hasActiveFilters ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => {
                  setSearchQuery("");
                  setActiveFilter("all");
                }}
              >
                Limpar filtros
              </Button>
            ) : null}
          </div>
        </div>
      </header>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
        <StatTile label="Atrasadas" value={String(dashboard.overdue_assessments)} helper="janela fora do prazo ideal" />
        <StatTile label="Vencem em breve" value={String(dashboard.upcoming_7_days)} helper="avaliacoes previstas para 7 dias" />
        <StatTile label="Nunca avaliados" value={String(dashboard.never_assessed)} helper="primeira leitura ainda pendente" />
        <StatTile label="Pressao operacional" value={`${overduePressure}%`} helper="parcela da base com atraso ativo" />
        <StatTile label="Cobertura recente" value={`${coverageRatio}%`} helper="avaliados nos ultimos 90 dias" />
      </section>

      <section className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
        <Card className="border-lovable-primary/20 bg-lovable-primary-soft/70">
          <CardContent className="space-y-3 pt-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">Leitura executiva enxuta</p>
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
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Precisa de atencao agora</p>
                <p className="text-sm text-lovable-ink-muted">Subconjunto curto para a equipe bater o olho e agir.</p>
              </div>
              <Badge variant="warning">{attentionNow.length} no foco imediato</Badge>
            </div>

            {attentionNow.length === 0 ? (
              <div className="rounded-xl border border-dashed border-lovable-border px-4 py-5 text-sm text-lovable-ink-muted">
                Sem casos criticos no filtro atual.
              </div>
            ) : (
              <ul className="space-y-2">
                {attentionNow.map((member) => (
                  <li key={member.id} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                    <div className="flex flex-col gap-2 lg:flex-row lg:items-center lg:justify-between">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-lovable-ink">{member.full_name}</p>
                        <p className="text-xs text-lovable-ink-muted">{member.dueLabel}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={getRiskVariant(member.risk_level)}>{member.risk_level.toUpperCase()}</Badge>
                        <Link
                          to={`/assessments/members/${member.id}`}
                          className="text-xs font-semibold text-lovable-primary hover:underline"
                        >
                          Abrir workspace
                        </Link>
                      </div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      </section>

      <section className="space-y-4">
        {groups.length === 0 ? (
          <Card>
            <CardContent className="space-y-3 pt-5">
              <p className="text-sm font-semibold text-lovable-ink">Nenhum aluno encontrado</p>
              <p className="text-sm text-lovable-ink-muted">
                Ajuste a busca ou limpe os filtros para voltar a enxergar a fila operacional.
              </p>
            </CardContent>
          </Card>
      ) : (
          groups.map((group) => (
            <Card key={group.key}>
              <CardContent className="space-y-4 pt-5">
                <div className="flex flex-col gap-1 lg:flex-row lg:items-end lg:justify-between">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">{group.label}</p>
                    <p className="text-sm text-lovable-ink-muted">{group.description}</p>
                  </div>
                  <Badge variant="neutral">{group.members.length} aluno(s)</Badge>
                </div>

                {group.members.length === 0 ? (
                  <p className="text-sm text-lovable-ink-muted">{group.emptyMessage}</p>
                ) : (
                  <ul className="space-y-3">
                    {group.members.map((member) => (
                      <AssessmentRow key={member.id} member={member} />
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          ))
        )}
      </section>

      {dashboard.assessed_members?.length ? (
        <Card>
          <CardContent className="space-y-2 pt-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Base coberta recentemente</p>
            <p className="text-sm text-lovable-ink-muted">
              {dashboard.assessed_last_90_days} aluno(s) ja tiveram avaliacao nos ultimos 90 dias. Ultima atualizacao da agenda:
              {" "}
              {(dashboard.upcoming_members?.[0] as { next_assessment_due?: string | null } | undefined)?.next_assessment_due
                ? formatDate((dashboard.upcoming_members?.[0] as { next_assessment_due?: string | null }).next_assessment_due)
                : "sem janela futura definida"}.
            </p>
          </CardContent>
        </Card>
      ) : null}
    </div>
  );
}
