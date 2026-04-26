import { AlertTriangle, RefreshCw } from "lucide-react";

import type { LeadToMemberIntelligenceContext, MemberIntelligenceSignalSeverity } from "../../types";
import { Badge, Button, Card, CardContent, Skeleton } from "../ui2";
import { formatDateTime } from "./assessmentWorkspaceUtils";

interface MemberIntelligenceContextPanelProps {
  context: LeadToMemberIntelligenceContext | null;
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
}

const severityToBadgeVariant: Record<MemberIntelligenceSignalSeverity, "neutral" | "success" | "warning" | "danger" | "info"> = {
  neutral: "neutral",
  info: "info",
  success: "success",
  warning: "warning",
  danger: "danger",
};

const consentLabels: Record<string, string> = {
  lgpd: "LGPD",
  communication: "Comunicacao",
  image: "Imagem",
  contract: "Contrato",
};

function safeValue(value: string | number | boolean | null | undefined): string {
  if (typeof value === "boolean") return value ? "Sim" : "Nao";
  if (value === null || value === undefined || value === "") return "-";
  return String(value);
}

function formatDays(days: number | null): string {
  if (days === null) return "Sem registro";
  if (days === 0) return "Hoje";
  if (days === 1) return "1 dia";
  return `${days} dias`;
}

function formatConsent(value: boolean | null): { label: string; variant: "success" | "warning" | "neutral" } {
  if (value === true) return { label: "Ok", variant: "success" };
  if (value === false) return { label: "Negado", variant: "warning" };
  return { label: "Pendente", variant: "neutral" };
}

function InfoTile({ label, value, helper }: { label: string; value: string; helper?: string }) {
  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{label}</p>
      <p className="mt-2 text-base font-semibold text-lovable-ink">{value}</p>
      {helper ? <p className="mt-1 text-xs leading-relaxed text-lovable-ink-muted">{helper}</p> : null}
    </div>
  );
}

