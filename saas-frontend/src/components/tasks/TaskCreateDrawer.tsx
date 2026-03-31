import { useRef } from "react";

import { Button, Drawer, Input, Select, Textarea } from "../ui2";
import type { CreateTaskPayload } from "../../services/taskService";
import type { Member } from "../../types";
import type { StaffUser } from "../../services/userService";

interface TaskCreateDrawerProps {
  open: boolean;
  onClose: () => void;
  members: Member[];
  users: StaffUser[];
  isPending: boolean;
  onSubmit: (payload: CreateTaskPayload) => void;
}

export function TaskCreateDrawer({ open, onClose, members, users, isPending, onSubmit }: TaskCreateDrawerProps) {
  const formRef = useRef<HTMLFormElement>(null);

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!formRef.current) return;

    const data = new FormData(formRef.current);
    const title = String(data.get("title") ?? "").trim();
    if (!title) return;

    const dueDate = String(data.get("due_date") ?? "").trim();
    const memberId = String(data.get("member_id") ?? "").trim();
    const assignedUserId = String(data.get("assigned_to_user_id") ?? "").trim();
    const description = String(data.get("description") ?? "").trim();

    onSubmit({
      title,
      description: description || undefined,
      member_id: memberId || undefined,
      assigned_to_user_id: assignedUserId || null,
      priority: (String(data.get("priority") ?? "medium") as CreateTaskPayload["priority"]) ?? "medium",
      status: "todo",
      due_date: dueDate ? `${dueDate}T00:00:00Z` : null,
    });
  }

  return (
    <Drawer open={open} onClose={onClose} side="right" title="Nova tarefa">
      <form ref={formRef} onSubmit={handleSubmit} className="space-y-4 p-4">
        <div>
          <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Titulo *</label>
          <Input name="title" required minLength={3} maxLength={160} placeholder="Ex.: Ligar para Ana Silva" />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Descricao</label>
          <Textarea
            name="description"
            rows={4}
            placeholder="Deixe o contexto que o time precisa para executar bem."
          />
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Aluno relacionado</label>
          <Select name="member_id" defaultValue="">
            <option value="">Nenhum</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.full_name}
              </option>
            ))}
          </Select>
        </div>

        <div>
          <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Responsavel</label>
          <Select name="assigned_to_user_id" defaultValue="">
            <option value="">Sem responsavel</option>
            {users.map((user) => (
              <option key={user.id} value={user.id}>
                {user.full_name}
              </option>
            ))}
          </Select>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Prioridade</label>
            <Select name="priority" defaultValue="medium">
              <option value="low">Baixa</option>
              <option value="medium">Media</option>
              <option value="high">Alta</option>
              <option value="urgent">Critica</option>
            </Select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Prazo</label>
            <input
              type="date"
              name="due_date"
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
            Cancelar
          </Button>
          <Button type="submit" variant="primary" size="sm" disabled={isPending}>
            {isPending ? "Salvando..." : "Criar tarefa"}
          </Button>
        </div>
      </form>
    </Drawer>
  );
}
