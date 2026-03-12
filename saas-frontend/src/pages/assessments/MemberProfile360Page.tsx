import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { AxiosError } from "axios";
import toast from "react-hot-toast";

import { AssessmentTimeline } from "../../components/assessments/AssessmentTimeline";
import { ConstraintsAlert } from "../../components/assessments/ConstraintsAlert";
import { EvolutionCharts } from "../../components/assessments/EvolutionCharts";
import { GoalsProgress } from "../../components/assessments/GoalsProgress";
import { MemberBodyCompositionTab } from "../../components/assessments/MemberBodyCompositionTab";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Button, Dialog, Textarea } from "../../components/ui2";
import { assessmentService, type AssessmentSummary360 } from "../../services/assessmentService";
import { memberService } from "../../services/memberService";

type ProfileTab = "summary" | "diagnosis" | "evolution" | "constraints" | "goals" | "training" | "actions" | "bioimpedancia";

interface InternalNote {
  id: string;
  text: string;
  created_at: string;
}

interface ApiErrorPayload {
  detail?: string;
}

const tabs: Array<{ key: ProfileTab; label: string }> = [
  { key: "summary", label: "Resumo" },
  { key: "diagnosis", label: "Diagnostico IA" },
  { key: "evolution", label: "Evolucao" },
  { key: "constraints", label: "Restricoes" },
  { key: "goals", label: "Objetivos" },
  { key: "training", label: "Treino" },
  { key: "actions", label: "Acoes" },
  { key: "bioimpedancia", label: "Bioimpedancia" },
];

function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((part) => part[0]?.toUpperCase() ?? "").join("") || "AL";
}

function normalizeDate(value: unknown): Date | null {
  if (typeof value !== "string") return null;
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return null;
  return new Date(parsed);
}

function getAge(extraData: Record<string, unknown> | undefined): number | null {
  if (!extraData) return null;

  const directAge = extraData.age;
  if (typeof directAge === "number" && Number.isFinite(directAge) && directAge > 0) {
    return Math.floor(directAge);
  }

  const birthDate = normalizeDate(extraData.birth_date);
  if (!birthDate) return null;

  const now = new Date();
  let age = now.getFullYear() - birthDate.getFullYear();
  const monthDiff = now.getMonth() - birthDate.getMonth();
  if (monthDiff < 0 || (monthDiff === 0 && now.getDate() < birthDate.getDate())) {
    age -= 1;
  }
  return age >= 0 ? age : null;
}

function daysSince(dateValue: string | null | undefined): number | null {
  if (!dateValue) return null;
  const parsed = Date.parse(dateValue);
  if (Number.isNaN(parsed)) return null;
  return Math.floor((Date.now() - parsed) / (1000 * 60 * 60 * 24));
}

function riskBadgeClass(riskLevel: string): string {
  if (riskLevel === "red") return "bg-lovable-danger/20 text-lovable-danger";
  if (riskLevel === "yellow") return "bg-lovable-warning/25 text-lovable-warning";
  return "bg-lovable-success/20 text-lovable-success";
}

function riskLabel(riskLevel: string): string {
  if (riskLevel === "red") return "Risco de cancelamento: Alto";
  if (riskLevel === "yellow") return "Risco de cancelamento: Medio";
  return "Risco de cancelamento: Baixo";
}

function statusBadgeClass(status: AssessmentSummary360["status"]): string {
  if (status === "critical") return "bg-lovable-danger/20 text-lovable-danger";
  if (status === "attention") return "bg-lovable-warning/25 text-lovable-warning";
  return "bg-lovable-success/20 text-lovable-success";
}

function statusLabel(status: AssessmentSummary360["status"]): string {
  if (status === "critical") return "Meta em risco";
  if (status === "attention") return "Atencao operacional";
  return "Na curva esperada";
}

function formatGoalType(goalType: string): string {
  if (goalType === "fat_loss") return "Perda de gordura";
  if (goalType === "muscle_gain") return "Ganho de massa";
  if (goalType === "performance") return "Performance";
  return "Geral";
}

