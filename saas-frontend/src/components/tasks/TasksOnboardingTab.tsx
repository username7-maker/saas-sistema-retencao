import clsx from "clsx";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, MessageCircle, Phone, Rocket, Search } from "lucide-react";

import { AIAssistantPanel } from "../common/AIAssistantPanel";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from "../ui2";
import { memberService, type OnboardingScoreResult } from "../../services/memberService";
import type { Member, Task } from "../../types";
import { getPreferredShiftLabel, matchesPreferredShift } from "../../utils/preferredShift";
import { buildWhatsAppHref, formatPhoneDisplay, normalizeWhatsAppPhone } from "../../utils/whatsapp";
import {
  PLAYBOOK_META,
  type OnboardingPlaybookKey,
  getTodayKey,
  isOnboardingActiveMember,
  isOverdue,
  isDueToday,
  memberToPlaybook,
  taskSource,
} from "./taskUtils";

const FACTOR_META: Record<keyof OnboardingScoreResult["factors"], { label: string; weight: number }> = {
  checkin_frequency: { label: "Check-ins", weight: 30 },
  first_assessment: { label: "Avaliacao", weight: 15 },
  task_completion: { label: "Tarefas", weight: 20 },
  consistency: { label: "Consistencia", weight: 20 },
  member_response: { label: "Resposta/feedback", weight: 15 },
};

const PLAYBOOK_ACTIONS: Record<
  OnboardingPlaybookKey,
  Array<{ day: string; owner: string; label: string; description: string }>
> = {
  engajado: [
    { day: "D7", owner: "automatico", label: "Celebracao inicial", description: "Mensagem contextual reforcando a meta e o bom ritmo." },
    { day: "D14", owner: "automatico", label: "NPS antecipado", description: "Capturar o pico de engajamento antes do D30." },
    { day: "D21", owner: "consultor", label: "Oferta de upsell", description: "Abordagem baseada no progresso ja construindo fidelizacao." },
    { day: "D30", owner: "automatico", label: "Handoff para retencao", description: "Encerrar onboarding e migrar o aluno para acompanhamento recorrente." },
  ],
  atencao: [
    { day: "D3", owner: "automatico", label: "Check-in empatico", description: "Mensagem curta para entender o que travou a rotina." },
    { day: "D7", owner: "consultor", label: "Reagendar avaliacao", description: "Contato humano para recuperar o plano de entrada." },
    { day: "D14", owner: "automatico", label: "Reforco do objetivo", description: "Reconectar meta, rotina e beneficio percebido." },
    { day: "D30", owner: "professor", label: "Revisao tecnica", description: "Ajustar o plano antes de o aluno esfriar de vez." },
  ],
  critico: [
    { day: "D1", owner: "urgente", label: "Intervencao humana", description: "Nao esperar automacao. O risco de evasao e imediato." },
    { day: "D3", owner: "consultor", label: "Ligacao contextual", description: "Contato humano com historico recente em maos." },
    { day: "D7", owner: "gerencia", label: "Escalada", description: "Gerencia assume se ainda nao houve resposta." },
    { day: "D14", owner: "consultor", label: "Reformulacao", description: "Propor ajuste de horario, frequencia ou abordagem." },
  ],
};

function scoreBarClass(score: number): string {
  if (score >= 70) return "bg-emerald-500";
  if (score >= 40) return "bg-amber-500";
  return "bg-rose-500";
}

