import clsx from "clsx";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Activity, CheckCircle2, Rocket, Search } from "lucide-react";

import { AIAssistantPanel } from "../common/AIAssistantPanel";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle, Input } from "../ui2";
import { memberService, type OnboardingScoreResult } from "../../services/memberService";
import type { Member, Task } from "../../types";
import {
  PLAYBOOK_META,
  type OnboardingPlaybookKey,
  isOnboardingActiveMember,
  memberToPlaybook,
  taskSource,
} from "./taskUtils";

const FACTOR_META: Record<keyof OnboardingScoreResult["factors"], { label: string; weight: number }> = {
  checkin_frequency: { label: "Check-ins", weight: 30 },
  first_assessment: { label: "Avaliacao", weight: 15 },
  task_completion: { label: "Tarefas", weight: 20 },
  consistency: { label: "Consistencia", weight: 20 },
  nps_response: { label: "Resposta", weight: 15 },
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

function OnboardingScorePanel({ member }: { member: Member }) {
  const scoreQuery = useQuery({
    queryKey: ["onboarding-score", member.id],
    queryFn: () => memberService.getOnboardingScore(member.id),
    staleTime: 60_000,
  });

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
  const playbookKey = memberToPlaybook(member);
  const playbook = PLAYBOOK_META[playbookKey];

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
            <p>{score.factors.nps_response === 100 ? "Ja respondeu ao contato." : "Ainda nao respondeu ao contato."}</p>
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
  onOpenOnboardingQueue: () => void;
}

export function TasksOnboardingTab({
  members,
  membersLoading,
  membersError,
  tasks,
  onOpenOnboardingQueue,
}: TasksOnboardingTabProps) {
  const [activePlaybook, setActivePlaybook] = useState<OnboardingPlaybookKey>("atencao");
  const [selectedMemberId, setSelectedMemberId] = useState<string | null>(null);
  const [search, setSearch] = useState("");

  const onboardingMembers = useMemo(() => members.filter((member) => isOnboardingActiveMember(member)), [members]);
  const playbookGroups = useMemo<Record<OnboardingPlaybookKey, Member[]>>(
    () => ({
      engajado: onboardingMembers.filter((member) => memberToPlaybook(member) === "engajado"),
      atencao: onboardingMembers.filter((member) => memberToPlaybook(member) === "atencao"),
      critico: onboardingMembers.filter((member) => memberToPlaybook(member) === "critico"),
    }),
    [onboardingMembers],
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
      const scoreDiff = (left.onboarding_score ?? 0) - (right.onboarding_score ?? 0);
      if (scoreDiff !== 0) return scoreDiff;
      return new Date(right.join_date).getTime() - new Date(left.join_date).getTime();
    });
    if (!query) return sortedMembers;
    return sortedMembers.filter((member) => member.full_name.toLowerCase().includes(query));
  }, [activePlaybook, playbookGroups, search]);

  const selectedMember = filteredMembers.find((member) => member.id === selectedMemberId) ?? filteredMembers[0] ?? null;
  const onboardingTasks = useMemo(() => tasks.filter((task) => taskSource(task) === "onboarding" && task.status !== "done" && task.status !== "cancelled"), [tasks]);

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
          <h3 className="mt-4 text-base font-semibold text-lovable-ink">Sem onboarding ativo</h3>
          <p className="mt-2 text-sm text-lovable-ink-muted">
            Nao ha alunos em onboarding ativo agora. Quando surgirem novos alunos, esta fila reaparece aqui.
          </p>
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
            <Button variant="secondary" size="sm" onClick={onOpenOnboardingQueue}>
              Ver tasks de onboarding
            </Button>
          </div>

          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Ativos</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{onboardingMembers.length}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Em atencao</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{playbookGroups.atencao.length + playbookGroups.critico.length}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Tasks pendentes</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{onboardingTasks.length}</p>
            </div>
            <div className="rounded-2xl border border-lovable-border bg-lovable-surface-soft p-3">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-ink-muted">Playbook critico</p>
              <p className="mt-2 text-2xl font-bold text-lovable-ink">{playbookGroups.critico.length}</p>
            </div>
          </div>
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
                          <span className="text-sm font-bold text-lovable-ink">{member.onboarding_score ?? "--"}</span>
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
                <OnboardingScorePanel member={selectedMember} />
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
