import clsx from "clsx";
import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Activity, CheckCircle2, Rocket, Search, X } from "lucide-react";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Input,
  Select,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui2";
import { memberService, type OnboardingScoreResult } from "../../services/memberService";
import { taskService, type CreateTaskPayload } from "../../services/taskService";
import { userService } from "../../services/userService";
import type { Member, Task } from "../../types";

const STATUS_LABELS: Record<Task["status"], string> = {
  todo: "A fazer",
  doing: "Em andamento",
  done: "Concluida",
  cancelled: "Cancelada",
};

const PRIORITY_LABELS: Record<Task["priority"], string> = {
  low: "Baixa",
  medium: "Media",
  high: "Alta",
  urgent: "Urgente",
};

type SourceFilter = "all" | "onboarding" | "plan_followup" | "automation" | "manual";
type PlanFilter = "all" | "mensal" | "semestral" | "anual";
type TopTaskFilter = "all" | "pending" | "overdue";
type WorkspaceTab = "queue" | "onboarding";
type PlaybookKey = "engajado" | "atencao" | "critico";
type FactorKey = keyof OnboardingScoreResult["factors"];

const FACTOR_META: Record<FactorKey, { label: string; weight: number; icon: string }> = {
  checkin_frequency: { label: "Check-ins (catraca)", weight: 30, icon: "🏃" },
  first_assessment: { label: "Avaliacao confirmada", weight: 15, icon: "📊" },
  task_completion: { label: "Tarefas concluidas", weight: 20, icon: "✓" },
  consistency: { label: "Consistencia de horario", weight: 20, icon: "🕐" },
  nps_response: { label: "Resposta a mensagens", weight: 15, icon: "💬" },
};

const PLAYBOOK_CONFIG = {
  engajado: {
    label: "Aluno engajado",
    color: "#0F7553",
    bg: "#E1F5EE",
    border: "#0F755330",
    description: "Score >= 70 - celebrar + NPS antecipado + upsell",
    actions: [
      { day: "D7", badge: "automatico", label: "Mensagem de celebracao", desc: "Claude gera mensagem personalizada comemorando o 1o treino e ancora no objetivo do aluno." },
      { day: "D14", badge: "automatico", label: "NPS antecipado", desc: "Score alto indica promotor em formacao. O NPS entra antes do D30 para capturar o pico de engajamento." },
      { day: "D21", badge: "consultor", label: "Oferta de upsell contextual", desc: "Aluno engajado e com meta clara vira candidato a plano anual com abordagem baseada em progresso." },
      { day: "D30", badge: "automatico", label: "Handoff para retencao", desc: "Score final salvo e onboarding encerrado. O aluno entra no radar recorrente de retencao." },
    ],
  },
  atencao: {
    label: "Aluno em risco",
    color: "#BA7517",
    bg: "#FAEEDA",
    border: "#BA751730",
    description: "Score 40-69 - contato empatico + reagendamento de avaliacao",
    actions: [
      { day: "D3", badge: "automatico", label: "Check-in empatico", desc: "A mensagem investiga o que mudou na rotina sem tom de cobranca." },
      { day: "D7", badge: "consultor", label: "Ligacao de reagendamento", desc: "Consultor prioriza avaliacao pendente com pergunta aberta sobre a semana do aluno." },
      { day: "D14", badge: "automatico", label: "Reforco de objetivo", desc: "A comunicacao lembra o motivo da matricula e reconecta a meta ao habito." },
      { day: "D30", badge: "consultor", label: "Revisao tecnica", desc: "Professor revisa plano e rotina para reduzir barreiras de consistencia." },
    ],
  },
  critico: {
    label: "Aluno sumido",
    color: "#C0392B",
    bg: "#FCEBEB",
    border: "#C0392B30",
    description: "Score < 40 - intervencao humana + bloqueio de automacoes",
    actions: [
      { day: "D1", badge: "urgente", label: "Intervencao humana obrigatoria", desc: "Automacoes param aqui. O risco e cancelar antes do fim do primeiro mes." },
      { day: "D3", badge: "consultor", label: "Ligacao com script contextual", desc: "Script com objetivo, ultimos check-ins e pergunta aberta nao ameacadora." },
      { day: "D7", badge: "gerente", label: "Escalada para gerente", desc: "Se nao houver resposta ate D7, gerente entra diretamente para proteger o LTV do primeiro mes." },
      { day: "D14", badge: "consultor", label: "Proposta de reformulacao", desc: "Ajustar plano ou horario para adequar treino ao contexto real do aluno." },
    ],
  },
} as const;

function taskSource(task: Task): string {
  const src = task.extra_data?.source;
  return typeof src === "string" ? src : "manual";
}

function taskPlanType(task: Task): string {
  const pt = task.extra_data?.plan_type;
  return typeof pt === "string" ? pt : "";
}

function normalizePlanType(val: string | null | undefined): "mensal" | "semestral" | "anual" | null {
  const v = (val ?? "").toLowerCase();
  if (v.includes("anual")) return "anual";
  if (v.includes("semestral")) return "semestral";
  if (v.includes("mensal")) return "mensal";
  return null;
}

function detectPlanFromMember(planName: string | null | undefined): "mensal" | "semestral" | "anual" {
  return normalizePlanType(planName) ?? "mensal";
}

function getTodayKey(): string {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
}

function getDueDateKey(val: string | null): string | null {
  return val && val.length >= 10 ? val.slice(0, 10) : null;
}

