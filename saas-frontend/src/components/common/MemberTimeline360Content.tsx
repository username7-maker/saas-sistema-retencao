import { useState } from "react";
import {
  Activity,
  AlertTriangle,
  Clipboard,
  ClipboardList,
  Dumbbell,
  ScanLine,
  ShieldAlert,
  Star,
  Target,
  Zap,
  type LucideIcon,
} from "lucide-react";
import clsx from "clsx";

import type { MemberTimelineEvent, TimelineMemberSummary } from "../../services/memberTimelineService";

type FilterKey =
  | "all"
  | "assessment"
  | "constraints"
  | "goal"
  | "training_plan"
  | "body_composition"
  | "checkin"
  | "risk_alert"
  | "nps"
  | "task"
  | "automation";

interface MemberTimeline360ContentProps {
  member: TimelineMemberSummary;
  events?: MemberTimelineEvent[];
  isLoading: boolean;
  isError?: boolean;
  showContextCard?: boolean;
}

const typeConfig: Record<string, { label: string; cardClass: string; chipClass: string; iconClass: string; icon: LucideIcon }> = {
  assessment: {
    label: "Avaliacao",
    cardClass: "border-cyan-500/25 bg-cyan-500/10",
    chipClass: "bg-cyan-500/15 text-cyan-200",
    iconClass: "text-cyan-300",
    icon: ClipboardList,
  },
  constraints: {
    label: "Restricoes",
    cardClass: "border-amber-500/25 bg-amber-500/10",
    chipClass: "bg-amber-500/15 text-amber-200",
    iconClass: "text-amber-300",
    icon: ShieldAlert,
  },
  goal: {
    label: "Objetivo",
    cardClass: "border-indigo-500/25 bg-indigo-500/10",
    chipClass: "bg-indigo-500/15 text-indigo-200",
    iconClass: "text-indigo-300",
    icon: Target,
  },
  training_plan: {
    label: "Treino",
    cardClass: "border-fuchsia-500/25 bg-fuchsia-500/10",
    chipClass: "bg-fuchsia-500/15 text-fuchsia-200",
    iconClass: "text-fuchsia-300",
    icon: Dumbbell,
  },
  body_composition: {
    label: "Bioimpedancia",
    cardClass: "border-emerald-500/25 bg-emerald-500/10",
    chipClass: "bg-emerald-500/15 text-emerald-200",
    iconClass: "text-emerald-300",
    icon: ScanLine,
  },
  checkin: {
    label: "Check-in",
    cardClass: "border-lime-500/25 bg-lime-500/10",
    chipClass: "bg-lime-500/15 text-lime-200",
    iconClass: "text-lime-300",
    icon: Activity,
  },
  risk_alert: {
    label: "Risco",
    cardClass: "border-rose-500/25 bg-rose-500/10",
    chipClass: "bg-rose-500/15 text-rose-200",
    iconClass: "text-rose-300",
    icon: AlertTriangle,
  },
  nps: {
    label: "NPS",
    cardClass: "border-orange-500/25 bg-orange-500/10",
    chipClass: "bg-orange-500/15 text-orange-200",
    iconClass: "text-orange-300",
    icon: Star,
  },
  task: {
    label: "Tarefa",
    cardClass: "border-violet-500/25 bg-violet-500/10",
    chipClass: "bg-violet-500/15 text-violet-200",
    iconClass: "text-violet-300",
    icon: Clipboard,
  },
  automation: {
    label: "Automacao",
    cardClass: "border-sky-500/25 bg-sky-500/10",
    chipClass: "bg-sky-500/15 text-sky-200",
    iconClass: "text-sky-300",
    icon: Zap,
  },
};

const filters: Array<{ key: FilterKey; label: string; eventTypes?: string[] }> = [
  { key: "all", label: "Tudo" },
  { key: "assessment", label: "Avaliacoes", eventTypes: ["assessment"] },
  { key: "constraints", label: "Restricoes", eventTypes: ["constraints"] },
  { key: "goal", label: "Objetivos", eventTypes: ["goal"] },
  { key: "training_plan", label: "Treinos", eventTypes: ["training_plan"] },
  { key: "body_composition", label: "Bio", eventTypes: ["body_composition"] },
  { key: "checkin", label: "Check-ins", eventTypes: ["checkin"] },
  { key: "risk_alert", label: "Risco", eventTypes: ["risk_alert"] },
  { key: "task", label: "Tarefas", eventTypes: ["task"] },
  { key: "automation", label: "Automacoes", eventTypes: ["automation"] },
  { key: "nps", label: "NPS", eventTypes: ["nps"] },
];