export function MemberIntelligenceContextPanel({
  context,
  isLoading,
  isError,
  onRetry,
}: MemberIntelligenceContextPanelProps) {
  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-4 pt-5">
          <Skeleton className="h-5 w-52" />
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <Skeleton className="h-24 rounded-2xl" />
            <Skeleton className="h-24 rounded-2xl" />
            <Skeleton className="h-24 rounded-2xl" />
            <Skeleton className="h-24 rounded-2xl" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (isError || !context) {
    return (
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-5">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 text-[hsl(var(--lovable-warning))]" />
            <div>
              <p className="text-sm font-semibold text-lovable-ink">Inteligencia do aluno indisponivel</p>
              <p className="text-xs text-lovable-ink-muted">
                O perfil segue funcionando. Tente recarregar este bloco antes de usar origem, consentimento e sinais integrados.
              </p>
            </div>
          </div>
          <Button size="sm" variant="secondary" onClick={onRetry}>
            <RefreshCw className="h-4 w-4" />
            Recarregar
          </Button>
        </CardContent>
      </Card>
    );
  }

  const consentEntries = [
    ["lgpd", context.consent.lgpd],
    ["communication", context.consent.communication],
    ["image", context.consent.image],
    ["contract", context.consent.contract],
  ] as const;

  return (
    <Card className="border-lovable-primary/25 bg-gradient-to-br from-lovable-primary-soft/70 via-lovable-surface to-lovable-surface">
      <CardContent className="space-y-5 pt-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-lovable-primary">Inteligencia do aluno</p>
            <h3 className="mt-1 text-lg font-semibold text-lovable-ink">Contexto canonico lead para membro</h3>
            <p className="mt-1 max-w-3xl text-sm text-lovable-ink-muted">
              Origem comercial, consentimentos, atividade, avaliacoes, tarefas e risco em uma leitura unica para a equipe.
            </p>
          </div>
          <div className="flex flex-wrap justify-end gap-2">
            <Badge variant="info" size="sm">{context.version}</Badge>
            <Badge variant="neutral" size="sm">Atualizado {formatDateTime(context.generated_at)}</Badge>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <InfoTile
            label="Origem"
            value={context.lead?.source ?? "Nao informada"}
            helper={context.lead?.stage ? `Etapa comercial: ${context.lead.stage}` : "Sem lead convertido vinculado"}
          />
          <InfoTile
            label="Turno"
            value={context.activity.preferred_shift ?? "Nao definido"}
            helper={`${context.activity.checkins_30d} check-in(s) em 30 dias`}
          />
          <InfoTile
            label="Sem check-in"
            value={formatDays(context.activity.days_without_checkin)}
            helper={context.activity.last_checkin_at ? `Ultimo: ${formatDateTime(context.activity.last_checkin_at)}` : "Sem historico recente"}
          />
          <InfoTile
            label="Operacao"
            value={`${context.operations.open_tasks_total} task(s) abertas`}
            helper={`${context.operations.overdue_tasks_total} atrasada(s)`}
          />
        </div>

        <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <div className="rounded-2xl border border-lovable-border bg-lovable-surface/80 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Consentimentos</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {consentEntries.map(([key, value]) => {
                const formatted = formatConsent(value);
                return (
                  <Badge key={key} variant={formatted.variant} size="sm">
                    {consentLabels[key]}: {formatted.label}
                  </Badge>
                );
              })}
            </div>
            {context.consent.missing.length > 0 ? (
              <p className="mt-3 text-xs text-lovable-ink-muted">
                Pendente revisar: {context.consent.missing.map((key) => consentLabels[key] ?? key).join(", ")}.
              </p>
            ) : (
              <p className="mt-3 text-xs text-lovable-ink-muted">Base minima de consentimento encontrada no cadastro.</p>
            )}
          </div>

          <div className="rounded-2xl border border-lovable-border bg-lovable-surface/80 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Avaliacao e composicao</p>
            <div className="mt-3 grid gap-2 sm:grid-cols-3">
              <InfoTile label="Avaliacoes" value={`${context.assessment.assessments_total}`} />
              <InfoTile label="Bioimpedancias" value={`${context.assessment.body_composition_total}`} />
              <InfoTile label="% gordura" value={safeValue(context.assessment.latest_body_fat_percent)} />
            </div>
            <p className="mt-3 text-xs text-lovable-ink-muted">
              Massa muscular: {safeValue(context.assessment.latest_muscle_mass_kg)} kg - Peso: {safeValue(context.assessment.latest_weight_kg)} kg.
            </p>
          </div>
        </div>

        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="rounded-2xl border border-lovable-border bg-lovable-surface/80 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Sinais principais</p>
            {context.signals.length > 0 ? (
              <div className="mt-3 grid gap-2">
                {context.signals.slice(0, 5).map((signal) => (
                  <div key={`${signal.key}-${signal.source}`} className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2">
                    <div>
                      <p className="text-sm font-semibold text-lovable-ink">{signal.label}</p>
                      <p className="text-xs text-lovable-ink-muted">
                        Fonte: {signal.source}
                        {signal.observed_at ? ` - ${formatDateTime(signal.observed_at)}` : ""}
                      </p>
                    </div>
                    <Badge variant={severityToBadgeVariant[signal.severity]} size="sm">{safeValue(signal.value)}</Badge>
                  </div>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-lovable-ink-muted">Ainda nao ha sinais integrados suficientes.</p>
            )}
          </div>

          <div className="rounded-2xl border border-lovable-border bg-lovable-surface/80 px-4 py-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Qualidade dos dados</p>
            {context.data_quality_flags.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2">
                {context.data_quality_flags.map((flag) => (
                  <Badge key={flag} variant="warning" size="sm">{flag.split("_").join(" ")}</Badge>
                ))}
              </div>
            ) : (
              <p className="mt-3 text-sm text-lovable-ink-muted">Sem lacunas criticas detectadas para este payload.</p>
            )}
            <p className="mt-3 text-xs text-lovable-ink-muted">
              Ausencias aparecem como flags; o sistema nao inventa origem, consentimento, avaliacao ou bioimpedancia.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
