import { ArrowUpRight, Copy, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import type { AIAssistantPayload } from "../../types";
import { SectionHeader } from "../ui";
import { Badge, Button } from "../ui2";

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

  return (
    <section className={`rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4 ${className}`.trim()}>
      <SectionHeader
        title={title}
        subtitle={subtitle}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="info" size="sm" className="normal-case tracking-normal">
              {assistantData.recommended_channel}
            </Badge>
            <Badge variant="neutral" size="sm" className="normal-case tracking-normal">
              {assistantData.confidence_label}
            </Badge>
          </div>
        }
      />

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

        <div className="grid gap-3 md:grid-cols-2">
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
