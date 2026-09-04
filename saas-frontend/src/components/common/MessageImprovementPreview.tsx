import { useState } from "react";
import { Check, Sparkles, X } from "lucide-react";
import toast from "react-hot-toast";

import { messageComposerService, type MessageComposition } from "../../services/messageComposerService";
import { getHttpErrorDetail } from "../../utils/httpErrors";
import { Badge, Button } from "../ui2";

interface MessageImprovementPreviewProps {
  sourceType: string;
  sourceId: string;
  templateKey: string;
  objective: string;
  baseMessage: string;
  onApplied?: (message: string) => void;
}

export function MessageImprovementPreview({ sourceType, sourceId, templateKey, objective, baseMessage, onApplied }: MessageImprovementPreviewProps) {
  const [preview, setPreview] = useState<MessageComposition | null>(null);
  const [phase, setPhase] = useState<"idle" | "improving" | "applying" | "discarding">("idle");

  async function improve() {
    setPhase("improving");
    try {
      const idempotencyKey = `${sourceType}:${sourceId}:${templateKey}:${crypto.randomUUID()}`;
      setPreview(await messageComposerService.improve({ source_type: sourceType, source_id: sourceId, template_key: templateKey, objective, idempotency_key: idempotencyKey }));
    } catch (error) {
      toast.error(getHttpErrorDetail(error, "Não foi possível melhorar a mensagem. A mensagem pronta foi mantida."));
    } finally {
      setPhase("idle");
    }
  }

  async function apply() {
    if (!preview) return;
    setPhase("applying");
    try {
      const result = await messageComposerService.apply(preview.request_id);
      const message = result.improved_message || result.base_message;
      onApplied?.(message);
      setPreview(null);
      toast.success("Versão melhorada aplicada ao rascunho.");
    } catch (error) {
      toast.error(getHttpErrorDetail(error, "Não foi possível aplicar a versão melhorada."));
    } finally {
      setPhase("idle");
    }
  }

  async function discard() {
    if (!preview) return;
    setPhase("discarding");
    try {
      await messageComposerService.discard(preview.request_id);
      setPreview(null);
      toast.success("Versão descartada. A mensagem pronta foi preservada.");
    } catch (error) {
      toast.error(getHttpErrorDetail(error, "Não foi possível descartar a versão."));
    } finally {
      setPhase("idle");
    }
  }

  if (!preview) {
    return (
      <Button size="sm" variant="secondary" className="mt-3" onClick={() => void improve()} disabled={phase !== "idle" || !baseMessage.trim()}>
        <Sparkles size={14} />
        {phase === "improving" ? "Analisando contexto..." : "Melhorar com IA"}
      </Button>
    );
  }

  return (
    <div className="mt-3 space-y-3 rounded-xl border border-lovable-primary/30 bg-lovable-surface p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-lovable-ink-muted">Comparar versões</p>
        <Badge variant={preview.origin === "ai_improved" ? "success" : "warning"} size="sm">
          {preview.origin === "ai_improved" ? "IA sob demanda" : "Mensagem pronta preservada"}
        </Badge>
      </div>
      <div className="grid gap-2 md:grid-cols-2">
        <div className="rounded-lg border border-lovable-border p-3">
          <p className="mb-2 text-xs font-semibold text-lovable-ink-muted">Mensagem pronta</p>
          <p className="whitespace-pre-wrap text-sm text-lovable-ink">{preview.base_message}</p>
        </div>
        <div className="rounded-lg border border-lovable-primary/30 p-3">
          <p className="mb-2 text-xs font-semibold text-lovable-ink-muted">Versão melhorada</p>
          <p className="whitespace-pre-wrap text-sm text-lovable-ink">{preview.improved_message || preview.base_message}</p>
        </div>
      </div>
      <p className="text-xs text-lovable-ink-muted">Aplicar altera apenas este rascunho e não envia a mensagem.</p>
      <div className="flex flex-wrap gap-2">
        <Button size="sm" variant="primary" onClick={() => void apply()} disabled={phase !== "idle"}>
          <Check size={14} /> Aplicar
        </Button>
        <Button size="sm" variant="secondary" onClick={() => void discard()} disabled={phase !== "idle"}>
          <X size={14} /> Descartar
        </Button>
      </div>
    </div>
  );
}
