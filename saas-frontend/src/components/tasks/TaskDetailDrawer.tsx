import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { ArrowRight, CalendarClock, CheckCheck, CircleDashed, ExternalLink, MessageCircle, PhoneCall, UserRound } from "lucide-react";

import { AIAssistantPanel } from "../common/AIAssistantPanel";
import { PreferredShiftBadge } from "../common/PreferredShiftBadge";
import { Badge, Button, Drawer, Input, Select, Textarea } from "../ui2";
import { taskService, type UpdateTaskPayload } from "../../services/taskService";
import type { Member, Task } from "../../types";
import { buildWhatsAppHref, formatPhoneDisplay, normalizeWhatsAppPhone } from "../../utils/whatsapp";
import type { StaffUser } from "../../services/userService";
import {
  PRIORITY_LABELS,
  STATUS_LABELS,
  formatDateTime,
  formatDueDate,
  getAssigneeLabel,
  getPriorityBadgeVariant,
  getStatusBadgeVariant,
  getTaskContextLabel,
  getTaskSourceContext,
} from "./taskUtils";

interface TaskDetailDrawerProps {
  task: Task | null;
  relatedMember: Member | null;
  open: boolean;
  users: StaffUser[];
  userNameById: Map<string, string>;
  isSaving: boolean;
  isDeleting: boolean;
  onClose: () => void;
  onSave: (taskId: string, payload: UpdateTaskPayload) => void;
  onDeleteRequest: (taskId: string) => void;
  onStatusChange: (taskId: string, status: Task["status"]) => void;
  onOpenContext: (task: Task) => void;
}

