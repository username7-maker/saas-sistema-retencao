import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AxiosError } from "axios";
import toast from "react-hot-toast";
import { Link, useParams, useSearchParams } from "react-router-dom";

import { AssessmentRegistrationComposer } from "../../components/assessments/AssessmentRegistrationComposer";
import { AssessmentTimeline } from "../../components/assessments/AssessmentTimeline";
import { AssessmentWorkspaceOverview } from "../../components/assessments/AssessmentWorkspaceOverview";
import {
  ASSESSMENT_WORKSPACE_TABS,
  daysSince,
  formatDateTime,
  getAge,
  getInitials,
  normalizeAssessmentWorkspaceTab,
  riskBadgeVariant,
  riskLabel,
  statusBadgeVariant,
  statusLabel,
  type AssessmentWorkspaceTab,
} from "../../components/assessments/assessmentWorkspaceUtils";
import { EvolutionCharts } from "../../components/assessments/EvolutionCharts";
import { GoalsProgress } from "../../components/assessments/GoalsProgress";
import { MemberBodyCompositionTab } from "../../components/assessments/MemberBodyCompositionTab";
import { MemberConstraintsEditor } from "../../components/assessments/MemberConstraintsEditor";
import { MemberGoalsEditor } from "../../components/assessments/MemberGoalsEditor";
import { MemberTrainingPlanEditor } from "../../components/assessments/MemberTrainingPlanEditor";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { MemberTimeline360Content } from "../../components/common/MemberTimeline360Content";
import { Badge, Button, Card, CardContent, Dialog, Tabs, TabsContent, TabsList, TabsTrigger, Textarea } from "../../components/ui2";
import { bodyCompositionService } from "../../services/bodyCompositionService";
import { assessmentService, type AssessmentSummary360 } from "../../services/assessmentService";
import { memberTimelineService } from "../../services/memberTimelineService";
import { memberService } from "../../services/memberService";

interface InternalNote {
  id: string;
  text: string;
  created_at: string;
}

interface ApiErrorPayload {
  detail?: string;
}

function createNoteId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function parseInternalNotes(extraData: Record<string, unknown>): InternalNote[] {
  const parsed: InternalNote[] = [];
  const raw = extraData.profile360_notes;

  if (Array.isArray(raw)) {
    for (const entry of raw) {
      if (!entry || typeof entry !== "object") continue;
      const noteObj = entry as Record<string, unknown>;
      const text = typeof noteObj.text === "string" ? noteObj.text.trim() : "";
      if (!text) continue;
      const createdAt =
        typeof noteObj.created_at === "string" && !Number.isNaN(Date.parse(noteObj.created_at))
          ? noteObj.created_at
          : new Date().toISOString();
      parsed.push({
        id: typeof noteObj.id === "string" ? noteObj.id : createNoteId(),
        text,
        created_at: createdAt,
      });
    }
  }

  const legacy = typeof extraData.profile360_internal_notes === "string" ? extraData.profile360_internal_notes.trim() : "";
  if (parsed.length === 0 && legacy) {
    parsed.push({
      id: "legacy-note",
      text: legacy,
      created_at: new Date().toISOString(),
    });
  }

  return parsed.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
}

function getLocalNotesStorageKey(memberId: string): string {
  return `profile360_notes_${memberId}`;
}

function parseInternalNotesFromStorage(memberId: string): InternalNote[] {
  if (typeof window === "undefined") return [];
  const raw = window.localStorage.getItem(getLocalNotesStorageKey(memberId));
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    const notes: InternalNote[] = [];
    for (const entry of parsed) {
      if (!entry || typeof entry !== "object") continue;
      const noteObj = entry as Record<string, unknown>;
      const text = typeof noteObj.text === "string" ? noteObj.text.trim() : "";
      if (!text) continue;
      const createdAt =
        typeof noteObj.created_at === "string" && !Number.isNaN(Date.parse(noteObj.created_at))
          ? noteObj.created_at
          : new Date().toISOString();
      notes.push({
        id: typeof noteObj.id === "string" ? noteObj.id : createNoteId(),
        text,
        created_at: createdAt,
      });
    }
    return notes.sort((a, b) => Date.parse(b.created_at) - Date.parse(a.created_at));
  } catch {
    return [];
  }
}