function OnboardingScorePanel({
  member,
  onScoreResolved,
}: {
  member: Member;
  onScoreResolved?: (memberId: string, score: number) => void;
}) {
  const scoreQuery = useQuery({
    queryKey: ["onboarding-score", member.id],
    queryFn: () => memberService.getOnboardingScore(member.id),
    staleTime: 60_000,
  });

  useEffect(() => {
    if (!scoreQuery.data || !onScoreResolved) return;
    onScoreResolved(member.id, scoreQuery.data.score);
  }, [member.id, onScoreResolved, scoreQuery.data]);

  if (scoreQuery.isLoading) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-sm text-lovable-ink-muted">Calculando score detalhado...</CardContent>
      </Card>
    );
  }

  if (scoreQuery.isError || !scoreQuery.data) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-sm text-lovable-ink-muted">
          Nao foi possivel carregar o score detalhado.
        </CardContent>
      </Card>
    );
  }

  const score = scoreQuery.data;
  const playbookKey = memberToPlaybook(member, score.score);
  const playbook = PLAYBOOK_META[playbookKey];
  const phoneDisplay = formatPhoneDisplay(member.phone);
  const normalizedPhone = normalizeWhatsAppPhone(member.phone);
  const whatsappHref = buildWhatsAppHref(member.phone, score.assistant?.suggested_message, member.full_name);

  return (
    <div className="space-y-4">
      <AIAssistantPanel
        assistant={score.assistant}
        title="IA recomenda"
        subtitle="Leitura operacional do onboarding para agir nas proximas 24 horas."
      />

      <Card className={playbook.surfaceClass}>
        <CardContent className="flex flex-col gap-4 p-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">
              Score de onboarding
            </p>
            <p className={clsx("mt-2 text-4xl font-bold", playbook.accentClass)}>{score.score}</p>
            <p className="mt-2 text-sm text-lovable-ink-muted">
              {member.full_name} - {score.days_since_join} dias de jornada
            </p>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              {normalizedPhone && phoneDisplay ? (
                <a
                  href={`tel:${normalizedPhone}`}
                  className="inline-flex items-center gap-2 rounded-full border border-lovable-border bg-lovable-surface px-3 py-1.5 text-xs font-medium text-lovable-ink transition hover:border-lovable-primary/40 hover:text-lovable-primary"
                >
                  <Phone size={12} />
                  {phoneDisplay}
                </a>
              ) : (
                <span className="inline-flex items-center gap-2 rounded-full border border-dashed border-lovable-border px-3 py-1.5 text-xs text-lovable-ink-muted">
                  <Phone size={12} />
                  Telefone nao informado
                </span>
              )}
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
          <div className="max-w-sm">
            <Badge variant={playbookKey === "critico" ? "danger" : playbookKey === "atencao" ? "warning" : "success"}>
              {PLAYBOOK_META[playbookKey].label}
            </Badge>
            <p className="mt-3 text-sm text-lovable-ink-muted">{PLAYBOOK_META[playbookKey].description}</p>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Fatores do score</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0">
            {(Object.entries(FACTOR_META) as Array<[keyof OnboardingScoreResult["factors"], (typeof FACTOR_META)[keyof OnboardingScoreResult["factors"]]]>).map(
              ([key, meta]) => {
                const value = score.factors[key] ?? 0;
                return (
                  <div key={key}>
                    <div className="mb-1 flex items-center justify-between gap-3">
                      <span className="text-sm text-lovable-ink">
                        {meta.label}
                        <span className="ml-1 text-xs text-lovable-ink-muted">({meta.weight}%)</span>
                      </span>
                      <span className="text-sm font-semibold text-lovable-ink">{value}%</span>
                    </div>
                    <div className="h-2 rounded-full bg-lovable-border">
                      <div className={clsx("h-2 rounded-full transition-all", scoreBarClass(value))} style={{ width: `${value}%` }} />
                    </div>
                  </div>
                );
              },
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Sinais captados</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 pt-0 text-sm text-lovable-ink-muted">
            <p>{score.checkin_count} check-ins detectados nos primeiros {score.days_since_join} dias.</p>
            <p>{score.completed_tasks}/{score.total_tasks} tarefas concluidas no onboarding.</p>
            <p>{score.factors.first_assessment === 100 ? "Avaliacao ja realizada." : "Avaliacao ainda pendente."}</p>
            <p>{score.factors.member_response === 100 ? "Ja houve resposta ou feedback do aluno." : "Ainda nao houve resposta registrada do aluno."}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Playbook sugerido</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 pt-0">
          {PLAYBOOK_ACTIONS[playbookKey].map((action) => (
            <div key={`${playbookKey}-${action.day}-${action.label}`} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={playbookKey === "critico" ? "danger" : playbookKey === "atencao" ? "warning" : "success"}>{action.day}</Badge>
                <span className="text-sm font-semibold text-lovable-ink">{action.label}</span>
                <span className="rounded-full bg-lovable-surface px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-lovable-ink-muted">
                  {action.owner}
                </span>
              </div>
              <p className="mt-2 text-sm text-lovable-ink-muted">{action.description}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

interface TasksOnboardingTabProps {
  members: Member[];
  membersLoading: boolean;
  membersError: boolean;
  tasks: Task[];
  currentUserShift: "overnight" | "morning" | "afternoon" | "evening" | null;
  onOpenOnboardingQueue: () => void;
}

const JOURNEY_BUCKETS = [
  { key: "d0-d1", label: "D0 / D1", match: (offset: number | null) => offset === 0 || offset === 1 },
  { key: "d3", label: "D3", match: (offset: number | null) => offset === 3 },
  { key: "d7", label: "D7", match: (offset: number | null) => offset === 7 },
  { key: "d15", label: "D15", match: (offset: number | null) => offset === 15 },
  { key: "d30", label: "D30", match: (offset: number | null) => offset === 30 },
] as const;

export function TasksOnboardingTab({
  members,
  membersLoading,
  membersError,
  tasks,
  currentUserShift,
  onOpenOnboardingQueue,
}: TasksOnboardingTabProps) {
  const [activePlaybook, setActivePlaybook] = useState<OnboardingPlaybookKey>("atencao");
  const [selectedMemberId, setSelectedMemberId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [useCurrentShift, setUseCurrentShift] = useState(Boolean(currentUserShift));
  const [scoreOverridesByMemberId, setScoreOverridesByMemberId] = useState<Record<string, number>>({});
  const todayKey = useMemo(() => getTodayKey(), []);
  const membersById = useMemo(() => new Map(members.map((member) => [member.id, member])), [members]);
  const currentShiftLabel = getPreferredShiftLabel(currentUserShift);

  useEffect(() => {
    if (currentUserShift) {
      setUseCurrentShift(true);
    }
  }, [currentUserShift]);

  const onboardingMembers = useMemo(() => {
    const activeMembers = members.filter((member) => isOnboardingActiveMember(member));
    if (!useCurrentShift || !currentUserShift) return activeMembers;
    return activeMembers.filter((member) => matchesPreferredShift(member.preferred_shift, currentUserShift));
  }, [currentUserShift, members, useCurrentShift]);
  const onboardingScoreboardQuery = useQuery({
    queryKey: ["onboarding-scoreboard"],
    queryFn: () => memberService.getOnboardingScoreboard(),
    staleTime: 0,
    refetchOnMount: "always",
    refetchOnWindowFocus: true,
    enabled: onboardingMembers.length > 0,
  });

  useEffect(() => {
    setScoreOverridesByMemberId((current) => {
      const activeIds = new Set(onboardingMembers.map((member) => member.id));
      const next = Object.fromEntries(Object.entries(current).filter(([memberId]) => activeIds.has(memberId)));
      return Object.keys(next).length === Object.keys(current).length ? current : next;
    });
  }, [onboardingMembers]);

  const onboardingScoreByMemberId = useMemo(() => {
    const scoreMap = new Map<string, number>();
    const snapshots = onboardingScoreboardQuery.data ?? [];
    const snapshotScoreByMemberId = new Map(snapshots.map((snapshot) => [snapshot.member_id, snapshot.score]));
    onboardingMembers.forEach((member) => {
      scoreMap.set(
        member.id,
        scoreOverridesByMemberId[member.id] ?? snapshotScoreByMemberId.get(member.id) ?? member.onboarding_score ?? 0,
      );
    });
    return scoreMap;
  }, [onboardingMembers, onboardingScoreboardQuery.data, scoreOverridesByMemberId]);
  const getResolvedOnboardingScore = useCallback(
    (member: Member): number => onboardingScoreByMemberId.get(member.id) ?? member.onboarding_score ?? 0,
    [onboardingScoreByMemberId],
  );
  const handleScoreResolved = useCallback((memberId: string, score: number) => {
    setScoreOverridesByMemberId((current) => (current[memberId] === score ? current : { ...current, [memberId]: score }));
    if (selectedMemberId !== memberId) return;
    const member = membersById.get(memberId);
    if (!member) return;
    const nextPlaybook = memberToPlaybook(member, score);
    setActivePlaybook((current) => (current === nextPlaybook ? current : nextPlaybook));
  }, [membersById, selectedMemberId]);
  const playbookGroups = useMemo<Record<OnboardingPlaybookKey, Member[]>>(
    () => ({
      engajado: onboardingMembers.filter((member) => memberToPlaybook(member, getResolvedOnboardingScore(member)) === "engajado"),
      atencao: onboardingMembers.filter((member) => memberToPlaybook(member, getResolvedOnboardingScore(member)) === "atencao"),
      critico: onboardingMembers.filter((member) => memberToPlaybook(member, getResolvedOnboardingScore(member)) === "critico"),
    }),
    [onboardingMembers, onboardingScoreByMemberId],
  );

  useEffect(() => {
    if (playbookGroups[activePlaybook].length > 0) return;
    const nextPlaybook = (["atencao", "critico", "engajado"] as OnboardingPlaybookKey[]).find(
      (key) => playbookGroups[key].length > 0,
    );
    if (nextPlaybook) {
      setActivePlaybook(nextPlaybook);
      setSelectedMemberId(null);
    }
  }, [activePlaybook, playbookGroups]);

  const filteredMembers = useMemo(() => {
    const groupMembers = playbookGroups[activePlaybook];
    const query = search.trim().toLowerCase();
    const sortedMembers = [...groupMembers].sort((left, right) => {
      const scoreDiff = getResolvedOnboardingScore(left) - getResolvedOnboardingScore(right);
      if (scoreDiff !== 0) return scoreDiff;
      return new Date(right.join_date).getTime() - new Date(left.join_date).getTime();
    });
    if (!query) return sortedMembers;
    return sortedMembers.filter((member) => member.full_name.toLowerCase().includes(query));
  }, [activePlaybook, playbookGroups, search, onboardingScoreByMemberId]);

  const selectedMember = filteredMembers.find((member) => member.id === selectedMemberId) ?? filteredMembers[0] ?? null;
  const onboardingTasks = useMemo(
    () =>
      tasks.filter((task) => {
        if (taskSource(task) !== "onboarding" || task.status === "done" || task.status === "cancelled") return false;
        if (!useCurrentShift || !currentUserShift) return true;
        return matchesPreferredShift(task.preferred_shift ?? (task.member_id ? membersById.get(task.member_id)?.preferred_shift : null), currentUserShift);
      }),
    [currentUserShift, membersById, tasks, useCurrentShift],
  );
  const onboardingStats = useMemo(
    () => ({
      pending: onboardingTasks.length,
      overdue: onboardingTasks.filter((task) => isOverdue(task, todayKey)).length,
      unassigned: onboardingTasks.filter((task) => !task.assigned_to_user_id).length,
      dueToday: onboardingTasks.filter((task) => isDueToday(task, todayKey)).length,
    }),
    [onboardingTasks, todayKey],
  );
  const taskDayOffset = useMemo(
    () => (task: Task) => {
      const rawValue = task.extra_data?.day_offset;
      if (typeof rawValue === "number" && Number.isFinite(rawValue)) return rawValue;
      if (typeof rawValue === "string") {
        const parsed = Number(rawValue);
        if (Number.isFinite(parsed)) return parsed;
      }

      if (!task.member_id || !task.due_date) return null;
      const member = membersById.get(task.member_id);
      if (!member?.join_date) return null;

      const joinDate = new Date(`${member.join_date}T00:00:00Z`).getTime();
      const dueDate = new Date(`${task.due_date.slice(0, 10)}T00:00:00Z`).getTime();
      const diff = Math.round((dueDate - joinDate) / 86_400_000);
      return Number.isFinite(diff) ? diff : null;
    },
    [membersById],
  );
  const journeyGroups = useMemo(
    () =>
      JOURNEY_BUCKETS.map((bucket) => ({
        ...bucket,
        tasks: onboardingTasks.filter((task) => bucket.match(taskDayOffset(task))),
      })),
    [onboardingTasks, taskDayOffset],
  );

  if (membersLoading) {
    return <Card><CardContent className="p-8 text-center text-sm text-lovable-ink-muted">Carregando onboarding...</CardContent></Card>;
  }

  if (membersError) {
    return <Card><CardContent className="p-8 text-center text-sm text-lovable-danger">Nao foi possivel carregar os dados de onboarding.</CardContent></Card>;
  }

  if (onboardingMembers.length === 0) {
    return (
      <Card>
        <CardContent className="p-10 text-center">
          <CheckCircle2 size={28} className="mx-auto text-lovable-ink-muted/30" />
          <h3 className="mt-4 text-base font-semibold text-lovable-ink">
            {useCurrentShift && currentShiftLabel ? `Sem onboarding ativo no turno ${currentShiftLabel}` : "Sem onboarding ativo"}
          </h3>
          <p className="mt-2 text-sm text-lovable-ink-muted">
            {useCurrentShift && currentShiftLabel
              ? "Nenhum aluno do seu turno entrou na janela ativa de onboarding. Se precisar cobrir outro turno, desligue o filtro do login."
              : "Nao ha alunos em onboarding ativo agora. Quando surgirem novos alunos, esta fila reaparece aqui."}
          </p>
          {useCurrentShift && currentShiftLabel ? (
            <Button variant="secondary" size="sm" className="mt-4" onClick={() => setUseCurrentShift(false)}>
              Ver todos os turnos
            </Button>
          ) : null}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4 p-4">
          <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-primary">Onboarding preservado</p>
              <h2 className="mt-1 text-2xl font-bold text-lovable-ink">Onboarding</h2>
              <p className="mt-1 text-sm text-lovable-ink-muted">
                Acompanhamento completo do primeiro mes, separado da fila operacional para reduzir ruido.
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {currentUserShift && currentShiftLabel ? (
                <Button variant={useCurrentShift ? "primary" : "secondary"} size="sm" onClick={() => setUseCurrentShift((value) => !value)}>
                  {useCurrentShift ? `Meu turno: ${currentShiftLabel}` : `Mostrar meu turno: ${currentShiftLabel}`}
                </Button>
              ) : null}
              <Button variant="secondary" size="sm" onClick={onOpenOnboardingQueue}>
                Ver tasks de onboarding
              </Button>
            </div>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Pendentes</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{onboardingStats.pending}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Atrasadas</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{onboardingStats.overdue}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Sem responsavel</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{onboardingStats.unassigned}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Vencem hoje</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{onboardingStats.dueToday}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base">Jornada ativa do onboarding</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 pt-0 md:grid-cols-2 xl:grid-cols-5">
          {journeyGroups.map((group) => (
            <div key={group.key} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <div className="flex items-center justify-between gap-3">
                <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{group.label}</p>
                <span className="text-sm font-bold text-lovable-ink">{group.tasks.length}</span>
              </div>
              <div className="mt-3 space-y-2">
                {group.tasks.slice(0, 3).map((task) => (
                  <div key={task.id} className="rounded-xl border border-lovable-border/70 px-2 py-2">
                    <p className="truncate text-xs font-semibold text-lovable-ink">{task.member_name ?? task.title}</p>
                    <p className="mt-1 truncate text-[11px] text-lovable-ink-muted">{task.title}</p>
                  </div>
                ))}
                {group.tasks.length === 0 ? <p className="text-xs text-lovable-ink-muted">Sem tasks nesta etapa.</p> : null}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            <Rocket size={18} className="text-lovable-primary" />
            Intelligence de onboarding
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 pt-0">
          <div className="grid gap-2 md:grid-cols-3">
            {(Object.entries(PLAYBOOK_META) as Array<[OnboardingPlaybookKey, (typeof PLAYBOOK_META)[OnboardingPlaybookKey]]>).map(([key, meta]) => {
              const active = activePlaybook === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => {
                    setActivePlaybook(key);
                    setSelectedMemberId(null);
                  }}
                  className={clsx(
                    "rounded-2xl border p-4 text-left transition-all",
                    active ? meta.surfaceClass : "border-lovable-border bg-lovable-surface hover:border-lovable-primary/30",
                  )}
                >
                  <p className={clsx("text-2xl font-bold", meta.accentClass)}>{playbookGroups[key].length}</p>
                  <p className="mt-1 text-sm font-semibold text-lovable-ink">{meta.label}</p>
                  <p className="mt-1 text-xs text-lovable-ink-muted">{meta.description}</p>
                </button>
              );
            })}
          </div>

          <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
            <Card className="border-lovable-border bg-lovable-surface-soft">
              <CardContent className="space-y-3 p-4">
                <div className="relative">
                  <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted" />
                  <Input
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Buscar aluno no playbook..."
                    className="pl-9"
                  />
                </div>

                <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
                  {filteredMembers.length === 0 ? (
                    <div className="rounded-2xl border border-dashed border-lovable-border p-6 text-center">
                      <Activity size={22} className="mx-auto text-lovable-ink-muted/30" />
                      <p className="mt-2 text-sm text-lovable-ink-muted">Nenhum aluno encontrado neste grupo.</p>
                    </div>
                  ) : (
                    filteredMembers.map((member) => (
                      <button
                        key={member.id}
                        type="button"
                        onClick={() => setSelectedMemberId(member.id)}
                        className={clsx(
                          "w-full rounded-2xl border p-3 text-left transition-all",
                          selectedMember?.id === member.id
                            ? PLAYBOOK_META[activePlaybook].surfaceClass
                            : "border-lovable-border bg-lovable-surface hover:border-lovable-primary/30",
                        )}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <p className="truncate text-sm font-semibold text-lovable-ink">{member.full_name}</p>
                          <span className="text-sm font-bold text-lovable-ink">{getResolvedOnboardingScore(member)}</span>
                        </div>
                        <p className="mt-1 text-xs text-lovable-ink-muted">{member.plan_name}</p>
                      </button>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>

            <div>
              {selectedMember ? (
                <OnboardingScorePanel member={selectedMember} onScoreResolved={handleScoreResolved} />
              ) : (
                <Card>
                  <CardContent className="p-10 text-center">
                    <Activity size={28} className="mx-auto text-lovable-ink-muted/30" />
                    <p className="mt-3 text-sm text-lovable-ink-muted">Selecione um aluno para ver o detalhamento.</p>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