export function TaskDetailDrawer({
  task,
  relatedMember,
  open,
  users,
  userNameById,
  isSaving,
  isDeleting,
  onClose,
  onSave,
  onDeleteRequest,
  onStatusChange,
  onOpenContext,
}: TaskDetailDrawerProps) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<Task["priority"]>("medium");
  const [status, setStatus] = useState<Task["status"]>("todo");
  const [assignedToUserId, setAssignedToUserId] = useState("");
  const [dueDate, setDueDate] = useState("");

  useEffect(() => {
    if (!task) return;
    setTitle(task.title);
    setDescription(task.description ?? "");
    setPriority(task.priority);
    setStatus(task.status);
    setAssignedToUserId(task.assigned_to_user_id ?? "");
    setDueDate(task.due_date ? task.due_date.slice(0, 10) : "");
  }, [task]);

  const suggestedMessage = useMemo(() => task?.suggested_message?.trim() ?? "", [task]);
  const assistantQuery = useQuery({
    queryKey: ["task-assistant", task?.id],
    queryFn: () => taskService.getAssistant(task!.id),
    enabled: open && Boolean(task?.id),
    staleTime: 60_000,
  });

  if (!task) return null;
  const activeTask = task;
  const normalizedPhone = normalizeWhatsAppPhone(relatedMember?.phone);
  const phoneDisplay = formatPhoneDisplay(relatedMember?.phone);
  const whatsappHref = relatedMember
    ? buildWhatsAppHref(
        relatedMember.phone,
        (assistantQuery.data?.suggested_message ?? suggestedMessage) || null,
        relatedMember.full_name,
      )
    : null;

  function handleSave() {
    onSave(activeTask.id, {
      title: title.trim(),
      description: description.trim() || null,
      priority,
      status,
      due_date: dueDate ? `${dueDate}T00:00:00Z` : null,
      assigned_to_user_id: assignedToUserId || null,
    });
  }

  function renderQuickAction() {
    if (activeTask.status === "todo") {
      return (
        <Button
          size="sm"
          variant="primary"
          disabled={isSaving}
          onClick={() => {
            onStatusChange(activeTask.id, "doing");
            onOpenContext(activeTask);
          }}
        >
          <ArrowRight size={14} />
          Iniciar
        </Button>
      );
    }

    if (activeTask.status === "doing") {
      return (
        <Button size="sm" variant="primary" disabled={isSaving} onClick={() => onStatusChange(activeTask.id, "done")}>
          <CheckCheck size={14} />
          Concluir
        </Button>
      );
    }

    return (
      <Button size="sm" variant="secondary" disabled={isSaving} onClick={() => onOpenContext(activeTask)}>
        <ExternalLink size={14} />
        Abrir contexto
      </Button>
    );
  }

  return (
    <Drawer open={open} onClose={onClose} side="right" title="Detalhe da tarefa">
      <div className="space-y-5 p-4">
        {assistantQuery.data ? (
          <AIAssistantPanel assistant={assistantQuery.data} />
        ) : assistantQuery.isLoading ? (
          <section className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4 text-sm text-lovable-ink-muted">
            Carregando recomendacao da IA...
          </section>
        ) : null}

        <section className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo operacional</p>
              <h3 className="mt-2 text-lg font-bold text-lovable-ink">{task.title}</h3>
              <p className="mt-1 text-sm text-lovable-ink-muted">{getTaskContextLabel(task)} - {getTaskSourceContext(task)}</p>
            </div>
            <div className="flex flex-wrap gap-2">
              <Badge variant={getPriorityBadgeVariant(task.priority)}>{PRIORITY_LABELS[task.priority]}</Badge>
              <Badge variant={getStatusBadgeVariant(task.status)}>{STATUS_LABELS[task.status]}</Badge>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            {renderQuickAction()}
            {(activeTask.member_id || activeTask.lead_id) ? (
              <Button size="sm" variant="ghost" onClick={() => onOpenContext(activeTask)}>
                <ExternalLink size={14} />
                Ver perfil
              </Button>
            ) : null}
            {activeTask.status !== "cancelled" ? (
              <Button size="sm" variant="ghost" disabled={isSaving} onClick={() => onStatusChange(activeTask.id, "cancelled")}>
                Cancelar
              </Button>
            ) : null}
          </div>
        </section>

        <section className="grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl border border-lovable-border p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Contexto</p>
            <div className="mt-3 space-y-3 text-sm text-lovable-ink">
              <div className="flex items-start gap-2">
                <UserRound size={15} className="mt-0.5 text-lovable-ink-muted" />
                <div>
                  <p className="font-medium">Responsavel</p>
                  <p className="text-lovable-ink-muted">{getAssigneeLabel(activeTask, userNameById)}</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CalendarClock size={15} className="mt-0.5 text-lovable-ink-muted" />
                <div>
                  <p className="font-medium">Prazo</p>
                  <p className="text-lovable-ink-muted">{formatDueDate(activeTask.due_date)}</p>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <CircleDashed size={15} className="mt-0.5 text-lovable-ink-muted" />
                <div>
                  <p className="font-medium">Origem</p>
                  <p className="text-lovable-ink-muted">{getTaskSourceContext(activeTask)}</p>
                </div>
              </div>
              {activeTask.member_id ? (
                <div className="flex items-start gap-2">
                  <PhoneCall size={15} className="mt-0.5 text-lovable-ink-muted" />
                  <div className="space-y-2">
                    <div>
                      <p className="font-medium">Contato do aluno</p>
                      <p className="text-lovable-ink-muted">
                        {phoneDisplay ?? "Telefone nao informado"}
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-2">
                        <PreferredShiftBadge preferredShift={activeTask.preferred_shift ?? relatedMember?.preferred_shift} prefix />
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {normalizedPhone && phoneDisplay ? (
                        <a
                          href={`tel:${normalizedPhone}`}
                          className="inline-flex items-center gap-2 rounded-full border border-lovable-border bg-lovable-surface px-3 py-1.5 text-xs font-medium text-lovable-ink transition hover:border-lovable-primary/40 hover:text-lovable-primary"
                        >
                          <PhoneCall size={12} />
                          Ligar
                        </a>
                      ) : null}
                      {whatsappHref ? (
                        <a
                          href={whatsappHref}
                          target="_blank"
                          rel="noreferrer"
                          className="inline-flex items-center gap-2 rounded-full border border-lovable-primary/30 bg-lovable-primary/12 px-3 py-1.5 text-xs font-semibold text-lovable-primary transition hover:bg-lovable-primary/18"
                        >
                          <MessageCircle size={12} />
                          WhatsApp
                        </a>
                      ) : (
                        <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-lovable-border px-3 py-1.5 text-xs text-lovable-ink-muted">
                          <MessageCircle size={12} />
                          WhatsApp indisponivel
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>

          <div className="rounded-2xl border border-lovable-border p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Historico</p>
            <div className="mt-3 space-y-3 text-sm text-lovable-ink-muted">
              <p>Criada em {formatDateTime(activeTask.created_at)}</p>
              <p>Atualizada em {formatDateTime(activeTask.updated_at)}</p>
              <p>Ultima conclusao: {formatDateTime(activeTask.completed_at)}</p>
            </div>
          </div>
        </section>

        <section className="space-y-4 rounded-2xl border border-lovable-border p-4">
          <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Editar tarefa</p>

          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Titulo</label>
            <Input value={title} onChange={(event) => setTitle(event.target.value)} maxLength={160} />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Descricao</label>
            <Textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={4} />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Status</label>
              <Select value={status} onChange={(event) => setStatus(event.target.value as Task["status"])}>
                <option value="todo">A fazer</option>
                <option value="doing">Em andamento</option>
                <option value="done">Concluida</option>
                <option value="cancelled">Cancelada</option>
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Prioridade</label>
              <Select value={priority} onChange={(event) => setPriority(event.target.value as Task["priority"])}>
                <option value="low">Baixa</option>
                <option value="medium">Media</option>
                <option value="high">Alta</option>
                <option value="urgent">Critica</option>
              </Select>
            </div>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Responsavel</label>
              <Select value={assignedToUserId} onChange={(event) => setAssignedToUserId(event.target.value)}>
                <option value="">Sem responsavel</option>
                {users.map((user) => (
                  <option key={user.id} value={user.id}>
                    {user.full_name}
                  </option>
                ))}
              </Select>
            </div>

            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Prazo</label>
              <input
                type="date"
                value={dueDate}
                onChange={(event) => setDueDate(event.target.value)}
                className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
            <Button variant="danger" size="sm" disabled={isDeleting} onClick={() => onDeleteRequest(activeTask.id)}>
              {isDeleting ? "Excluindo..." : "Excluir"}
            </Button>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={onClose}>
                Fechar
              </Button>
              <Button variant="primary" size="sm" disabled={isSaving || !title.trim()} onClick={handleSave}>
                {isSaving ? "Salvando..." : "Salvar alteracoes"}
              </Button>
            </div>
          </div>
        </section>

        {suggestedMessage ? (
          <section className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Mensagem sugerida</p>
            <p className="mt-2 text-sm leading-relaxed text-lovable-ink">{suggestedMessage}</p>
          </section>
        ) : null}
      </div>
    </Drawer>
  );
}