function formatDate(value: string | null | undefined): string {
  if (!value) return "Sem data";
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return "Sem data";
  return new Date(parsed).toLocaleDateString("pt-BR");
}

function computeTrainingStatus(plan: {
  is_active: boolean;
  end_date: string | null;
} | null): { label: string; className: string } {
  if (!plan) {
    return { label: "Sem treino", className: "bg-lovable-surface-soft text-lovable-ink-muted" };
  }

  if (!plan.is_active) {
    return { label: "Treino vencido", className: "bg-lovable-danger/20 text-lovable-danger" };
  }

  if (!plan.end_date) {
    return { label: "Treino ativo", className: "bg-lovable-success/20 text-lovable-success" };
  }

  const endDate = Date.parse(plan.end_date);
  if (Number.isNaN(endDate)) {
    return { label: "Treino ativo", className: "bg-lovable-success/20 text-lovable-success" };
  }

  const daysToExpire = Math.ceil((endDate - Date.now()) / (1000 * 60 * 60 * 24));
  if (daysToExpire < 0) {
    return { label: "Treino vencido", className: "bg-lovable-danger/20 text-lovable-danger" };
  }
  if (daysToExpire <= 5) {
    return { label: `Vence em ${daysToExpire} dia(s)`, className: "bg-lovable-warning/25 text-lovable-warning" };
  }

  return { label: "Treino ativo", className: "bg-lovable-success/20 text-lovable-success" };
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
  if (typeof window === "undefined") {
    return [];
  }
  const raw = window.localStorage.getItem(getLocalNotesStorageKey(memberId));
  if (!raw) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
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
  if (typeof window === "undefined") {
    return;
  }
  window.localStorage.setItem(getLocalNotesStorageKey(memberId), JSON.stringify(notes));
}