function persistInternalNotesToStorage(memberId: string, notes: InternalNote[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(getLocalNotesStorageKey(memberId), JSON.stringify(notes));
}

function openTabWithSearchParams(
  current: URLSearchParams,
  nextTab: AssessmentWorkspaceTab,
  setSearchParams: ReturnType<typeof useSearchParams>[1],
) {
  const next = new URLSearchParams(current);
  next.set("tab", nextTab);
  setSearchParams(next, { replace: true });
}

function DetailMetric({
  label,
  value,
  helper,
}: {
  label: string;
  value: string;
  helper: string;
}) {
  return (
    <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">{label}</p>
      <p className="mt-2 text-lg font-semibold text-lovable-ink">{value}</p>
      <p className="mt-1 text-xs text-lovable-ink-muted">{helper}</p>
    </div>
  );
}

function NotesSummaryCard({
  latestNote,
  notesCount,
  onAdd,
  onHistory,
}: {
  latestNote: InternalNote | null;
  notesCount: number;
  onAdd: () => void;
  onHistory: () => void;
}) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        <div className="flex items-center justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Notas internas</p>
            <p className="text-sm text-lovable-ink-muted">Contexto da equipe e observacoes comportamentais.</p>
          </div>
          <Badge variant="neutral">{notesCount} nota(s)</Badge>
        </div>
        {latestNote ? (
          <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
            <p className="text-sm text-lovable-ink">{latestNote.text}</p>
            <p className="mt-2 text-xs text-lovable-ink-muted">{formatDateTime(latestNote.created_at)}</p>
          </div>
        ) : (
          <div className="rounded-xl border border-dashed border-lovable-border px-4 py-4 text-sm text-lovable-ink-muted">
            Nenhuma nota registrada ainda.
          </div>
        )}
        <div className="flex flex-wrap gap-2">
          <Button size="sm" variant="primary" onClick={onAdd}>
            + Adicionar nota
          </Button>
          <Button size="sm" variant="secondary" onClick={onHistory}>
            Historico
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function ContextSupportPanel({ summary }: { summary: AssessmentSummary360 }) {
  const hasDiagnosisFactors = summary.diagnosis.factors.length > 0;
  const hasActions = summary.actions.length > 0;

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4 pt-5">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Leitura causal</p>
            <p className="mt-2 text-lg font-semibold text-lovable-ink">{summary.diagnosis.primary_bottleneck_label}</p>
            <p className="mt-1 text-sm text-lovable-ink-muted">
              Secundario: {summary.diagnosis.secondary_bottleneck_label}
            </p>
            <p className="mt-3 text-sm text-lovable-ink">{summary.diagnosis.explanation}</p>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <DetailMetric
              label="Risco de frustracao"
              value={String(summary.diagnosis.frustration_risk)}
              helper={`Confianca: ${summary.diagnosis.confidence}`}
            />
            <DetailMetric
              label="Benchmark"
              value={summary.benchmark.position_label}
              helper={`${summary.benchmark.percentile} percentil no cohort`}
            />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Fatores avaliados</p>
            {hasDiagnosisFactors ? (
              <ul className="mt-3 space-y-2">
                {summary.diagnosis.factors.map((factor) => (
                  <li key={factor.key} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-lovable-ink">{factor.label}</p>
                      <Badge variant="neutral">{factor.score}</Badge>
                    </div>
                    <p className="mt-1 text-xs text-lovable-ink-muted">{factor.reason}</p>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-sm text-lovable-ink-muted">Sem fatores suficientes para detalhar esta leitura.</p>
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="space-y-4 pt-5">
          <div className="flex items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Acoes recomendadas</p>
              <p className="text-sm text-lovable-ink-muted">Desdobramentos sugeridos a partir da leitura atual.</p>
            </div>
            <Badge variant={statusBadgeVariant(summary.status)}>{statusLabel(summary.status)}</Badge>
          </div>
          {hasActions ? (
            <ul className="space-y-3">
              {summary.actions.map((action) => (
                <li key={action.key} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-4 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-lovable-ink">{action.title}</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">{action.reason}</p>
                    </div>
                    <Badge variant="neutral">{action.priority}</Badge>
                  </div>
                  <p className="mt-3 text-xs text-lovable-primary">{action.suggested_message}</p>
                  <p className="mt-2 text-[11px] text-lovable-ink-muted">
                    Responsavel sugerido: {action.owner_role} - prazo: D+{action.due_in_days}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-lovable-ink-muted">Sem acoes recomendadas enquanto nao houver dados suficientes.</p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export function MemberProfile360Page() {
  const { memberId } = useParams<{ memberId: string }>();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();

  const [noteDraft, setNoteDraft] = useState("");
  const [isAddNoteOpen, setIsAddNoteOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const activeTab = normalizeAssessmentWorkspaceTab(searchParams.get("tab"));

  const profileQuery = useQuery({
    queryKey: ["assessments", "profile360", memberId],
    queryFn: () => assessmentService.profile360(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const assessmentsQuery = useQuery({
    queryKey: ["assessments", "list", memberId],
    queryFn: () => assessmentService.list(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const evolutionQuery = useQuery({
    queryKey: ["assessments", "evolution", memberId],
    queryFn: () => assessmentService.evolution(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const summary360Query = useQuery({
    queryKey: ["assessments", "summary360", memberId],
    queryFn: () => assessmentService.summary360(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const timelineQuery = useQuery({
    queryKey: ["member-timeline", memberId],
    queryFn: () => memberTimelineService.list(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const bodyCompositionQuery = useQuery({
    queryKey: ["body-composition", memberId],
    queryFn: () => bodyCompositionService.list(memberId ?? "", 5),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const addNoteMutation = useMutation({
    mutationFn: async () => {
      if (!memberId) throw new Error("MEMBRO_INVALIDO");
      const text = noteDraft.trim();
      if (!text) throw new Error("NOTA_VAZIA");

      const freshMember = await memberService.getMember(memberId);
      const currentExtra = (freshMember.extra_data ?? {}) as Record<string, unknown>;
      const currentNotes = parseInternalNotes(currentExtra);
      const newNote: InternalNote = {
        id: createNoteId(),
        text,
        created_at: new Date().toISOString(),
      };
      const mergedExtra = {
        ...currentExtra,
        profile360_internal_notes: text,
        profile360_notes: [newNote, ...currentNotes],
      };

      const updatedMember = await memberService.updateMember(memberId, {
        extra_data: {
          ...mergedExtra,
        },
      });

      const updatedExtra = (updatedMember.extra_data ?? mergedExtra) as Record<string, unknown>;
      return updatedExtra;
    },
    onSuccess: (updatedExtra) => {
      const parsedUpdatedNotes = parseInternalNotes(updatedExtra);
      if (memberId && parsedUpdatedNotes.length > 0) {
        persistInternalNotesToStorage(memberId, parsedUpdatedNotes);
      }
      queryClient.setQueryData(["assessments", "profile360", memberId], (current: unknown) => {
        if (!current || typeof current !== "object") return current;
        const currentObj = current as Record<string, unknown>;
        const currentMember = currentObj.member;
        if (!currentMember || typeof currentMember !== "object") return current;
        return {
          ...currentObj,
          member: {
            ...(currentMember as Record<string, unknown>),
            extra_data: updatedExtra,
          },
        };
      });
      toast.success("Nota adicionada.");
      setNoteDraft("");
      setIsAddNoteOpen(false);
      void queryClient.invalidateQueries({ queryKey: ["members"] });
    },
    onError: (error: unknown) => {
      if (error instanceof Error && error.message === "NOTA_VAZIA") {
        toast.error("Digite uma nota antes de adicionar.");
        return;
      }
      if (error instanceof Error && error.message === "MEMBRO_INVALIDO") {
        toast.error("Membro invalido para salvar nota.");
        return;
      }
      if (error instanceof AxiosError) {
        const detail = (error.response?.data as ApiErrorPayload | undefined)?.detail;
        if (detail) {
          toast.error(`Falha ao salvar nota: ${detail}`);
          return;
        }
      }
      toast.error("Nao foi possivel salvar a nota. Verifique permissao e tente novamente.");
    },
  });

  if (!memberId) {
    return <LoadingPanel text="Membro nao informado." />;
  }

  if (profileQuery.isLoading || assessmentsQuery.isLoading || evolutionQuery.isLoading || summary360Query.isLoading) {
    return <LoadingPanel text="Carregando workspace de avaliacao..." />;
  }

  if (profileQuery.isError || assessmentsQuery.isError || evolutionQuery.isError || summary360Query.isError) {
    return <LoadingPanel text="Erro ao carregar o workspace de avaliacao. Tente novamente." />;
  }

  if (!profileQuery.data || !summary360Query.data) {
    return <LoadingPanel text="Workspace de avaliacao indisponivel." />;
  }

  const profile = profileQuery.data;
  const assessments = assessmentsQuery.data ?? [];
  const evolution =
    evolutionQuery.data ?? {
      labels: [],
      weight: [],
      body_fat: [],
      lean_mass: [],
      bmi: [],
      strength: [],
      flexibility: [],
      cardio: [],
      checkins_labels: [],
      checkins_per_month: [],
      main_lift_load: [],
      main_lift_label: null,
      deltas: {},
    };
  const assessmentIntelligence = summary360Query.data;
  const latestBodyComposition = bodyCompositionQuery.data?.[0] ?? null;

  const memberExtra = profile.member.extra_data ?? {};
  const apiNotes = parseInternalNotes(memberExtra);
  const localNotes = parseInternalNotesFromStorage(memberId);
  const notes = apiNotes.length > 0 ? apiNotes : localNotes;
  const latestNote = notes[0] ?? null;
  const previousNotes = notes.slice(1);
  const age = getAge(memberExtra);
  const photoUrl = typeof memberExtra.photo_url === "string" ? memberExtra.photo_url : null;
  const daysWithoutCheckin = daysSince(profile.member.last_checkin_at);
  const hasStructuredAssessment = Boolean(assessmentIntelligence.latest_assessment);
  const hasEvolutionData = Boolean(evolution.labels.length);

  const openTab = (tab: AssessmentWorkspaceTab) => openTabWithSearchParams(searchParams, tab, setSearchParams);

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Workspace principal</p>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Avaliacao do aluno</h2>
          <p className="text-sm text-lovable-ink-muted">
            Leitura rapida, registro, evolucao e contexto operacional em uma unica jornada.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            to="/assessments"
            className="inline-flex h-9 items-center justify-center rounded-lg border border-lovable-border px-3 text-xs font-semibold text-lovable-ink hover:bg-lovable-surface-soft"
          >
            Voltar para fila
          </Link>
          <Button size="sm" variant="primary" onClick={() => openTab("registro")}>
            Registrar avaliacao
          </Button>
        </div>
      </header>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
          <div className="flex gap-4">
            <div className="h-20 w-20 overflow-hidden rounded-2xl border border-lovable-border bg-lovable-surface-soft">
              {photoUrl ? (
                <img src={photoUrl} alt={profile.member.full_name} className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-xl font-bold text-lovable-ink-muted">
                  {getInitials(profile.member.full_name)}
                </div>
              )}
            </div>

            <div className="space-y-3">
              <div>
                <p className="text-2xl font-semibold text-lovable-ink">{profile.member.full_name}</p>
                <p className="text-sm text-lovable-ink-muted">
                  Plano: {profile.member.plan_name}
                  {profile.member.email ? ` - ${profile.member.email}` : ""}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={riskBadgeVariant(profile.member.risk_level)}>{riskLabel(profile.member.risk_level)}</Badge>
                <Badge variant={statusBadgeVariant(assessmentIntelligence.status)}>{statusLabel(assessmentIntelligence.status)}</Badge>
                <Badge variant="neutral">{age !== null ? `${age} anos` : "Idade nao informada"}</Badge>
                <Badge variant="neutral">
                  {daysWithoutCheckin === null
                    ? "Sem check-in"
                    : daysWithoutCheckin === 0
                      ? "Check-in hoje"
                      : `${daysWithoutCheckin} dia(s) sem check-in`}
                </Badge>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <DetailMetric
                  label="Chance em 60 dias"
                  value={`${assessmentIntelligence.forecast.probability_60d}%`}
                  helper={`Meta: ${assessmentIntelligence.goal_type}`}
                />
                <DetailMetric
                  label="Ultima avaliacao"
                  value={assessmentIntelligence.latest_assessment ? "Registrada" : "Pendente"}
                  helper={
                    assessmentIntelligence.latest_assessment
                      ? formatDateTime(assessmentIntelligence.latest_assessment.assessment_date)
                      : "Sem historico estruturado"
                  }
                />
                <DetailMetric
                  label="Proxima acao"
                  value={assessmentIntelligence.next_best_action.title}
                  helper={assessmentIntelligence.next_best_action.reason}
                />
              </div>
            </div>
          </div>

          <NotesSummaryCard
            latestNote={latestNote}
            notesCount={notes.length}
            onAdd={() => setIsAddNoteOpen(true)}
            onHistory={() => setIsHistoryOpen(true)}
          />
        </div>
      </section>

      {!hasStructuredAssessment ? (
        <section className="rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4 shadow-panel">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">Sem avaliacao estruturada</h3>
          <p className="mt-1 text-sm text-lovable-ink">
            Este aluno ainda nao tem dados suficientes para leitura completa. O workspace continua funcional para registro, contexto, metas, treino e bioimpedancia.
          </p>
        </section>
      ) : null}

      <Tabs value={activeTab} onValueChange={(value) => openTab(value as AssessmentWorkspaceTab)} className="space-y-4">
        <TabsList className="flex flex-wrap gap-1">
          {ASSESSMENT_WORKSPACE_TABS.map((tab) => (
            <TabsTrigger key={tab.key} value={tab.key}>
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="overview">
          <AssessmentWorkspaceOverview
            profile={profile}
            summary={assessmentIntelligence}
            assessments={assessments}
            latestBodyComposition={latestBodyComposition}
            onOpenTab={openTab}
          />
        </TabsContent>

        <TabsContent value="registro">
          <AssessmentRegistrationComposer memberId={memberId} onSaved={() => openTab("overview")} />
        </TabsContent>

        <TabsContent value="evolucao">
          <div className="space-y-4">
            {hasEvolutionData ? (
              <EvolutionCharts evolution={evolution} />
            ) : (
              <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
                <p className="text-sm text-lovable-ink-muted">Sem dados de evolucao consolidados ainda.</p>
              </section>
            )}

            <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
              <AssessmentTimeline assessments={assessments} />
              <Card>
                <CardContent className="space-y-4 pt-5">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Ritmo operacional</p>
                    <p className="mt-2 text-sm text-lovable-ink-muted">
                      Compare a evolucao das metricas com o historico 360 e os registros de acompanhamento.
                    </p>
                  </div>
                  <div className="grid gap-3 md:grid-cols-2">
                    <DetailMetric
                      label="Check-ins recentes"
                      value={assessmentIntelligence.recent_weekly_checkins.toFixed(1)}
                      helper={`Meta semanal: ${assessmentIntelligence.target_frequency_per_week}x`}
                    />
                    <DetailMetric
                      label="Cenario corrigido"
                      value={`${assessmentIntelligence.forecast.corrected_probability_90d}%`}
                      helper="chance em 90 dias com ajuste do gargalo dominante"
                    />
                  </div>
                </CardContent>
              </Card>
            </div>

            <MemberTimeline360Content
              member={profile.member}
              events={timelineQuery.data}
              isLoading={timelineQuery.isLoading}
              isError={timelineQuery.isError}
              showContextCard={false}
            />
          </div>
        </TabsContent>

        <TabsContent value="plano">
          <div className="space-y-4">
            <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
              <MemberGoalsEditor
                memberId={memberId}
                goals={profile.goals}
                defaultAssessmentId={profile.latest_assessment?.id ?? null}
              />
              <MemberTrainingPlanEditor
                memberId={memberId}
                trainingPlan={profile.active_training_plan}
                defaultAssessmentId={profile.latest_assessment?.id ?? null}
              />
            </div>
            <GoalsProgress goals={profile.goals} />
          </div>
        </TabsContent>

        <TabsContent value="contexto">
          <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
            <div className="space-y-4">
              <MemberConstraintsEditor memberId={memberId} constraints={profile.constraints} />
              <NotesSummaryCard
                latestNote={latestNote}
                notesCount={notes.length}
                onAdd={() => setIsAddNoteOpen(true)}
                onHistory={() => setIsHistoryOpen(true)}
              />
            </div>
            <ContextSupportPanel summary={assessmentIntelligence} />
          </div>
        </TabsContent>

        <TabsContent value="bioimpedancia">
          <MemberBodyCompositionTab memberId={memberId} />
        </TabsContent>
      </Tabs>

      <Dialog
        open={isAddNoteOpen}
        onClose={() => setIsAddNoteOpen(false)}
        title="Adicionar nota interna"
        description="Ao salvar, esta nota vira a ultima nota registrada do aluno."
      >
        <div className="space-y-3">
          <Textarea
            value={noteDraft}
            onChange={(event) => setNoteDraft(event.target.value)}
            rows={5}
            placeholder="Ex: Prefere bike a esteira. Precisa de mais acompanhamento na adesao ao treino."
          />
          <div className="flex justify-end gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setIsAddNoteOpen(false);
                setNoteDraft("");
              }}
              disabled={addNoteMutation.isPending}
            >
              Cancelar
            </Button>
            <Button
              size="sm"
              variant="primary"
              onClick={() => addNoteMutation.mutate()}
              disabled={addNoteMutation.isPending || noteDraft.trim().length === 0}
            >
              {addNoteMutation.isPending ? "Salvando..." : "Salvar nota"}
            </Button>
          </div>
        </div>
      </Dialog>

      <Dialog
        open={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        title="Historico de notas"
        description="Notas anteriores da equipe para este aluno."
        size="md"
      >
        {previousNotes.length === 0 ? (
          <p className="text-sm text-lovable-ink-muted">Sem notas anteriores.</p>
        ) : (
          <ul className="max-h-80 space-y-2 overflow-y-auto pr-1">
            {previousNotes.map((note) => (
              <li key={note.id} className="rounded-lg border border-lovable-border bg-lovable-surface-soft px-3 py-2">
                <p className="text-sm text-lovable-ink">{note.text}</p>
                <p className="mt-1 text-xs text-lovable-ink-muted">{formatDateTime(note.created_at)}</p>
              </li>
            ))}
          </ul>
        )}
      </Dialog>
    </section>
  );
}
