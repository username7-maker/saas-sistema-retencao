import { ArrowUpRight, Copy, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import type { AIAssistantPayload } from "../../types";
import { SectionHeader } from "../ui";
import { Badge, Button, cn } from "../ui2";

interface AIAssistantPanelProps {
  assistant: AIAssistantPayload | null | undefined;
  title?: string;
  subtitle?: string;
  compact?: boolean;
  className?: string;
}

export function AIAssistantPanel({
  assistant,
  title = "IA recomenda",
  subtitle = "Contexto, proxima acao e mensagem sugerida para executar melhor.",
  compact = false,
  className = "",
}: AIAssistantPanelProps) {
  const navigate = useNavigate();
  const assistantData = assistant;

  if (!assistantData) return null;

  async function handleCopyMessage() {
    const message = assistantData?.suggested_message;
    if (!message?.trim()) return;
    try {
      await navigator.clipboard.writeText(message);
      toast.success("Mensagem sugerida copiada.");
    } catch {
      toast.error("Nao foi possivel copiar a mensagem.");
    }
  }

  const providerLabel = formatProviderLabel(assistantData.provider);
  const modeLabel = formatModeLabel(assistantData.mode);
  const transparencyNote = buildTransparencyNote(assistantData);
  const providerBadgeVariant = getProviderBadgeVariant(assistantData.provider);
  const badges = (
    <div className="flex max-w-full flex-wrap items-center gap-2">
      <Badge variant={providerBadgeVariant} size="sm" className="normal-case tracking-normal">
        {providerLabel}
      </Badge>
      <Badge variant="info" size="sm" className="normal-case tracking-normal">
        {assistantData.recommended_channel}
      </Badge>
      <Badge variant="neutral" size="sm" className="normal-case tracking-normal">
        {assistantData.confidence_label}
      </Badge>
      <Badge variant="neutral" size="sm" className="normal-case tracking-normal">
        {modeLabel}
      </Badge>
      {assistantData.fallback_used ? (
        <Badge variant="warning" size="sm" className="normal-case tracking-normal">
          Fallback ativo
        </Badge>
      ) : null}
      {assistantData.manual_required ? (
        <Badge variant="neutral" size="sm" className="normal-case tracking-normal">
          Supervisao humana
        </Badge>
      ) : null}
    </div>
  );

  return (
    <section className={`min-w-0 rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4 ${className}`.trim()}>
      {compact ? (
        <div className="mb-4 space-y-3">
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">{title}</p>
            {subtitle ? <p className="mt-1 text-sm text-lovable-ink-muted">{subtitle}</p> : null}
          </div>
          {badges}
        </div>
      ) : (
        <SectionHeader title={title} subtitle={subtitle} actions={badges} />
      )}

      <div className={compact ? "space-y-3" : "space-y-4"}>
        <div className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
          <div className="flex items-start gap-2">
            <Sparkles size={16} className="mt-0.5 text-lovable-primary" />
            <div>
              <p className="text-sm font-semibold text-lovable-ink">{assistantData.summary}</p>
              <p className="mt-2 text-sm leading-relaxed text-lovable-ink-muted">{assistantData.why_it_matters}</p>
            </div>
          </div>
        </div>

        <div className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Estado operacional</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-lovable-ink">
            <span className="font-medium">Motor:</span>
            <Badge variant={providerBadgeVariant} size="sm" className="normal-case tracking-normal">
              {providerLabel}
            </Badge>
            <span className="font-medium">Modo:</span>
            <Badge variant="neutral" size="sm" className="normal-case tracking-normal">
              {modeLabel}
            </Badge>
          </div>
          <p className="mt-1 text-sm text-lovable-ink-muted">{transparencyNote}</p>
        </div>

        <div className={cn("grid gap-3", compact ? "grid-cols-1" : "md:grid-cols-2")}>
          <article className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Proxima melhor acao</p>
            <p className="mt-2 text-sm font-semibold text-lovable-ink">{assistantData.next_best_action}</p>
          </article>
          <article className="rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Evidencias</p>
            {assistantData.evidence.length > 0 ? (
              <ul className="mt-2 space-y-1.5 text-sm text-lovable-ink-muted">
                {assistantData.evidence.slice(0, compact ? 3 : 5).map((item) => (
                  <li key={item}>- {item}</li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-lovable-ink-muted">Sem evidencias estruturadas adicionais.</p>
            )}
          </article>
        </div>

        {assistantData.suggested_message ? (
          <div className="rounded-xl border border-lovable-primary/20 bg-lovable-primary-soft/40 px-4 py-3">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">Mensagem sugerida</p>
            <p className="mt-2 text-sm leading-relaxed text-lovable-ink">{assistantData.suggested_message}</p>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="primary" onClick={() => navigate(assistantData.cta_target)}>
            <ArrowUpRight size={14} />
            {assistantData.cta_label}
          </Button>
          {assistantData.suggested_message ? (
            <Button size="sm" variant="secondary" onClick={() => void handleCopyMessage()}>
              <Copy size={14} />
              Copiar mensagem
            </Button>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function formatProviderLabel(provider: string | null | undefined): string {
  switch ((provider || "system").trim().toLowerCase()) {
    case "openai":
      return "OpenAI";
    case "claude":
      return "Claude";
    case "system":
      return "Sistema";
    default:
      return "Sistema";
  }
}

function getProviderBadgeVariant(provider: string | null | undefined): "neutral" | "info" {
  switch ((provider || "system").trim().toLowerCase()) {
    case "openai":
    case "claude":
      return "info";
    default:
      return "neutral";
  }
}

function formatModeLabel(mode: string | null | undefined): string {
  switch ((mode || "rule_based").trim().toLowerCase()) {
    case "assisted_summary":
      return "Leitura assistida";
    case "rule_based":
      return "Baseado em regras";
    default:
      return "Baseado em regras";
  }
}

function buildTransparencyNote(assistant: AIAssistantPayload): string {
  if (assistant.fallback_used && assistant.manual_required) {
    return "O sistema esta em fallback e a acao ainda exige supervisao humana.";
  }
  if (assistant.fallback_used) {
    return "O sistema esta em fallback. Revise antes de executar a acao sugerida.";
  }
  if (assistant.manual_required) {
    return "A recomendacao e explicavel, mas a execucao continua supervisionada neste ciclo.";
  }
  return "A recomendacao esta disponivel com o estado atual do motor configurado.";
}
