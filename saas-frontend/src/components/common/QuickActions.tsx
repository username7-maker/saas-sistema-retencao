import { useState } from "react";
import { MessageSquare, Phone, ClipboardList, Send, X } from "lucide-react";
import clsx from "clsx";
import type { Member } from "../../types";
import { api } from "../../services/api";
import { automationService } from "../../services/automationService";

interface QuickActionsProps {
  member: Member;
  onActionComplete?: () => void;
}

export function QuickActions({ member, onActionComplete }: QuickActionsProps) {
  const [sending, setSending] = useState(false);
  const [showWhatsApp, setShowWhatsApp] = useState(false);
  const [whatsAppMessage, setWhatsAppMessage] = useState(
    `Ola ${member.full_name}, tudo bem? Sentimos sua falta na academia. Que tal retomar os treinos esta semana?`
  );
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const handleSendWhatsApp = async () => {
    if (!member.phone) {
      setFeedback({ type: "error", text: "Aluno sem telefone cadastrado" });
      return;
    }
    setSending(true);
    try {
      await automationService.sendWhatsApp({
        phone: member.phone,
        message: whatsAppMessage,
        member_id: member.id,
      });
      setFeedback({ type: "success", text: "WhatsApp enviado!" });
      setShowWhatsApp(false);
      onActionComplete?.();
    } catch {
      setFeedback({ type: "error", text: "Falha ao enviar WhatsApp" });
    } finally {
      setSending(false);
    }
  };

  const handleCreateTask = async () => {
    setSending(true);
    try {
      await api.post("/api/v1/tasks/", {
        member_id: member.id,
        title: `Contatar ${member.full_name} - Risco ${member.risk_level}`,
        description: `Score: ${member.risk_score}. Entrar em contato para retencao.`,
        priority: member.risk_level === "red" ? "urgent" : "high",
        status: "todo",
      });
      setFeedback({ type: "success", text: "Tarefa criada!" });
      setSending(false);
      onActionComplete?.();
    } catch {
      setFeedback({ type: "error", text: "Falha ao criar tarefa" });
    } finally {
      setSending(false);
    }
  };

  const handleCall = () => {
    if (member.phone) {
      window.open(`tel:${member.phone}`, "_self");
    } else {
      setFeedback({ type: "error", text: "Aluno sem telefone cadastrado" });
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex gap-1.5">
        <button
          type="button"
          onClick={() => setShowWhatsApp((prev) => !prev)}
          disabled={sending}
          className="flex items-center gap-1 rounded-full bg-emerald-500 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:bg-emerald-600 disabled:opacity-50"
          title="Enviar WhatsApp"
        >
          <MessageSquare size={12} />
          WhatsApp
        </button>
        <button
          type="button"
          onClick={handleCall}
          disabled={sending}
          className="flex items-center gap-1 rounded-full bg-blue-500 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:bg-blue-600 disabled:opacity-50"
          title="Ligar"
        >
          <Phone size={12} />
          Ligar
        </button>
        <button
          type="button"
          onClick={handleCreateTask}
          disabled={sending}
          className="flex items-center gap-1 rounded-full bg-violet-500 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:bg-violet-600 disabled:opacity-50"
          title="Criar Tarefa"
        >
          <ClipboardList size={12} />
          Tarefa
        </button>
      </div>

      {showWhatsApp && (
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-3">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-xs font-semibold text-emerald-700">Mensagem WhatsApp</p>
            <button type="button" onClick={() => setShowWhatsApp(false)} className="text-slate-400 hover:text-slate-600">
              <X size={14} />
            </button>
          </div>
          <textarea
            value={whatsAppMessage}
            onChange={(e) => setWhatsAppMessage(e.target.value)}
            rows={3}
            className="w-full rounded-md border border-emerald-200 bg-white px-2 py-1.5 text-sm text-slate-700 focus:border-emerald-400 focus:outline-none focus:ring-1 focus:ring-emerald-400"
          />
          <button
            type="button"
            onClick={handleSendWhatsApp}
            disabled={sending || !whatsAppMessage.trim()}
            className="mt-2 flex items-center gap-1 rounded-full bg-emerald-600 px-3 py-1 text-xs font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
          >
            <Send size={12} />
            {sending ? "Enviando..." : "Enviar"}
          </button>
        </div>
      )}

      {feedback && (
        <p
          className={clsx(
            "text-xs font-medium",
            feedback.type === "success" ? "text-emerald-600" : "text-rose-600"
          )}
        >
          {feedback.text}
        </p>
      )}
    </div>
  );
}