function formatTimestamp(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return "Data indisponivel";
  }
  return new Date(parsed).toLocaleString("pt-BR", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatRelativeTimestamp(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return "";
  }
  const diffMs = Date.now() - parsed;
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);
  if (diffHours < 1) {
    return "Agora";
  }
  if (diffHours < 24) {
    return `${diffHours}h atras`;
  }
  if (diffDays === 1) {
    return "Ontem";
  }
  if (diffDays < 30) {
    return `${diffDays} dias atras`;
  }
  const diffMonths = Math.floor(diffDays / 30);
  return `${diffMonths} mes${diffMonths > 1 ? "es" : ""} atras`;
}

function formatBucket(value: string): string {
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) {
    return "Sem data";
  }
  return new Date(parsed).toLocaleDateString("pt-BR", {
    month: "long",
    year: "numeric",
  });
}

function riskPillClass(level: string): string {
  if (level === "red") {
    return "bg-lovable-danger/20 text-lovable-danger";
  }
  if (level === "yellow") {
    return "bg-lovable-warning/20 text-lovable-warning";
  }
  return "bg-lovable-success/20 text-lovable-success";
}

function riskLabel(level: string): string {
  if (level === "red") {
    return "Risco alto";
  }
  if (level === "yellow") {
    return "Risco medio";
  }
  return "Risco baixo";
}

function countByTypes(events: MemberTimelineEvent[], eventTypes?: string[]): number {
  if (!eventTypes) {
    return events.length;
  }
  return events.filter((event) => eventTypes.includes(event.type)).length;
}

function filterEvents(events: MemberTimelineEvent[], selectedFilter: FilterKey): MemberTimelineEvent[] {
  if (selectedFilter === "all") {
    return events;
  }
  const selected = filters.find((item) => item.key === selectedFilter);
  if (!selected?.eventTypes) {
    return events;
  }
  return events.filter((event) => selected.eventTypes?.includes(event.type));
}

function getIconConfig(event: MemberTimelineEvent): { icon: LucideIcon; label: string; cardClass: string; chipClass: string; iconClass: string } {
  return typeConfig[event.type] ?? {
    label: event.type,
    cardClass: "border-lovable-border bg-lovable-surface-soft",
    chipClass: "bg-lovable-surface-soft text-lovable-ink-muted",
    iconClass: "text-lovable-ink-muted",
    icon: Activity,
  };
}