function formatDateTime(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return "-";
  return new Date(parsed).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function MemberProfile360Page() {
  const { memberId } = useParams<{ memberId: string }>();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<ProfileTab>("summary");
  const [noteDraft, setNoteDraft] = useState("");
  const [isAddNoteOpen, setIsAddNoteOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

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

  const addNoteMutation = useMutation({
    mutationFn: async () => {
      if (!memberId) {
        throw new Error("MEMBRO_INVALIDO");
      }
      const text = noteDraft.trim();
      if (!text) {
        throw new Error("NOTA_VAZIA");
      }

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
        if (!current || typeof current !== "object") {
          return current;
        }
        const currentObj = current as Record<string, unknown>;
        const currentMember = currentObj.member;
        if (!currentMember || typeof currentMember !== "object") {
          return current;
        }
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
      // Evita sobrescrever a nota recem salva quando o backend nao retorna extra_data no payload de profile.
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
    return <LoadingPanel text="Carregando perfil 360..." />;
  }

  if (profileQuery.isError || assessmentsQuery.isError || evolutionQuery.isError || summary360Query.isError) {
    return <LoadingPanel text="Erro ao carregar perfil 360. Tente novamente." />;
  }

  if (!profileQuery.data || !summary360Query.data) {
    return <LoadingPanel text="Perfil 360 indisponivel." />;
  }

  const profile = profileQuery.data;
  const assessments = assessmentsQuery.data ?? [];
  const evolution = evolutionQuery.data;
  const assessmentIntelligence = summary360Query.data;
  const memberExtra = profile.member.extra_data ?? {};
  const apiNotes = parseInternalNotes(memberExtra);
  const localNotes = memberId ? parseInternalNotesFromStorage(memberId) : [];
  const notes = apiNotes.length > 0 ? apiNotes : localNotes;
  const latestNote = notes[0] ?? null;
  const previousNotes = notes.slice(1);

  const age = getAge(memberExtra);
  const photoUrl = typeof memberExtra.photo_url === "string" ? memberExtra.photo_url : null;
  const daysWithoutCheckin = daysSince(profile.member.last_checkin_at);
  const trainingStatus = computeTrainingStatus(profile.active_training_plan);

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Perfil 360</h2>
          <p className="text-sm text-lovable-ink-muted">Visao integrada para decisao rapida de treino e retencao.</p>
        </div>
        <div className="flex gap-2">
          <Link
            to="/assessments"
            className="rounded-full border border-lovable-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted hover:bg-lovable-surface-soft"
          >
            Voltar
          </Link>
          <Link
            to={`/assessments/new/${memberId}`}
            className="rounded-full bg-lovable-primary px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-white hover:brightness-105"
          >
            Nova avaliacao
          </Link>
        </div>
      </header>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr]">
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

            <div className="space-y-2">
              <p className="text-2xl font-semibold text-lovable-ink">{profile.member.full_name}</p>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full bg-lovable-surface-soft px-3 py-1 text-xs font-semibold text-lovable-ink-muted">
                  {age !== null ? `${age} anos` : "Idade nao informada"}
                </span>
                <span className={`rounded-full px-3 py-1 text-xs font-semibold ${riskBadgeClass(profile.member.risk_level)}`}>
                  {riskLabel(profile.member.risk_level)}
                </span>
                <span className="rounded-full bg-lovable-surface-soft px-3 py-1 text-xs font-semibold text-lovable-ink-muted">
                  {daysWithoutCheckin === null
                    ? "Sem check-in registrado"
                    : daysWithoutCheckin === 0
                      ? "Ultimo check-in: hoje"
                      : `${daysWithoutCheckin} dia(s) desde ultimo check-in`}
                </span>
              </div>
              <p className="text-sm text-lovable-ink-muted">
                Plano: {profile.member.plan_name}
                {profile.member.email ? ` | ${profile.member.email}` : ""}
              </p>
              <article className="rounded-lg border border-lovable-border bg-lovable-surface-soft px-3 py-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-lovable-ink-muted">
                  Ultima nota registrada
                </p>
                {latestNote ? (
                  <>
                    <p className="mt-1 text-xs text-lovable-ink">{latestNote.text}</p>
                    <p className="mt-1 text-[10px] text-lovable-ink-muted">{formatDateTime(latestNote.created_at)}</p>
                  </>
                ) : (
                  <p className="mt-1 text-xs text-lovable-ink-muted">Nenhuma nota registrada.</p>
                )}
              </article>
            </div>
          </div>

          <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Notas internas dos professores</p>
            <p className="mt-2 text-xs text-lovable-ink-muted">
              Registre observacoes comportamentais e acompanhe o historico cronologico das notas.
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <Button size="sm" variant="primary" onClick={() => setIsAddNoteOpen(true)}>
                + Add nota
              </Button>
              <Button size="sm" variant="secondary" onClick={() => setIsHistoryOpen(true)}>
                Historico
              </Button>
            </div>
            <p className="mt-3 text-[11px] text-lovable-ink-muted">{notes.length} nota(s) registrada(s).</p>
          </div>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Status da meta</p>
          <div className="mt-2 flex items-center gap-2">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${statusBadgeClass(assessmentIntelligence.status)}`}>
              {statusLabel(assessmentIntelligence.status)}
            </span>
          </div>
          <p className="mt-3 text-2xl font-semibold text-lovable-ink">{assessmentIntelligence.forecast.probability_60d}%</p>
          <p className="text-xs text-lovable-ink-muted">chance de meta em 60 dias</p>
        </article>
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Gargalo principal</p>
          <p className="mt-3 text-lg font-semibold text-lovable-ink">{assessmentIntelligence.diagnosis.primary_bottleneck_label}</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">Meta: {formatGoalType(assessmentIntelligence.goal_type)}</p>
        </article>
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Risco de frustracao</p>
          <p className="mt-3 text-2xl font-semibold text-lovable-ink">{assessmentIntelligence.diagnosis.frustration_risk}</p>
          <p className="text-xs text-lovable-ink-muted">score de 0 a 100</p>
        </article>
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Benchmark</p>
          <p className="mt-3 text-lg font-semibold text-lovable-ink">{assessmentIntelligence.benchmark.position_label}</p>
          <p className="text-xs text-lovable-ink-muted">{assessmentIntelligence.benchmark.percentile} percentil no cohort</p>
        </article>
      </section>

      <section className="grid gap-3 xl:grid-cols-[1.2fr_0.8fr]">
        <article className="rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">Narrativa para a equipe</p>
          <p className="mt-2 text-sm text-lovable-ink">{assessmentIntelligence.narratives.coach_summary}</p>
          <p className="mt-3 text-xs text-lovable-ink-muted">{assessmentIntelligence.forecast.current_summary}</p>
          <p className="mt-1 text-xs text-lovable-ink-muted">{assessmentIntelligence.forecast.corrected_summary}</p>
        </article>
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Proxima melhor acao</p>
          <p className="mt-2 text-base font-semibold text-lovable-ink">{assessmentIntelligence.next_best_action.title}</p>
          <p className="mt-1 text-sm text-lovable-ink-muted">{assessmentIntelligence.next_best_action.reason}</p>
          <p className="mt-3 text-xs text-lovable-primary">{assessmentIntelligence.next_best_action.suggested_message}</p>
        </article>
      </section>

      {profile.insight_summary ? (
        <section className="rounded-2xl border border-lovable-border bg-lovable-primary-soft p-4 shadow-panel">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-lovable-primary">Insight da avaliacao</h3>
          <p className="mt-1 text-sm text-lovable-ink">{profile.insight_summary}</p>
        </section>
      ) : null}

      <nav className="flex flex-wrap gap-2">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wider ${
              activeTab === tab.key
                ? "bg-lovable-primary-soft text-lovable-primary"
                : "bg-lovable-surface-soft text-lovable-ink-muted hover:bg-lovable-surface-soft"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      {activeTab === "summary" && (
        <div className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <AssessmentTimeline assessments={assessments} />
          <section className="space-y-4 rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para o aluno</p>
              <p className="mt-2 text-sm text-lovable-ink">{assessmentIntelligence.narratives.member_summary}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo para retencao</p>
              <p className="mt-2 text-sm text-lovable-ink">{assessmentIntelligence.narratives.retention_summary}</p>
            </div>
          </section>
        </div>
      )}

      {activeTab === "diagnosis" && (
        <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
          <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Diagnostico causal</h3>
            <p className="mt-3 text-lg font-semibold text-lovable-ink">{assessmentIntelligence.diagnosis.primary_bottleneck_label}</p>
            <p className="mt-1 text-sm text-lovable-ink-muted">Secundario: {assessmentIntelligence.diagnosis.secondary_bottleneck_label}</p>
            <p className="mt-3 text-sm text-lovable-ink">{assessmentIntelligence.diagnosis.explanation}</p>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Fatores de evolucao</p>
                <ul className="mt-2 space-y-1 text-sm text-lovable-ink">
                  {assessmentIntelligence.diagnosis.evolution_factors.map((item) => (
                    <li key={item}>- {item}</li>
                  ))}
                </ul>
              </article>
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Fatores de estagnacao</p>
                <ul className="mt-2 space-y-1 text-sm text-lovable-ink">
                  {assessmentIntelligence.diagnosis.stagnation_factors.map((item) => (
                    <li key={item}>- {item}</li>
                  ))}
                </ul>
              </article>
            </div>
          </article>

          <aside className="space-y-4">
            <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Scores de leitura</h3>
              <ul className="mt-3 space-y-2">
                {assessmentIntelligence.diagnosis.factors.map((factor) => (
                  <li key={factor.key} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2">
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm font-medium text-lovable-ink">{factor.label}</span>
                      <span className="text-xs font-semibold text-lovable-primary">{factor.score}</span>
                    </div>
                    <p className="mt-1 text-xs text-lovable-ink-muted">{factor.reason}</p>
                  </li>
                ))}
              </ul>
            </article>

            <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Benchmark</h3>
              <p className="mt-3 text-lg font-semibold text-lovable-ink">{assessmentIntelligence.benchmark.position_label}</p>
              <p className="mt-1 text-sm text-lovable-ink-muted">{assessmentIntelligence.benchmark.explanation}</p>
              <p className="mt-3 text-xs text-lovable-ink-muted">
                {assessmentIntelligence.benchmark.sample_size} perfis analisados - media do cohort {assessmentIntelligence.benchmark.peer_average_score ?? "-"}
              </p>
            </article>
          </aside>
        </section>
      )}

      {activeTab === "evolution" &&
        (evolution ? (
          <EvolutionCharts evolution={evolution} />
        ) : (
          <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
            <p className="text-sm text-lovable-ink-muted">Sem dados de evolucao.</p>
          </section>
        ))}

      {activeTab === "constraints" && <ConstraintsAlert constraints={profile.constraints} />}

      {activeTab === "goals" && <GoalsProgress goals={profile.goals} />}

      {activeTab === "training" && (
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Resumo do treino atual</h3>
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold ${trainingStatus.className}`}>{trainingStatus.label}</span>
          </div>

          {profile.active_training_plan ? (
            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Divisao</p>
                <p className="mt-1 text-sm font-semibold text-lovable-ink">{profile.active_training_plan.split_type ?? "Nao informado"}</p>
              </article>
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Foco</p>
                <p className="mt-1 text-sm font-semibold text-lovable-ink">{profile.active_training_plan.objective ?? "Nao informado"}</p>
              </article>
              <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Vencimento</p>
                <p className="mt-1 text-sm font-semibold text-lovable-ink">{formatDate(profile.active_training_plan.end_date)}</p>
              </article>
            </div>
          ) : (
            <p className="mt-3 text-sm text-lovable-ink-muted">Aluno sem ficha de treino ativa no momento.</p>
          )}
        </section>
      )}

      {activeTab === "actions" && (
        <section className="grid gap-4 xl:grid-cols-[1fr_1fr]">
          <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Acoes recomendadas</h3>
            <ul className="mt-4 space-y-3">
              {assessmentIntelligence.actions.map((action) => (
                <li key={action.key} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-semibold text-lovable-ink">{action.title}</p>
                      <p className="mt-1 text-xs text-lovable-ink-muted">{action.reason}</p>
                    </div>
                    <span className="rounded-full bg-lovable-primary-soft px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-lovable-primary">
                      {action.priority}
                    </span>
                  </div>
                  <p className="mt-3 text-xs text-lovable-primary">{action.suggested_message}</p>
                  <p className="mt-2 text-[11px] text-lovable-ink-muted">Responsavel sugerido: {action.owner_role} - prazo: D+{action.due_in_days}</p>
                </li>
              ))}
            </ul>
          </article>
          <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Leitura operacional</h3>
            <div className="mt-4 space-y-3">
              <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Consistencia atual</p>
                <p className="mt-1 text-xl font-semibold text-lovable-ink">
                  {assessmentIntelligence.recent_weekly_checkins.toFixed(1)} / {assessmentIntelligence.target_frequency_per_week}x semana
                </p>
              </div>
              <div className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
                <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Cenario corrigido</p>
                <p className="mt-1 text-xl font-semibold text-lovable-ink">{assessmentIntelligence.forecast.corrected_probability_90d}%</p>
                <p className="text-xs text-lovable-ink-muted">chance de meta em 90 dias se a equipe corrigir o gargalo dominante</p>
              </div>
            </div>
          </article>
        </section>
      )}

      {activeTab === "bioimpedancia" && memberId && <MemberBodyCompositionTab memberId={memberId} />}

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
            placeholder="Ex: Odeia esteira, prefere bike. Tem medo de agachamento livre. Gosta de ser corrigido."
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