function formatDueDate(val: string | null): string {
  const key = getDueDateKey(val);
  if (!key) return "Sem vencimento";
  const [y, m, d] = key.split("-");
  return `${d}/${m}/${y}`;
}

function isOverdue(task: Task, todayKey: string): boolean {
  if (task.status === "done" || task.status === "cancelled") return false;
  const key = getDueDateKey(task.due_date);
  return key !== null && key < todayKey;
}

function isDueTodayOrPast(task: Task, todayKey: string): boolean {
  const key = getDueDateKey(task.due_date);
  if (!key) return true;
  return key <= todayKey;
}

function statusVariant(s: Task["status"]): "neutral" | "success" | "warning" | "danger" {
  if (s === "done") return "success";
  if (s === "doing") return "warning";
  if (s === "cancelled") return "danger";
  return "neutral";
}

function priorityVariant(p: Task["priority"]): "neutral" | "success" | "warning" | "danger" {
  if (p === "urgent") return "danger";
  if (p === "high") return "warning";
  if (p === "low") return "success";
  return "neutral";
}

function formatPlanLabel(planType: string): string {
  if (!planType) return "Mensal";
  return planType.charAt(0).toUpperCase() + planType.slice(1);
}

async function listAllMembers(): Promise<Member[]> {
  const PAGE = 100;
  const first = await memberService.listMembers({ page: 1, page_size: PAGE });
  const pages = Math.ceil(first.total / PAGE);
  if (pages <= 1) return first.items;
  const rest = await Promise.all(
    Array.from({ length: pages - 1 }, (_, i) =>
      memberService.listMembers({ page: i + 2, page_size: PAGE }).then((r) => r.items),
    ),
  );
  return [...first.items, ...rest.flat()];
}

interface TaskGroup {
  key: string;
  label: string;
  memberId: string | null;
  leadId: string | null;
  planType: "mensal" | "semestral" | "anual" | null;
  tasks: Task[];
  todoCount: number;
  doingCount: number;
  doneCount: number;
}

interface CreateModalProps {
  members: Member[];
  onClose: () => void;
  onSubmit: (payload: CreateTaskPayload) => void;
  isPending: boolean;
}

