import { AlertTriangle, RefreshCw } from "lucide-react";

import type { LeadToMemberIntelligenceContext, MemberIntelligenceSignalSeverity } from "../../types";
import { getPreferredShiftLabel } from "../../utils/preferredShift";
import { Badge, Button, Skeleton } from "../ui2";
import { formatDateTime } from "../assessments/assessmentWorkspaceUtils";

interface MemberIntelligenceMiniCardProps {
  context: LeadToMemberIntelligenceContext | null;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  title?: string;
}

const severityToBadgeVariant: Record<MemberIntelligenceSignalSeverity, "neutral" | "success" | "warning" | "danger" | "info"> = {
  neutral: "neutral",
  info: "info",
  success: "success",
  warning: "warning",
  danger: "danger",
};

function formatDays(days: number | null): string {
  if (days === null) return "sem registro";
  if (days === 0) return "hoje";
  if (days === 1) return "1 dia";
  return `${days} dias`;
}

function countMissingConsent(context: LeadToMemberIntelligenceContext): number {
  return context.consent.missing.length;
}

function formatPreferredShift(context: LeadToMemberIntelligenceContext): string {
  const rawShift = context.activity.preferred_shift ?? context.member.preferred_shift;
  return getPreferredShiftLabel(rawShift ?? "") || "Nao definido";
}

export function MemberIntelligenceMiniCard({
  context,
  isLoading,
  isError,
  onRetry,
  title = "Contexto canonico do aluno",
}: MemberIntelligenceMiniCardProps) {
  if (isLoading) {
    return (
      <section className="rounded-[24px] border border-lovable-border bg-lovable-bg-muted/45 p-4">
        <Skeleton className="h-4 w-48" />
        <div className="mt-4 grid gap-2 sm:grid-cols-2">
          <Skeleton className="h-16 rounded-2xl" />
          <Skeleton className="h-16 rounded-2xl" />
          <Skeleton className="h-16 rounded-2xl" />
          <Skeleton className="h-16 rounded-2xl" />
        </div>
      </section>
    );
  }

  if (isError || !context) {
    return (
      <section className="rounded-[24px] border border-[hsl(var(--lovable-warning)/0.35)] bg-[hsl(var(--lovable-warning)/0.08)] p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="flex items-start gap-3">
            <AlertTriangle size={18} className="mt-0.5 shrink-0 text-[hsl(var(--lovable-warning))]" />
            <div>
              <p className="text-sm font-semibold text-lovable-ink">Contexto canonico indisponivel</p>
              <p className="mt-1 text-xs text-lovable-ink-muted">
                A acao pode seguir, mas turno, origem e sinais integrados nao foram carregados.
              </p>
            </div>
          </div>
          <Button size="sm" variant="secondary" onClick={onRetry}>
            <RefreshCw size={14} />
            Recarregar
          </Button>
        </div>
      </section>
    );
  }

  const topSignals = context.signals.slice(0, 3);
  const missingConsentTotal = countMissingConsent(context);

  return (
    <section className="rounded-[24px] border border-lovable-primary/25 bg-lovable-bg-muted/45 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-lovable-primary">{title}</p>
          <p className="mt-1 text-sm text-lovable-ink-muted">
            Origem, turno, atividade e pendencias reais para decidir a execucao.
          </p>
        </div>
        <Badge variant="neutral" size="sm">
          {context.version}
        </Badge>
      </div>

      <div className="mt-4 grid gap-2 sm:grid-cols-2">
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface/75 px-3 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Turno</p>
          <p className="mt-1 text-sm font-semibold text-lovable-ink">{formatPreferredShift(context)}</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">{context.activity.checkins_30d} check-in(s) em 30 dias</p>
        </div>
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface/75 px-3 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Ultimo check-in</p>
          <p className="mt-1 text-sm font-semibold text-lovable-ink">{formatDays(context.activity.days_without_checkin)}</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">
            {context.activity.last_checkin_at ? formatDateTime(context.activity.last_checkin_at) : "Sem historico recente"}
          </p>
        </div>
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface/75 px-3 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Operacao</p>
          <p className="mt-1 text-sm font-semibold text-lovable-ink">{context.operations.open_tasks_total} task(s) abertas</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">{context.operations.overdue_tasks_total} atrasada(s)</p>
        </div>
        <div className="rounded-2xl border border-lovable-border bg-lovable-surface/75 px-3 py-3">
          <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Origem e consentimento</p>
          <p className="mt-1 text-sm font-semibold text-lovable-ink">{context.lead?.source ?? "Nao informada"}</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">
            {missingConsentTotal ? `${missingConsentTotal} consentimento(s) pendente(s)` : "Consentimentos sem lacuna critica"}
          </p>
        </div>
      </div>

      {topSignals.length ? (
        <div className="mt-4 flex flex-wrap gap-2">
          {topSignals.map((signal) => (
            <Badge key={`${signal.key}-${signal.source}`} variant={severityToBadgeVariant[signal.severity]} size="sm">
              {signal.label}: {signal.value === null ? "-" : String(signal.value)}
            </Badge>
          ))}
        </div>
      ) : (
        <p className="mt-4 text-xs text-lovable-ink-muted">Sem sinais integrados suficientes para este aluno.</p>
      )}

      {context.data_quality_flags.length ? (
        <p className="mt-3 text-xs text-lovable-ink-muted">
          Lacunas: {context.data_quality_flags.slice(0, 4).map((flag) => flag.split("_").join(" ")).join(", ")}.
        </p>
      ) : null}
    </section>
  );
}
