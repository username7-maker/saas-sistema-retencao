import { useEffect, useRef, useState } from "react";
import { ClipboardList, MessageSquare, Phone, Send, X } from "lucide-react";
import clsx from "clsx";

import { automationService } from "../../services/automationService";
import { crmService } from "../../services/crmService";
import { taskService } from "../../services/taskService";
import type { Lead } from "../../types";

type CallOutcome = "answered" | "no_answer" | "voicemail" | "invalid_number";

const OUTCOME_LABELS: Record<CallOutcome, string> = {
  answered: "Atendeu",
  no_answer: "Nao atendeu",
  voicemail: "Voicemail",
  invalid_number: "Numero invalido",
};

interface QuickLeadActionsProps {
  lead: Lead;
  onActionComplete?: () => void;
}

export function QuickLeadActions({ lead, onActionComplete }: QuickLeadActionsProps) {
  const [sending, setSending] = useState(false);
  const [showWhatsApp, setShowWhatsApp] = useState(false);
  const [showCallLog, setShowCallLog] = useState(false);
  const [callOutcome, setCallOutcome] = useState<CallOutcome | null>(null);
  const [callNote, setCallNote] = useState("");
  const [whatsAppMessage, setWhatsAppMessage] = useState(
    `Ola ${lead.full_name}, tudo bem? Passando para saber se voce ainda tem interesse em conhecer nossos planos da academia.`,
  );
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const dismissRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    setWhatsAppMessage(
      `Ola ${lead.full_name}, tudo bem? Passando para saber se voce ainda tem interesse em conhecer nossos planos da academia.`,
    );
  }, [lead.full_name, lead.id]);

  useEffect(() => {
    if (feedback) {
      if (dismissRef.current) clearTimeout(dismissRef.current);
      dismissRef.current = setTimeout(() => setFeedback(null), 3000);
    }
    return () => {
      if (dismissRef.current) clearTimeout(dismissRef.current);
    };
  }, [feedback]);

  const handleSendWhatsApp = async () => {
    if (!lead.phone) {
      setFeedback({ type: "error", text: "Lead sem telefone cadastrado" });
      return;
    }
    setSending(true);
    try {
      await automationService.sendWhatsApp({ phone: lead.phone, message: whatsAppMessage });
      setFeedback({ type: "success", text: "WhatsApp enviado!" });
      setShowWhatsApp(false);
      onActionComplete?.();
    } catch {
      setFeedback({ type: "error", text: "Falha ao enviar WhatsApp" });
    } finally {
      setSending(false);
    }
  };

  const handleCall = () => {
    if (!lead.phone) {
      setFeedback({ type: "error", text: "Lead sem telefone cadastrado" });
      return;
    }
    try {
      window.location.href = `tel:${lead.phone}`;
    } catch {
      // Desktop fallback.
    }
    setShowCallLog(true);
    setShowWhatsApp(false);
  };

  const handleSubmitCallLog = async () => {
    if (!callOutcome) return;
    setSending(true);
    try {
      const label = OUTCOME_LABELS[callOutcome];
      await crmService.appendLeadNote(lead.id, {
        text: callNote.trim() || `Ligacao registrada com resultado ${label}.`,
        entry_type: "contact_log",
        channel: "phone",
        outcome: callOutcome,
      });
      setFeedback({ type: "success", text: "Ligacao registrada!" });
      setShowCallLog(false);
      setCallOutcome(null);
      setCallNote("");
      onActionComplete?.();
    } catch {
      setFeedback({ type: "error", text: "Falha ao registrar ligacao" });
    } finally {
      setSending(false);
    }
  };

  const handleCreateTask = async () => {
    setSending(true);
    try {
      await taskService.createTask({
        lead_id: lead.id,
        title: `Follow-up com ${lead.full_name}`,
        description: `Lead no estagio ${lead.stage}. Realizar contato comercial.`,
        priority: "high",
        status: "todo",
      });
      setFeedback({ type: "success", text: "Tarefa criada!" });
      onActionComplete?.();
    } catch {
      setFeedback({ type: "error", text: "Falha ao criar tarefa" });
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-1.5">
        <button
          type="button"
          onClick={() => {
            setShowWhatsApp((prev) => !prev);
            setShowCallLog(false);
          }}
          disabled={sending}
          className="flex items-center gap-1 rounded-full bg-lovable-success px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:opacity-90 disabled:opacity-50"
          title="Enviar WhatsApp"
        >
          <MessageSquare size={12} />
          WhatsApp
        </button>
        <button
          type="button"
          onClick={handleCall}
          disabled={sending}
          className="flex items-center gap-1 rounded-full bg-lovable-primary px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:opacity-90 disabled:opacity-50"
          title="Ligar e registrar resultado"
        >
          <Phone size={12} />
          Ligar
        </button>
        <button
          type="button"
          onClick={handleCreateTask}
          disabled={sending}
          className="flex items-center gap-1 rounded-full border border-lovable-border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink hover:border-lovable-border-strong disabled:opacity-50"
          title="Criar Tarefa"
        >
          <ClipboardList size={12} />
          Tarefa
        </button>
      </div>

      {showWhatsApp ? (
        <div className="rounded-lg border border-lovable-border bg-lovable-surface p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold text-lovable-ink">Mensagem WhatsApp</p>
            <button
              type="button"
              aria-label="Fechar"
              onClick={() => setShowWhatsApp(false)}
              className="text-lovable-ink-muted hover:text-lovable-ink"
            >
              <X size={14} />
            </button>
          </div>
          <textarea
            value={whatsAppMessage}
            onChange={(event) => setWhatsAppMessage(event.target.value)}
            rows={3}
            className="w-full rounded-md border border-lovable-border bg-lovable-surface px-2 py-1.5 text-sm text-lovable-ink focus:border-lovable-primary focus:outline-none focus:ring-1 focus:ring-lovable-primary"
          />
          <button
            type="button"
            onClick={handleSendWhatsApp}
            disabled={sending || !whatsAppMessage.trim()}
            className="mt-2 flex items-center gap-1 rounded-full bg-lovable-success px-3 py-1 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            <Send size={12} />
            {sending ? "Enviando..." : "Enviar"}
          </button>
        </div>
      ) : null}

      {showCallLog ? (
        <div className="rounded-lg border border-lovable-border bg-lovable-surface p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold text-lovable-ink">Resultado da ligacao</p>
            <button
              type="button"
              aria-label="Fechar"
              onClick={() => setShowCallLog(false)}
              className="text-lovable-ink-muted hover:text-lovable-ink"
            >
              <X size={14} />
            </button>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {(Object.keys(OUTCOME_LABELS) as CallOutcome[]).map((outcome) => (
              <button
                key={outcome}
                type="button"
                onClick={() => setCallOutcome(outcome)}
                className={clsx(
                  "rounded-full px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider transition-colors",
                  callOutcome === outcome
                    ? "bg-lovable-primary text-white"
                    : "border border-lovable-border text-lovable-ink hover:border-lovable-border-strong",
                )}
              >
                {OUTCOME_LABELS[outcome]}
              </button>
            ))}
          </div>
          <textarea
            value={callNote}
            onChange={(event) => setCallNote(event.target.value)}
            rows={2}
            placeholder="Observacao (opcional)"
            className="mt-2 w-full rounded-md border border-lovable-border bg-lovable-surface px-2 py-1.5 text-sm text-lovable-ink placeholder:text-lovable-ink-muted focus:border-lovable-primary focus:outline-none focus:ring-1 focus:ring-lovable-primary"
          />
          <button
            type="button"
            onClick={handleSubmitCallLog}
            disabled={sending || !callOutcome}
            className="mt-2 flex items-center gap-1 rounded-full bg-lovable-primary px-3 py-1 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            {sending ? "Salvando..." : "Salvar"}
          </button>
        </div>
      ) : null}

      {feedback ? (
        <p
          className={clsx(
            "text-xs font-medium",
            feedback.type === "success" ? "text-lovable-success" : "text-lovable-danger",
          )}
        >
          {feedback.text}
        </p>
      ) : null}
    </div>
  );
}