export function MemberTimeline360Content({
  member,
  events,
  isLoading,
  isError = false,
  showContextCard = true,
}: MemberTimeline360ContentProps) {
  const [selectedFilter, setSelectedFilter] = useState<FilterKey>("all");
  const allEvents = events ?? [];
  const visibleEvents = filterEvents(allEvents, selectedFilter);

  return (
    <div className="space-y-4">
      {showContextCard ? (
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Timeline 360</p>
              <h3 className="mt-1 text-2xl font-semibold text-lovable-ink">{member.full_name}</h3>
              <p className="mt-1 text-sm text-lovable-ink-muted">
                {member.plan_name}
                {member.email ? ` | ${member.email}` : ""}
              </p>
            </div>
            <div className="flex flex-wrap gap-2">
              <span className={`rounded-full px-3 py-1 text-xs font-semibold ${riskPillClass(member.risk_level)}`}>
                {riskLabel(member.risk_level)} ({member.risk_score})
              </span>
              {member.last_checkin_at ? (
                <span className="rounded-full bg-lovable-surface-soft px-3 py-1 text-xs font-semibold text-lovable-ink-muted">
                  Ultimo check-in: {formatRelativeTimestamp(member.last_checkin_at)}
                </span>
              ) : null}
            </div>
          </div>
        </section>
      ) : null}

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Eventos</p>
          <p className="mt-2 text-3xl font-semibold text-lovable-ink">{allEvents.length}</p>
          <p className="text-xs text-lovable-ink-muted">consolidado do aluno</p>
        </article>
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Operacao</p>
          <p className="mt-2 text-3xl font-semibold text-lovable-ink">
            {countByTypes(allEvents, ["task", "automation", "risk_alert"])}
          </p>
          <p className="text-xs text-lovable-ink-muted">riscos, tarefas e automacoes</p>
        </article>
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Treino e Evolucao</p>
          <p className="mt-2 text-3xl font-semibold text-lovable-ink">
            {countByTypes(allEvents, ["assessment", "body_composition", "goal", "training_plan"])}
          </p>
          <p className="text-xs text-lovable-ink-muted">avaliacao, bio, meta e treino</p>
        </article>
        <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Frequencia</p>
          <p className="mt-2 text-3xl font-semibold text-lovable-ink">{countByTypes(allEvents, ["checkin"])}</p>
          <p className="text-xs text-lovable-ink-muted">check-ins registrados</p>
        </article>
      </section>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Feed unificado</h3>
            <p className="mt-1 text-sm text-lovable-ink-muted">Uma leitura unica da jornada do aluno, em ordem cronologica, com filtros por assunto.</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {filters.map((filter) => (
            <button
              key={filter.key}
              type="button"
              onClick={() => setSelectedFilter(filter.key)}
              className={clsx(
                "rounded-full px-3 py-1.5 text-xs font-semibold uppercase tracking-wider transition",
                selectedFilter === filter.key
                  ? "bg-lovable-primary-soft text-lovable-primary"
                  : "bg-lovable-surface-soft text-lovable-ink-muted hover:bg-lovable-surface-soft",
              )}
            >
              {filter.label} ({countByTypes(allEvents, filter.eventTypes)})
            </button>
          ))}
        </div>

        {isLoading ? (
          <div className="mt-6 space-y-3">
            {[1, 2, 3, 4].map((item) => (
              <div key={item} className="animate-pulse rounded-2xl border border-lovable-border bg-lovable-surface-soft p-4">
                <div className="h-3 w-40 rounded bg-lovable-surface" />
                <div className="mt-3 h-2 w-60 rounded bg-lovable-surface" />
              </div>
            ))}
          </div>
        ) : null}

        {isError ? (
          <div className="mt-6 rounded-2xl border border-lovable-danger/30 bg-lovable-danger/10 p-4 text-sm text-lovable-danger">
            Nao foi possivel carregar a timeline 360.
          </div>
        ) : null}

        {!isLoading && !isError && visibleEvents.length === 0 ? (
          <div className="mt-6 rounded-2xl border border-dashed border-lovable-border bg-lovable-surface-soft p-5 text-sm text-lovable-ink-muted">
            Nenhum evento encontrado para este filtro.
          </div>
        ) : null}

        {!isLoading && !isError && visibleEvents.length > 0 ? (
          <div className="relative mt-6 space-y-4 pl-6 before:absolute before:left-[11px] before:top-0 before:h-full before:w-px before:bg-gradient-to-b before:from-lovable-primary/50 before:via-lovable-border before:to-transparent">
            {(() => {
              let lastBucket = "";
              return visibleEvents.map((event, index) => {
                const bucket = formatBucket(event.timestamp);
                const showBucket = bucket !== lastBucket;
                lastBucket = bucket;
                const config = getIconConfig(event);
                const Icon = config.icon;

                return (
                  <div key={`${event.type}-${event.timestamp}-${index}`} className="space-y-2">
                    {showBucket ? (
                      <div className="pl-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-lovable-ink-muted">
                        {bucket}
                      </div>
                    ) : null}
                    <article className={clsx("relative rounded-2xl border p-4 shadow-panel", config.cardClass)}>
                      <div className="absolute -left-[26px] top-5 flex h-6 w-6 items-center justify-center rounded-full border border-lovable-border bg-lovable-surface shadow-sm">
                        <Icon size={14} className={config.iconClass} />
                      </div>

                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className={clsx("rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider", config.chipClass)}>
                              {config.label}
                            </span>
                            {event.level ? (
                              <span className={`rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${riskPillClass(event.level)}`}>
                                {event.level}
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-3 text-base font-semibold text-lovable-ink">{event.title}</p>
                          {event.detail ? <p className="mt-1 text-sm leading-6 text-lovable-ink-muted">{event.detail}</p> : null}
                        </div>

                        <div className="shrink-0 rounded-xl border border-lovable-border bg-lovable-surface/70 px-3 py-2 text-right">
                          <p className="text-[11px] font-semibold uppercase tracking-wider text-lovable-primary">{formatRelativeTimestamp(event.timestamp)}</p>
                          <p className="mt-1 text-xs text-lovable-ink-muted">{formatTimestamp(event.timestamp)}</p>
                        </div>
                      </div>
                    </article>
                  </div>
                );
              });
            })()}
          </div>
        ) : null}
      </section>
    </div>
  );
}