function CreateTaskModal({ members, onClose, onSubmit, isPending }: CreateModalProps) {
  const formRef = useRef<HTMLFormElement>(null);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!formRef.current) return;
    const fd = new FormData(formRef.current);
    const title = (fd.get("title") as string).trim();
    if (!title) return;
    const memberId = (fd.get("member_id") as string) || undefined;
    const description = (fd.get("description") as string).trim() || undefined;
    const priority = (fd.get("priority") as Task["priority"]) || "medium";
    const dueDate = (fd.get("due_date") as string) || undefined;
    onSubmit({
      title,
      description,
      member_id: memberId,
      priority,
      status: "todo",
      due_date: dueDate ? `${dueDate}T00:00:00Z` : null,
    });
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-2xl border border-lovable-border bg-lovable-surface p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="mb-4 text-lg font-bold text-lovable-ink">Nova Tarefa</h3>
        <form ref={formRef} onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Titulo *</label>
            <Input name="title" required minLength={3} maxLength={160} placeholder="Titulo da tarefa" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Descricao</label>
            <textarea
              name="description"
              rows={2}
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink placeholder:text-lovable-ink-muted focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              placeholder="Detalhes da tarefa (opcional)"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Aluno</label>
            <select
              name="member_id"
              className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
            >
              <option value="">Nenhum</option>
              {members.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.full_name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Prioridade</label>
              <select
                name="priority"
                defaultValue="medium"
                className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              >
                <option value="low">Baixa</option>
                <option value="medium">Media</option>
                <option value="high">Alta</option>
                <option value="urgent">Urgente</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-lovable-ink-muted">Vencimento</label>
              <input
                type="date"
                name="due_date"
                className="w-full rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2 text-sm text-lovable-ink focus:outline-none focus:ring-2 focus:ring-lovable-primary"
              />
            </div>
          </div>
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={isPending}>
              Cancelar
            </Button>
            <Button type="submit" variant="primary" size="sm" disabled={isPending}>
              {isPending ? "Salvando..." : "Criar tarefa"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

function isOnboardingActiveMember(member: Member): boolean {
  return member.status === "active" && (member.onboarding_status === "active" || member.onboarding_status === "at_risk");
}

function memberToPlaybook(member: Member): PlaybookKey {
  const score = member.onboarding_score ?? 0;
  if (score >= 70) return "engajado";
  if (score >= 40) return "atencao";
  return "critico";
}

function scoreBarColor(score: number): string {
  if (score >= 70) return "bg-[#0F7553]";
  if (score >= 40) return "bg-[#BA7517]";
  return "bg-[#C0392B]";
}

function badgeClass(badge: string): string {
  if (badge === "urgente") return "bg-red-100 text-red-700";
  if (badge === "gerente") return "bg-purple-100 text-purple-700";
  if (badge === "consultor") return "bg-blue-100 text-blue-700";
  return "bg-green-100 text-green-700";
}

function OnboardingScorePanel({ member }: { member: Member }) {
  const scoreQuery = useQuery({
    queryKey: ["onboarding-score", member.id],
    queryFn: () => memberService.getOnboardingScore(member.id),
    staleTime: 60_000,
  });

  if (scoreQuery.isLoading) {
    return (
      <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-8 text-center">
        <div className="animate-pulse text-sm text-lovable-ink-muted">Calculando score...</div>
      </div>
    );
  }

  if (scoreQuery.isError || !scoreQuery.data) {
    return (
      <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-6 text-center">
        <p className="text-sm text-lovable-ink-muted">Nao foi possivel carregar o score detalhado.</p>
        <p className="mt-1 text-xs text-lovable-ink-muted">Score resumido: {member.onboarding_score ?? "—"}</p>
      </div>
    );
  }

  const score = scoreQuery.data;
  const playbookKey: PlaybookKey = score.score >= 70 ? "engajado" : score.score >= 40 ? "atencao" : "critico";
  const playbook = PLAYBOOK_CONFIG[playbookKey];
  const factorEntries = Object.entries(FACTOR_META) as Array<[FactorKey, (typeof FACTOR_META)[FactorKey]]>;

  return (
    <div className="space-y-4">
      <div className="rounded-2xl border p-5" style={{ background: playbook.bg, borderColor: playbook.border }}>
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-wider opacity-70" style={{ color: playbook.color }}>
              Onboarding Score - primeiros {score.days_since_join} dias
            </p>
            <p className="mt-1 text-3xl font-bold" style={{ color: playbook.color }}>
              {score.score}
            </p>
            <p className="mt-2 text-xs opacity-80" style={{ color: playbook.color }}>
              Resumo da lista: {member.onboarding_score ?? "—"}
            </p>
          </div>
          <div className="text-right">
            <span
              className="rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide"
              style={{ background: `${playbook.color}20`, color: playbook.color }}
            >
              {playbook.label}
            </span>
            <p className="mt-1 text-[11px] opacity-70" style={{ color: playbook.color }}>
              {playbook.description}
            </p>
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Score por fator</p>
        <div className="space-y-3">
          {factorEntries.map(([key, meta]) => {
            const value = score.factors[key] ?? 0;
            return (
              <div key={key}>
                <div className="mb-1 flex items-center justify-between">
                  <span className="text-xs text-lovable-ink">
                    {meta.icon} {meta.label}
                    <span className="ml-1.5 text-[10px] text-lovable-ink-muted">({meta.weight}%)</span>
                  </span>
                  <span className="text-xs font-bold text-lovable-ink">{value}%</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-lovable-border">
                  <div className={clsx("h-2 rounded-full transition-all", scoreBarColor(value))} style={{ width: `${value}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">
          Sinais captados automaticamente
        </p>
        <div className="space-y-2">
          {[
            { ok: score.checkin_count >= 3, text: `${score.checkin_count} check-ins nos primeiros ${score.days_since_join} dias`, source: "catraca" },
            {
              ok: score.factors.first_assessment === 100,
              text: score.factors.first_assessment === 100 ? "Avaliacao fisica realizada" : "Avaliacao fisica ainda nao realizada",
              source: "avaliacao",
            },
            {
              ok: score.factors.nps_response === 100,
              text: score.factors.nps_response === 100 ? "Respondeu a mensagem de acompanhamento" : "Ainda nao respondeu a mensagem",
              source: "WhatsApp",
            },
            {
              ok: score.factors.consistency >= 70,
              text: score.factors.consistency >= 70 ? "Horario consistente - padrao estavel" : "Horario variavel - rotina instavel",
              source: "padrao horario",
            },
            {
              ok: score.completed_tasks === score.total_tasks && score.total_tasks > 0,
              text: `${score.completed_tasks}/${score.total_tasks} tarefas concluidas`,
              source: "tarefas",
            },
          ].map((signal, index) => (
            <div key={index} className="flex items-start gap-2.5">
              <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full" style={{ background: signal.ok ? "#0F7553" : "#E24B4A" }} />
              <span className="flex-1 text-xs text-lovable-ink">{signal.text}</span>
              <span className="shrink-0 rounded-full bg-lovable-surface-soft px-2 py-0.5 text-[10px] font-medium text-lovable-ink-muted">
                {signal.source}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-2xl border bg-lovable-surface" style={{ borderColor: playbook.border }}>
        <div className="border-b px-4 py-3" style={{ background: playbook.bg, borderColor: playbook.border }}>
          <p className="text-[10px] font-semibold uppercase tracking-wider" style={{ color: playbook.color }}>
            Playbook adaptativo gerado para este perfil
          </p>
        </div>
        <div className="divide-y divide-lovable-border">
          {playbook.actions.map((action, index) => (
            <div key={index} className="flex gap-3 p-4">
              <div className="flex shrink-0 flex-col items-center gap-1">
                <span className="rounded-full px-2 py-0.5 text-[10px] font-bold" style={{ background: playbook.bg, color: playbook.color }}>
                  {action.day}
                </span>
                {index < playbook.actions.length - 1 ? <div className="min-h-4 w-px flex-1" style={{ background: playbook.border }} /> : null}
              </div>
              <div className="min-w-0 flex-1">
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold text-lovable-ink">{action.label}</p>
                  <span className={clsx("shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide", badgeClass(action.badge))}>
                    {action.badge}
                  </span>
                </div>
                <p className="text-xs leading-relaxed text-lovable-ink-muted">{action.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function TasksPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [workspaceTab, setWorkspaceTab] = useState<WorkspaceTab>("queue");
  const [activePlaybook, setActivePlaybook] = useState<PlaybookKey>("atencao");
  const [selectedOnboardingMemberId, setSelectedOnboardingMemberId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [showDone, setShowDone] = useState(false);
  const [topFilter, setTopFilter] = useState<TopTaskFilter>("all");
  const [planFilter, setPlanFilter] = useState<PlanFilter>("all");
  const [sourceFilter, setSourceFilter] = useState<SourceFilter>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
  const tasksQuery = useQuery({
    queryKey: ["tasks"],
    queryFn: taskService.listTasks,
    staleTime: 5 * 60 * 1000,
  });

  const membersQuery = useQuery({
    queryKey: ["members", "all-index"],
    queryFn: listAllMembers,
    staleTime: 10 * 60 * 1000,
  });

  const usersQuery = useQuery({
    queryKey: ["users"],
    queryFn: userService.listUsers,
    staleTime: 15 * 60 * 1000,
  });
  const updateMutation = useMutation({
    mutationFn: ({ taskId, status }: { taskId: string; status: Task["status"] }) =>
      taskService.updateTask(taskId, { status }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["tasks"] }),
    onError: () => toast.error("Erro ao atualizar tarefa."),
  });

  const deleteMutation = useMutation({
    mutationFn: (taskId: string) => taskService.deleteTask(taskId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setPendingDeleteId(null);
      toast.success("Tarefa excluída.");
    },
    onError: () => toast.error("Erro ao excluir tarefa."),
  });

  const createMutation = useMutation({
    mutationFn: (payload: CreateTaskPayload) => taskService.createTask(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setCreateOpen(false);
      toast.success("Tarefa criada.");
    },
    onError: () => toast.error("Erro ao criar tarefa."),
  });
  const memberPlanById = useMemo(() => {
    const map = new Map<string, "mensal" | "semestral" | "anual">();
    for (const m of membersQuery.data ?? []) {
      map.set(m.id, detectPlanFromMember(m.plan_name));
    }
    return map;
  }, [membersQuery.data]);

  const userNameById = useMemo(() => {
    const map = new Map<string, string>();
    for (const u of usersQuery.data ?? []) {
      map.set(u.id, u.full_name);
    }
    return map;
  }, [usersQuery.data]);

  const allTasks = tasksQuery.data?.items ?? [];
  const todayKey = useMemo(() => getTodayKey(), []);
  const onboardingMembers = useMemo(
    () => (membersQuery.data ?? []).filter((member) => isOnboardingActiveMember(member)),
    [membersQuery.data],
  );
  const onboardingGroups = useMemo<Record<PlaybookKey, Member[]>>(
    () => ({
      engajado: onboardingMembers.filter((member) => memberToPlaybook(member) === "engajado"),
      atencao: onboardingMembers.filter((member) => memberToPlaybook(member) === "atencao"),
      critico: onboardingMembers.filter((member) => memberToPlaybook(member) === "critico"),
    }),
    [onboardingMembers],
  );
  const activeOnboardingMembers = onboardingGroups[activePlaybook];
  const effectiveOnboardingMemberId = selectedOnboardingMemberId ?? activeOnboardingMembers[0]?.id ?? null;
  const selectedOnboardingMember = activeOnboardingMembers.find((member) => member.id === effectiveOnboardingMemberId) ?? null;
  const onboardingTaskStats = useMemo(() => {
    const onboardingTasks = allTasks.filter((task) => taskSource(task) === "onboarding");
    return {
      total: onboardingTasks.length,
      pending: onboardingTasks.filter((task) => task.status !== "done" && task.status !== "cancelled").length,
      overdue: onboardingTasks.filter((task) => isOverdue(task, todayKey)).length,
    };
  }, [allTasks, todayKey]);
  const focuoStats = useMemo(() => {
    const urgentCount = allTasks.filter(
      (task) => task.priority === "urgent" && task.status !== "done" && task.status !== "cancelled",
    ).length;
    const completedToday = allTasks.filter((task) => {
      if (task.status !== "done") return false;
      return typeof task.updated_at === "string" && task.updated_at.startsWith(todayKey);
    }).length;
    return { urgentCount, completedToday };
  }, [allTasks, todayKey]);

  const pendingDeleteTask = useMemo(
    () => (pendingDeleteId ? allTasks.find((t) => t.id === pendingDeleteId) : null),
    [pendingDeleteId, allTasks],
  );

  useEffect(() => {
    if (onboardingMembers.length === 0 || activeOnboardingMembers.length > 0) return;
    const firstAvailable = (["atencao", "critico", "engajado"] as PlaybookKey[]).find(
      (key) => onboardingGroups[key].length > 0,
    );
    if (firstAvailable && firstAvailable !== activePlaybook) {
      setActivePlaybook(firstAvailable);
      setSelectedOnboardingMemberId(null);
    }
  }, [activeOnboardingMembers.length, activePlaybook, onboardingGroups, onboardingMembers.length]);

  const hiddenFutureCount = useMemo(
    () => allTasks.filter((t) => !isDueTodayOrPast(t, todayKey)).length,
    [allTasks, todayKey],
  );

  const filtered = useMemo(() => {
    let list = allTasks.filter((t) => isDueTodayOrPast(t, todayKey));
    if (!showDone) list = list.filter((t) => t.status !== "done");
    if (topFilter === "pending") list = list.filter((t) => t.status !== "done" && t.status !== "cancelled");
    if (topFilter === "overdue") list = list.filter((t) => isOverdue(t, todayKey));
    if (sourceFilter !== "all") list = list.filter((t) => taskSource(t) === sourceFilter);
    return list;
  }, [allTasks, showDone, sourceFilter, todayKey, topFilter]);

  const groups = useMemo(() => {
    const draft = new Map<string, TaskGroup>();

    for (const task of filtered) {
      const key = task.member_id ? `member:${task.member_id}` : task.lead_id ? `lead:${task.lead_id}` : "unlinked";

      const label =
        task.member_name ??
        task.lead_name ??
        (task.member_id ? `Aluno ${task.member_id.slice(0, 8)}` : task.lead_id ? "Lead (CRM)" : "Sem vinculo");

      const current = draft.get(key) ?? {
        key,
        label,
        memberId: task.member_id,
        leadId: task.lead_id,
        planType: task.member_id
          ? (memberPlanById.get(task.member_id) ?? normalizePlanType(taskPlanType(task)))
          : normalizePlanType(taskPlanType(task)),
        tasks: [],
        todoCount: 0,
        doingCount: 0,
        doneCount: 0,
      };

      current.tasks.push(task);
      if (task.status === "todo") current.todoCount += 1;
      if (task.status === "doing") current.doingCount += 1;
      if (task.status === "done") current.doneCount += 1;
      draft.set(key, current);
    }

    const normalizedSearch = search.trim().toLowerCase();

    return [...draft.values()]
      .map((g) => ({
        ...g,
        tasks: [...g.tasks].sort((a, b) => {
          const aDue = a.due_date ? new Date(a.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          const bDue = b.due_date ? new Date(b.due_date).getTime() : Number.MAX_SAFE_INTEGER;
          return aDue - bDue;
        }),
      }))
      .filter((g) => {
        if (planFilter !== "all" && g.planType !== planFilter) return false;
        if (!normalizedSearch) return true;
        if (g.label.toLowerCase().includes(normalizedSearch)) return true;
        return g.tasks.some((t) => t.title.toLowerCase().includes(normalizedSearch));
      })
      .sort((a, b) => {
        const pendA = a.todoCount + a.doingCount;
        const pendB = b.todoCount + b.doingCount;
        if (pendA !== pendB) return pendB - pendA;
        return a.label.localeCompare(b.label);
      });
  }, [filtered, memberPlanById, planFilter, search]);
  function groupDestination(group: TaskGroup): string {
    if (group.memberId) return `/assessments/members/${group.memberId}`;
    return "/crm";
  }
  if (tasksQuery.isLoading) return <LoadingPanel text="Carregando tarefas..." />;
  if (tasksQuery.isError) return <LoadingPanel text="Erro ao carregar tarefas. Tente novamente." />;

  const totalTasks = allTasks.length;
  const pendingTasks = allTasks.filter((t) => t.status !== "done" && t.status !== "cancelled").length;
  const overdueTasks = allTasks.filter((t) => isOverdue(t, todayKey)).length;
  const topFilterLabel =
    topFilter === "pending" ? "Filtrando: pendentes" : topFilter === "overdue" ? "Filtrando: atrasadas" : null;

  const openOnboardingQueue = () => {
    setSourceFilter("onboarding");
    setWorkspaceTab("queue");
  };

  return (
    <>
      <Tabs
        value={workspaceTab}
        onValueChange={(value) => setWorkspaceTab(value as WorkspaceTab)}
        className="space-y-6"
      >
        <section className="space-y-6">
          <header className="space-y-4">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <div>
                <h2 className="font-heading text-3xl font-bold text-lovable-ink">Tarefas</h2>
                <p className="text-sm text-lovable-ink-muted">
                  Operacao diaria e onboarding no mesmo modulo, organizados em visoes separadas.
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <TabsList className="w-full sm:w-auto">
                  <TabsTrigger value="queue" className="min-w-[150px]">
                    Fila operacional
                  </TabsTrigger>
                  <TabsTrigger value="onboarding" className="min-w-[150px]">
                    Onboarding
                  </TabsTrigger>
                </TabsList>
                {workspaceTab === "queue" ? (
                  <Button variant="primary" size="sm" onClick={() => setCreateOpen(true)}>
                    + Nova Tarefa
                  </Button>
                ) : (
                  <Button variant="secondary" size="sm" onClick={openOnboardingQueue}>
                    Ver tasks de onboarding
                  </Button>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="rounded-full"
                onClick={() => {
                  setWorkspaceTab("queue");
                  setTopFilter("all");
                }}
              >
                <Badge
                  variant="neutral"
                  className={
                    workspaceTab === "queue" && topFilter === "all"
                      ? "ring-2 ring-lovable-primary/40"
                      : "opacity-80 hover:opacity-100"
                  }
                >
                  Total: {totalTasks}
                </Badge>
              </button>
              <button
                type="button"
                className="rounded-full"
                onClick={() => {
                  setWorkspaceTab("queue");
                  setTopFilter((prev) => (prev === "pending" ? "all" : "pending"));
                }}
              >
                <Badge
                  variant="warning"
                  className={
                    workspaceTab === "queue" && topFilter === "pending"
                      ? "ring-2 ring-lovable-warning/50"
                      : "opacity-80 hover:opacity-100"
                  }
                >
                  Pendentes: {pendingTasks}
                </Badge>
              </button>
              {overdueTasks > 0 ? (
                <button
                  type="button"
                  className="rounded-full"
                  onClick={() => {
                    setWorkspaceTab("queue");
                    setTopFilter((prev) => (prev === "overdue" ? "all" : "overdue"));
                  }}
                >
                  <Badge
                    variant="danger"
                    className={
                      workspaceTab === "queue" && topFilter === "overdue"
                        ? "ring-2 ring-lovable-danger/50"
                        : "opacity-80 hover:opacity-100"
                    }
                  >
                    Atrasadas: {overdueTasks}
                  </Badge>
                </button>
              ) : null}
              <button type="button" className="rounded-full" onClick={() => setWorkspaceTab("onboarding")}>
                <Badge
                  variant="neutral"
                  className={workspaceTab === "onboarding" ? "ring-2 ring-lovable-primary/40" : "opacity-80 hover:opacity-100"}
                >
                  Onboarding ativo: {onboardingMembers.length}
                </Badge>
              </button>
              {hiddenFutureCount > 0 ? <Badge variant="neutral">Futuras ocultas: {hiddenFutureCount}</Badge> : null}
            </div>
          </header>

          <TabsContent value="onboarding" className="space-y-4">
            <Card>
              <CardContent className="flex flex-col gap-3 p-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">Painel de onboarding</p>
                  <p className="text-sm text-lovable-ink-muted">
                    Score, playbooks e selecao do aluno ficam aqui. A execucao das tasks continua na fila operacional.
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Badge variant="neutral">Alunos ativos: {onboardingMembers.length}</Badge>
                  <Badge variant="warning">Tasks onboarding: {onboardingTaskStats.pending}</Badge>
                  {onboardingTaskStats.overdue > 0 ? (
                    <Badge variant="danger">Atrasadas: {onboardingTaskStats.overdue}</Badge>
                  ) : null}
                  <Button variant="ghost" size="sm" onClick={openOnboardingQueue}>
                    Abrir fila filtrada
                  </Button>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <Rocket size={18} className="text-lovable-primary" />
                    Onboarding Intelligence
                  </CardTitle>
                  <p className="mt-1 text-sm text-lovable-ink-muted">
                    Leitura organizada por playbook, com selecao do aluno e score detalhado.
                  </p>
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-0">
              {membersQuery.isLoading ? (
                <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-6 text-center text-sm text-lovable-ink-muted">
                  Carregando painel de onboarding...
                </div>
              ) : membersQuery.isError ? (
                <div className="rounded-2xl border border-lovable-danger/30 bg-lovable-danger/5 p-6 text-center text-sm text-lovable-danger">
                  Nao foi possivel carregar os membros de onboarding.
                </div>
              ) : onboardingMembers.length === 0 ? (
                <div className="rounded-2xl border border-dashed border-lovable-border p-6 text-center">
                  <CheckCircle2 size={24} className="mx-auto mb-2 text-lovable-ink-muted/30" />
                  <p className="text-sm text-lovable-ink-muted">Nao ha alunos em onboarding ativo no momento.</p>
                </div>
              ) : (
                <>
                  <div className="grid gap-3 md:grid-cols-3">
                    {(Object.entries(PLAYBOOK_CONFIG) as Array<[PlaybookKey, (typeof PLAYBOOK_CONFIG)[PlaybookKey]]>).map(([key, config]) => {
                      const isActive = activePlaybook === key;
                      const count = onboardingGroups[key].length;
                      return (
                        <button
                          key={key}
                          type="button"
                          onClick={() => {
                            setActivePlaybook(key);
                            setSelectedOnboardingMemberId(null);
                          }}
                          className={clsx(
                            "rounded-2xl border p-4 text-left transition-all",
                            isActive ? "border-2 shadow-sm" : "border-lovable-border bg-lovable-surface hover:border-lovable-ink/20",
                          )}
                          style={isActive ? { borderColor: config.color, background: config.bg } : undefined}
                        >
                          <p className="text-2xl font-bold" style={{ color: config.color }}>
                            {count}
                          </p>
                          <p className="mt-1 text-sm font-semibold text-lovable-ink">{config.label}</p>
                          <p className="mt-0.5 text-xs leading-relaxed text-lovable-ink-muted">{config.description}</p>
                        </button>
                      );
                    })}
                  </div>

                  <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
                    <div className="max-h-[560px] space-y-2 overflow-y-auto pr-1">
                      <p className="px-0.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">
                        {activeOnboardingMembers.length} aluno{activeOnboardingMembers.length !== 1 ? "s" : ""} neste playbook
                      </p>
                      {activeOnboardingMembers.length === 0 ? (
                        <div className="rounded-2xl border border-dashed border-lovable-border p-6 text-center">
                          <Activity size={24} className="mx-auto mb-2 text-lovable-ink-muted/30" />
                          <p className="text-sm text-lovable-ink-muted">Nenhum aluno neste grupo.</p>
                        </div>
                      ) : (
                        activeOnboardingMembers.map((member) => {
                          const config = PLAYBOOK_CONFIG[activePlaybook];
                          const isSelected = effectiveOnboardingMemberId === member.id;
                          return (
                            <button
                              key={member.id}
                              type="button"
                              onClick={() => setSelectedOnboardingMemberId(member.id)}
                              className={clsx(
                                "w-full rounded-2xl border p-3 text-left transition-all",
                                isSelected ? "border-2 shadow-sm" : "border-lovable-border bg-lovable-surface hover:border-lovable-ink/20",
                              )}
                              style={isSelected ? { borderColor: config.color, background: config.bg } : undefined}
                            >
                              <div className="flex items-center justify-between gap-2">
                                <p className="truncate text-sm font-semibold text-lovable-ink">{member.full_name}</p>
                                <span className="shrink-0 text-sm font-bold" style={{ color: config.color }}>
                                  {member.onboarding_score ?? "--"}
                                </span>
                              </div>
                              <p className="mt-0.5 text-xs text-lovable-ink-muted">{member.plan_name}</p>
                            </button>
                          );
                        })
                      )}
                    </div>

                    <div className="lg:sticky lg:top-4">
                      {selectedOnboardingMember ? (
                        <OnboardingScorePanel member={selectedOnboardingMember} />
                      ) : (
                        <div className="rounded-2xl border border-dashed border-lovable-border p-12 text-center">
                          <Activity size={32} className="mx-auto mb-3 text-lovable-ink-muted/30" />
                          <p className="text-sm text-lovable-ink-muted">Selecione um aluno para ver o score detalhado.</p>
                        </div>
                      )}
                    </div>
                  </div>
                </>
              )}
            </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="queue" className="space-y-4">
            <Card>
              <CardContent className="space-y-4 p-4">
                <div className="flex flex-wrap items-center gap-2">
                  <Button variant={showDone ? "secondary" : "ghost"} size="sm" onClick={() => setShowDone((p) => !p)}>
                    {showDone ? "Ocultar concluidas" : "Mostrar concluidas"}
                  </Button>
                  {topFilterLabel ? <Badge variant="warning">{topFilterLabel}</Badge> : null}
                  {sourceFilter === "onboarding" ? <Badge variant="neutral">Fila filtrada por onboarding</Badge> : null}
                </div>

                <div className="flex flex-wrap items-center gap-2">
                  <div className="flex min-w-[260px] flex-1 items-center gap-2">
                    <Input
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      placeholder="Buscar por nome do aluno ou titulo da tarefa..."
                      className="flex-1"
                    />
                    <Button variant="primary" size="sm" onClick={() => setSearch((prev) => prev.trim())}>
                      <Search size={14} />
                    </Button>
                    {search ? (
                      <Button variant="ghost" size="sm" onClick={() => setSearch("")}>
                        <X size={14} />
                      </Button>
                    ) : null}
                  </div>

                  <div className="w-full md:w-56">
                    <Select value={sourceFilter} onChange={(event) => setSourceFilter(event.target.value as SourceFilter)}>
                      <option value="all">Todas</option>
                      <option value="onboarding">Onboarding</option>
                      <option value="plan_followup">Follow-up</option>
                      <option value="automation">Automacao</option>
                      <option value="manual">Manual</option>
                    </Select>
                  </div>

                  <div className="w-full md:w-56">
                    <Select value={planFilter} onChange={(event) => setPlanFilter(event.target.value as PlanFilter)}>
                      <option value="all">Todos planos</option>
                      <option value="mensal">Mensal</option>
                      <option value="semestral">Semestral</option>
                      <option value="anual">Anual</option>
                    </Select>
                  </div>
                </div>
              </CardContent>
            </Card>

            {(focuoStats.urgentCount > 0 || overdueTasks > 0) && (
          <div className="flex items-center justify-between gap-3 rounded-2xl border border-lovable-danger/30 bg-lovable-danger/5 px-4 py-3">
            <div>
              <p className="text-sm font-semibold text-lovable-danger">
                Foco agora: {focuoStats.urgentCount} urgente{focuoStats.urgentCount !== 1 ? "s" : ""} - {overdueTasks} atrasada{overdueTasks !== 1 ? "s" : ""}
              </p>
              <p className="mt-0.5 text-xs text-lovable-ink-muted">
                Resolva as urgentes primeiro - elas tem maior impacto na retencao.
              </p>
            </div>
            <span className="shrink-0 whitespace-nowrap text-xs font-semibold text-lovable-ink-muted">
              {focuoStats.completedToday} concluida{focuoStats.completedToday !== 1 ? "s" : ""} hoje
            </span>
          </div>
        )}
        {groups.length === 0 ? (
          <Card>
            <CardContent className="py-10 text-center text-sm text-lovable-ink-muted">
              Nenhuma tarefa encontrada para os filtros atuais.
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-4">
            {groups.map((group) => {
              const total = group.todoCount + group.doingCount + group.doneCount;
              const progress = total > 0 ? Math.round((group.doneCount / total) * 100) : 0;

              return (
                <Card key={group.key}>
                  <CardHeader className="pb-3">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 flex-1">
                        <CardTitle className="flex items-center gap-2">
                          {group.label}
                          {group.planType ? (
                            <Badge variant="neutral">{formatPlanLabel(group.planType)}</Badge>
                          ) : null}
                          {group.todoCount + group.doingCount >= 5 ? (
                            <span className="rounded-full border border-lovable-warning/20 bg-lovable-warning/10 px-2 py-0.5 text-[10px] font-semibold text-lovable-warning">
                                {group.todoCount + group.doingCount} tarefas abertas
                            </span>
                          ) : null}
                        </CardTitle>
                        <p className="mt-1 text-xs text-lovable-ink-muted">
                          {group.tasks.length} tarefa{group.tasks.length !== 1 ? "s" : ""} - {group.todoCount} a
                          fazer - {group.doingCount} em andamento - {group.doneCount} concluida
                          {group.doneCount !== 1 ? "s" : ""}
                        </p>
                        <div className="mt-2 h-1.5 w-full max-w-xs rounded-full bg-lovable-border">
                          <div
                            className="h-full rounded-full bg-lovable-success transition-all"
                            style={{ width: `${progress}%` }}
                          />
                        </div>
                        <p className="mt-0.5 text-xs text-lovable-ink-muted">{progress}% concluido</p>
                      </div>
                      <Button variant="secondary" size="sm" onClick={() => navigate(groupDestination(group))}>
                        Ver perfil
                      </Button>
                    </div>
                  </CardHeader>

                  <CardContent className="space-y-2 pt-0">
                    {group.tasks.map((task) => {
                      const overdue = isOverdue(task, todayKey);
                      const src = taskSource(task);
                      const planType = taskPlanType(task);

                      return (
                        <article
                          key={task.id}
                          className={`rounded-xl border p-3 transition ${
                            overdue
                              ? "border-lovable-danger/30 bg-lovable-danger/10"
                              : "border-lovable-border bg-lovable-surface-soft hover:bg-lovable-primary-soft/20"
                          }`}
                        >
                          <div className="flex flex-wrap items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-semibold text-lovable-ink">{task.title}</p>
                              {task.description ? (
                                <p className="mt-0.5 text-xs text-lovable-ink-muted">{task.description}</p>
                              ) : null}
                            </div>
                            <div className="flex flex-wrap items-center gap-1">
                              <Badge variant={statusVariant(task.status)}>{STATUS_LABELS[task.status]}</Badge>
                              <Badge variant={priorityVariant(task.priority)}>{PRIORITY_LABELS[task.priority]}</Badge>
                              {src === "onboarding" ? <Badge variant="neutral">Onboarding</Badge> : null}
                              {src === "plan_followup" && planType ? (
                                <Badge variant="neutral">Follow-up {formatPlanLabel(planType)}</Badge>
                              ) : null}
                              {src === "automation" ? <Badge variant="neutral">Automacao</Badge> : null}
                              {overdue ? <Badge variant="danger">Atrasada</Badge> : null}
                            </div>
                          </div>
                          {task.suggested_message ? (
                            <div className="mt-2 rounded-lg border border-lovable-border bg-lovable-primary-soft/20 px-3 py-2">
                              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-lovable-ink-muted">
                                Mensagem sugerida
                              </p>
                              <p className="text-xs text-lovable-ink">{task.suggested_message}</p>
                            </div>
                          ) : null}
                          <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className={`text-xs ${overdue ? "font-semibold text-lovable-danger" : "text-lovable-ink-muted"}`}
                              >
                                {overdue ? "Atrasada - " : ""}Vencimento: {formatDueDate(task.due_date)}
                              </span>
                              {task.assigned_to_user_id ? (
                                <span className="rounded-full bg-lovable-primary/10 px-2 py-0.5 text-[10px] font-medium text-lovable-primary">
                                  {userNameById.get(task.assigned_to_user_id) ?? "Responsavel"}
                                </span>
                              ) : null}
                            </div>
                            <div className="flex items-center gap-1">
                              {task.status !== "done" && task.status !== "cancelled" ? (
                                <>
                                  {task.status === "todo" ? (
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      className="text-lovable-success hover:bg-lovable-success/10"
                                      disabled={updateMutation.isPending}
                                      onClick={() => updateMutation.mutate({ taskId: task.id, status: "doing" })}
                                    >
                                      Andamento
                                    </Button>
                                  ) : null}
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="text-green-600 hover:bg-green-50"
                                    disabled={updateMutation.isPending}
                                    onClick={() => updateMutation.mutate({ taskId: task.id, status: "done" })}
                                  >
                                    Concluir
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    disabled={updateMutation.isPending}
                                    onClick={() => updateMutation.mutate({ taskId: task.id, status: "cancelled" })}
                                  >
                                    Cancelar
                                  </Button>
                                </>
                              ) : null}
                              <Button
                                variant="ghost"
                                size="sm"
                                disabled={deleteMutation.isPending}
                                onClick={() => setPendingDeleteId(task.id)}
                              >
                                Excluir
                              </Button>
                            </div>
                          </div>
                        </article>
                      );
                    })}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
          </TabsContent>
        </section>
      </Tabs>
      {createOpen ? (
        <CreateTaskModal
          members={membersQuery.data ?? []}
          onClose={() => setCreateOpen(false)}
          onSubmit={(p) => createMutation.mutate(p)}
          isPending={createMutation.isPending}
        />
      ) : null}
      {pendingDeleteId ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-sm rounded-2xl border border-lovable-border bg-lovable-surface p-6 shadow-xl">
            <h3 className="mb-2 text-base font-bold text-lovable-ink">Excluir tarefa?</h3>
            <p className="mb-4 text-sm text-lovable-ink-muted">
              <strong>{pendingDeleteTask?.title}</strong>
              <br />
              Esta acao nao pode ser desfeita.
            </p>
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={() => setPendingDeleteId(null)} disabled={deleteMutation.isPending}>
                Cancelar
              </Button>
              <Button
                variant="primary"
                size="sm"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(pendingDeleteId)}
              >
                {deleteMutation.isPending ? "Excluindo..." : "Confirmar exclusao"}
              </Button>
            </div>
          </div>
        </div>
      ) : null}
    </>
  );
}

