import { useEffect, useRef, useState } from "react";
import { ClipboardList, MessageSquare, Phone, Send, X } from "lucide-react";
import clsx from "clsx";

import type { Member } from "../../types";
import { automationService } from "../../services/automationService";
import { dashboardService } from "../../services/dashboardService";
import { taskService } from "../../services/taskService";

type QuickActionMember = Pick<Member, "id" | "full_name" | "phone" | "risk_level" | "risk_score">;

interface QuickActionsProps {
  member: QuickActionMember;
  onActionComplete?: () => void;
}

type CallOutcome = "answered" | "no_answer" | "voicemail" | "invalid_number";

const CALL_OUTCOMES: { value: CallOutcome; label: string }[] = [
  { value: "answered", label: "Atendeu" },
  { value: "no_answer", label: "Não atendeu" },
  { value: "voicemail", label: "Voicemail" },
  { value: "invalid_number", label: "Nº inválido" },
];

function getWhatsAppTemplate(member: QuickActionMember): string {
  if (member.risk_level === "red") {
    return `Olá ${member.full_name}! Notamos que faz um tempo que você não treina conosco. Sua saúde é nossa prioridade — podemos te ajudar a retomar? Estamos disponíveis para conversar!`;
  }
  return `Olá ${member.full_name}! Sentimos sua falta na academia. Que tal retomar os treinos essa semana? Estamos aqui para te apoiar e torcer pela sua evolução!`;
}

export function QuickActions({ member, onActionComplete }: QuickActionsProps) {
  const [sending, setSending] = useState(false);
  const [showWhatsApp, setShowWhatsApp] = useState(false);
  const [showCallModal, setShowCallModal] = useState(false);
  const [whatsAppMessage, setWhatsAppMessage] = useState(() => getWhatsAppTemplate(member));

  // Reset template when member changes (e.g. component reused without remount)
  useEffect(() => {
    setWhatsAppMessage(getWhatsAppTemplate(member));
  }, [member.id]); // eslint-disable-line react-hooks/exhaustive-deps
  const [callOutcome, setCallOutcome] = useState<CallOutcome>("answered");
  const [callNote, setCallNote] = useState("");
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const feedbackTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!feedback) return;
    feedbackTimer.current = setTimeout(() => setFeedback(null), 3000);
    return () => {
      if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    };
  }, [feedback]);

  const setResult = (type: "success" | "error", text: string) => setFeedback({ type, text });

  const handleSendWhatsApp = async () => {
    if (!member.phone) {
      setResult("error", "Aluno sem telefone cadastrado");
      return;
    }
    setSending(true);
    try {
      await automationService.sendWhatsApp({
        phone: member.phone,
        message: whatsAppMessage,
        member_id: member.id,
      });
      setResult("success", "WhatsApp enviado!");
      setShowWhatsApp(false);
      onActionComplete?.();
    } catch {
      setResult("error", "Falha ao enviar WhatsApp");
    } finally {
      setSending(false);
    }
  };

  const handleCreateTask = async () => {
    setSending(true);
    try {
      await taskService.createTask({
        member_id: member.id,
        title: `Contatar ${member.full_name} — Risco ${member.risk_level === "red" ? "Vermelho" : "Amarelo"}`,
        description: `Score: ${member.risk_score}. Entrar em contato para retenção.`,
        priority: member.risk_level === "red" ? "urgent" : "high",
        status: "todo",
      });
      setResult("success", "Tarefa criada!");
      onActionComplete?.();
    } catch {
      setResult("error", "Falha ao criar tarefa");
    } finally {
      setSending(false);
    }
  };

  const handleCall = () => {
    if (!member.phone) {
      setResult("error", "Aluno sem telefone cadastrado");
      return;
    }
    try {
      window.location.href = `tel:${member.phone}`;
    } catch {
      // silently ignored on desktop where tel: is unsupported
    }
    setShowCallModal(true);
  };

  const handleLogCall = async () => {
    setSending(true);
    try {
      await dashboardService.contactLog(member.id, callOutcome, callNote.trim() || undefined);
      setResult("success", "Ligação registrada!");
      setShowCallModal(false);
      setCallNote("");
      onActionComplete?.();
    } catch {
      setResult("error", "Falha ao registrar ligação");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-1.5">
        <button
          type="button"
          onClick={() => setShowWhatsApp((prev) => !prev)}
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
          title="Ligar"
        >
          <Phone size={12} />
          Ligar
        </button>
        <button
          type="button"
          onClick={handleCreateTask}
          disabled={sending}
          className="flex items-center gap-1 rounded-full border border-lovable-border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted hover:border-lovable-border-strong hover:text-lovable-ink disabled:opacity-50"
          title="Criar Tarefa"
        >
          <ClipboardList size={12} />
          Tarefa
        </button>
      </div>

      {/* WhatsApp panel */}
      {showWhatsApp && (
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
            onChange={(e) => setWhatsAppMessage(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-lovable-border bg-lovable-surface px-2 py-1.5 text-sm text-lovable-ink placeholder:text-lovable-ink-muted focus:border-lovable-primary focus:outline-none focus:ring-1 focus:ring-lovable-primary/30"
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
      )}

      {/* Call log panel */}
      {showCallModal && (
        <div className="rounded-lg border border-lovable-border bg-lovable-surface p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold text-lovable-ink">Registrar Ligação</p>
            <button
              type="button"
              aria-label="Fechar"
              onClick={() => setShowCallModal(false)}
              className="text-lovable-ink-muted hover:text-lovable-ink"
            >
              <X size={14} />
            </button>
          </div>
          <div className="mb-2 flex flex-wrap gap-1.5">
            {CALL_OUTCOMES.map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setCallOutcome(opt.value)}
                className={clsx(
                  "rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider transition-colors",
                  callOutcome === opt.value
                    ? "border-lovable-primary bg-lovable-primary/10 text-lovable-primary"
                    : "border-lovable-border text-lovable-ink-muted hover:border-lovable-border-strong hover:text-lovable-ink",
                )}
              >
                {opt.label}
              </button>
            ))}
          </div>
          <textarea
            value={callNote}
            onChange={(e) => setCallNote(e.target.value)}
            rows={2}
            placeholder="Anotação (opcional)"
            className="w-full rounded-md border border-lovable-border bg-lovable-surface px-2 py-1.5 text-sm text-lovable-ink placeholder:text-lovable-ink-muted focus:border-lovable-primary focus:outline-none focus:ring-1 focus:ring-lovable-primary/30"
          />
          <button
            type="button"
            onClick={handleLogCall}
            disabled={sending}
            className="mt-2 flex items-center gap-1 rounded-full bg-lovable-primary px-3 py-1 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-50"
          >
            <Phone size={12} />
            {sending ? "Registrando..." : "Registrar"}
          </button>
        </div>
      )}

      {feedback && (
        <p
          className={clsx(
            "text-xs font-medium",
            feedback.type === "success" ? "text-lovable-success" : "text-lovable-danger",
          )}
        >
          {feedback.text}
        </p>
      )}
    </div>
  );
}
