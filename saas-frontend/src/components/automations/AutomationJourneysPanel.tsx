import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Eye,
  ListTodo,
  Pause,
  Play,
  RefreshCw,
  Route,
  Users,
} from "lucide-react";
import toast from "react-hot-toast";
import clsx from "clsx";

import { LoadingPanel } from "../common/LoadingPanel";
import { Button } from "../ui2";
import { automationJourneyService } from "../../services/automationJourneyService";
import type { AutomationJourney, AutomationJourneyPreview, AutomationJourneyTemplate } from "../../types";

const DOMAIN_LABELS: Record<string, string> = {
  onboarding: "Onboarding",
  retention: "Retencao",
  nps: "NPS",
  renewal: "Renovacao",
  finance: "Financeiro",
  commercial: "Comercial",
  upsell: "Upsell",
};

const DOMAIN_ACCENTS: Record<string, string> = {
  onboarding: "#9B5CF6",
  retention: "#E58B2A",
  nps: "#E24B4A",
  renewal: "#185FA5",
  finance: "#1D9E75",
  commercial: "#4B7BE5",
  upsell: "#0F7553",
};

function pct(value: number, total: number): string {
  if (!total) return "0%";
  return `${Math.round((value / total) * 100)}%`;
}

function TemplateCard({
  template,
  selected,
  onSelect,
}: {
  template: AutomationJourneyTemplate;
  selected: boolean;
  onSelect: () => void;
}) {
  const accent = DOMAIN_ACCENTS[template.domain] ?? "#7C3DB3";
  return (
    <button
      type="button"
      onClick={onSelect}
      className={clsx(
        "rounded-2xl border p-4 text-left transition",
        selected
          ? "border-lovable-primary bg-lovable-primary/10 shadow-sm"
          : "border-lovable-border bg-lovable-surface hover:border-lovable-primary/50",
      )}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <span
          className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
          style={{ background: `${accent}20`, color: accent }}
        >
          {DOMAIN_LABELS[template.domain] ?? template.domain}
        </span>
        <span className="text-xs text-lovable-ink-muted">{template.steps.length} etapas</span>
      </div>
      <p className="text-sm font-bold text-lovable-ink">{template.name}</p>
      <p className="mt-1 text-xs leading-relaxed text-lovable-ink-muted">{template.description}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {template.steps.slice(0, 3).map((step) => (
          <span key={step.name} className="rounded-full border border-lovable-border px-2 py-1 text-[10px] text-lovable-ink-muted">
            D+{step.delay_days} · {step.owner_role ?? "staff"}
          </span>
        ))}
      </div>
    </button>
  );
}

function JourneyCard({
  journey,
  onActivate,
  onPause,
  onPreview,
  isBusy,
}: {
  journey: AutomationJourney;
  onActivate: () => void;
  onPause: () => void;
  onPreview: () => void;
  isBusy: boolean;
}) {
  const accent = DOMAIN_ACCENTS[journey.domain] ?? "#7C3DB3";
  const totalOutcomes = journey.positive_outcomes_total + journey.neutral_outcomes_total + journey.negative_outcomes_total;
  return (
    <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span
              className="rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider"
              style={{ background: `${accent}20`, color: accent }}
            >
              {DOMAIN_LABELS[journey.domain] ?? journey.domain}
            </span>
            <span className={clsx(
              "rounded-full px-2.5 py-1 text-[10px] font-bold uppercase",
              journey.is_active ? "bg-emerald-500/15 text-emerald-400" : "bg-lovable-surface-soft text-lovable-ink-muted",
            )}>
              {journey.is_active ? "Ativa" : "Pausada"}
            </span>
            <span className="rounded-full bg-amber-500/15 px-2.5 py-1 text-[10px] font-bold uppercase text-amber-400">
              Sem envio automatico
            </span>
          </div>
          <h3 className="text-base font-bold text-lovable-ink">{journey.name}</h3>
          {journey.description && <p className="mt-1 text-sm text-lovable-ink-muted">{journey.description}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button variant="ghost" onClick={onPreview} disabled={isBusy}>
            <Eye size={14} />Preview
          </Button>
          {journey.is_active ? (
            <Button variant="ghost" onClick={onPause} disabled={isBusy}>
              <Pause size={14} />Pausar
            </Button>
          ) : (
            <Button variant="primary" onClick={onActivate} disabled={isBusy}>
              <Play size={14} />Ativar
            </Button>
          )}
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 md:grid-cols-5">
        {[
          { label: "Inscritos", value: journey.enrollments_total, icon: Users },
          { label: "Aguardando", value: journey.awaiting_outcome_total, icon: Clock },
          { label: "Tasks criadas", value: journey.tasks_created_total, icon: ListTodo },
          { label: "Outcome +", value: journey.positive_outcomes_total, icon: CheckCircle2 },
          { label: "Execucao", value: pct(totalOutcomes, Math.max(journey.tasks_created_total, 1)), icon: Activity },
        ].map((metric) => (
          <div key={metric.label} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <div className="mb-1 flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-wider text-lovable-ink-muted">
              <metric.icon size={11} />{metric.label}
            </div>
            <p className="text-lg font-black text-lovable-ink">{metric.value}</p>
          </div>
        ))}
      </div>
    </article>
  );
}

function PreviewBox({ preview }: { preview: AutomationJourneyPreview | null }) {
  if (!preview) return null;
  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-4">
      <div className="mb-3 flex items-center gap-2">
        <Users size={16} className="text-lovable-primary" />
        <p className="text-sm font-bold text-lovable-ink">Preview de impacto</p>
        <span className="rounded-full bg-lovable-primary/15 px-2 py-0.5 text-xs font-bold text-lovable-primary">
          {preview.eligible_count} elegiveis
        </span>
      </div>
      {preview.warnings.length > 0 && (
        <div className="mb-3 rounded-xl border border-amber-500/25 bg-amber-500/10 p-3">
          {preview.warnings.map((warning) => (
            <p key={warning} className="flex items-start gap-2 text-xs text-amber-300">
              <AlertTriangle size={13} className="mt-0.5 shrink-0" />
              {warning}
            </p>
          ))}
        </div>
      )}
      {preview.sample.length === 0 ? (
        <p className="text-sm text-lovable-ink-muted">Nenhum aluno ou lead elegivel agora.</p>
      ) : (
        <div className="grid gap-2 md:grid-cols-2">
          {preview.sample.map((item) => (
            <div key={item.id} className="rounded-xl border border-lovable-border bg-lovable-surface-soft px-3 py-2">
              <p className="text-sm font-semibold text-lovable-ink">{item.name}</p>
              <p className="text-xs text-lovable-ink-muted">
                {item.kind} {item.preferred_shift ? `· turno ${item.preferred_shift}` : ""} {item.reason ? `· ${item.reason}` : ""}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function AutomationJourneysPanel() {
  const queryClient = useQueryClient();
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null);
  const [preview, setPreview] = useState<AutomationJourneyPreview | null>(null);

  const templatesQuery = useQuery({
    queryKey: ["automation-journeys", "templates"],
    queryFn: () => automationJourneyService.listTemplates(),
    staleTime: 60_000,
  });
  const journeysQuery = useQuery({
    queryKey: ["automation-journeys", "list"],
    queryFn: () => automationJourneyService.listJourneys(),
    staleTime: 30_000,
  });

  const selectedTemplate = useMemo(
    () => templatesQuery.data?.find((item) => item.id === selectedTemplateId) ?? null,
    [selectedTemplateId, templatesQuery.data],
  );

  const previewMutation = useMutation({
    mutationFn: (templateId: string) => automationJourneyService.previewTemplate(templateId),
    onSuccess: (data) => setPreview(data),
    onError: () => toast.error("Nao foi possivel gerar preview da jornada."),
  });

  const journeyPreviewMutation = useMutation({
    mutationFn: (journeyId: string) => automationJourneyService.previewJourney(journeyId),
    onSuccess: (data) => setPreview(data),
    onError: () => toast.error("Nao foi possivel gerar preview da jornada."),
  });

  const createMutation = useMutation({
    mutationFn: (templateId: string) => automationJourneyService.createFromTemplate(templateId),
    onSuccess: (journey) => {
      toast.success("Jornada criada. Revise e ative quando quiser.");
      void queryClient.invalidateQueries({ queryKey: ["automation-journeys"] });
      void journeyPreviewMutation.mutate(journey.id);
    },
    onError: () => toast.error("Erro ao criar jornada."),
  });

  const activateMutation = useMutation({
    mutationFn: (journeyId: string) => automationJourneyService.activateJourney(journeyId),
    onSuccess: (result) => {
      toast.success(`${result.enrolled_count} inscricoes novas na jornada.`);
      void queryClient.invalidateQueries({ queryKey: ["automation-journeys"] });
    },
    onError: () => toast.error("Erro ao ativar jornada."),
  });

  const pauseMutation = useMutation({
    mutationFn: (journeyId: string) => automationJourneyService.pauseJourney(journeyId),
    onSuccess: () => {
      toast.success("Jornada pausada.");
      void queryClient.invalidateQueries({ queryKey: ["automation-journeys"] });
    },
    onError: () => toast.error("Erro ao pausar jornada."),
  });

  if (templatesQuery.isLoading || journeysQuery.isLoading) {
    return <LoadingPanel text="Carregando jornadas..." />;
  }

  if (templatesQuery.isError || journeysQuery.isError) {
    return <LoadingPanel text="Erro ao carregar jornadas." />;
  }

  const templates = templatesQuery.data ?? [];
  const journeys = journeysQuery.data ?? [];
  const activeJourneys = journeys.filter((journey) => journey.is_active).length;
  const totalTasks = journeys.reduce((sum, journey) => sum + journey.tasks_created_total, 0);
  const waiting = journeys.reduce((sum, journey) => sum + journey.awaiting_outcome_total, 0);
  const busy = createMutation.isPending || activateMutation.isPending || pauseMutation.isPending || previewMutation.isPending || journeyPreviewMutation.isPending;

  return (
    <div className="space-y-5">
      <div className="rounded-3xl border border-lovable-border bg-lovable-surface p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="mb-2 flex items-center gap-2">
              <Route size={18} className="text-lovable-primary" />
              <h3 className="text-xl font-black text-lovable-ink">Jornadas prontas</h3>
            </div>
            <p className="max-w-3xl text-sm text-lovable-ink-muted">
              Jornadas criam tarefas operacionais por ciclo de vida. A equipe executa pela fila de Tasks/Work Queue; nada e enviado automaticamente.
            </p>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "Ativas", value: activeJourneys },
              { label: "Tasks", value: totalTasks },
              { label: "Aguardando", value: waiting },
            ].map((metric) => (
              <div key={metric.label} className="rounded-2xl border border-lovable-border bg-lovable-surface-soft px-4 py-3 text-center">
                <p className="text-lg font-black text-lovable-ink">{metric.value}</p>
                <p className="text-[10px] font-bold uppercase tracking-wider text-lovable-ink-muted">{metric.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-lovable-ink-muted">Templates</p>
            <h3 className="text-lg font-bold text-lovable-ink">Escolha uma jornada operacional</h3>
          </div>
          {selectedTemplate && (
            <div className="flex gap-2">
              <Button variant="ghost" onClick={() => previewMutation.mutate(selectedTemplate.id)} disabled={busy}>
                <Eye size={14} />Preview
              </Button>
              <Button variant="primary" onClick={() => createMutation.mutate(selectedTemplate.id)} disabled={busy}>
                <Play size={14} />Criar jornada
              </Button>
            </div>
          )}
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {templates.map((template) => (
            <TemplateCard
              key={template.id}
              template={template}
              selected={template.id === selectedTemplateId}
              onSelect={() => {
                setSelectedTemplateId(template.id);
                setPreview(null);
              }}
            />
          ))}
        </div>
      </section>

      <PreviewBox preview={preview} />

      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em] text-lovable-ink-muted">Ativas e configuradas</p>
            <h3 className="text-lg font-bold text-lovable-ink">Jornadas da academia</h3>
          </div>
          <Button variant="ghost" onClick={() => void queryClient.invalidateQueries({ queryKey: ["automation-journeys"] })}>
            <RefreshCw size={14} />Atualizar
          </Button>
        </div>
        {journeys.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-lovable-border bg-lovable-surface p-8 text-center">
            <Route size={36} className="mx-auto mb-3 text-lovable-ink-muted/30" />
            <p className="text-sm font-semibold text-lovable-ink">Nenhuma jornada criada ainda.</p>
            <p className="mt-1 text-xs text-lovable-ink-muted">Selecione um template acima, gere preview e crie a primeira jornada.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {journeys.map((journey) => (
              <JourneyCard
                key={journey.id}
                journey={journey}
                isBusy={busy}
                onPreview={() => journeyPreviewMutation.mutate(journey.id)}
                onActivate={() => activateMutation.mutate(journey.id)}
                onPause={() => pauseMutation.mutate(journey.id)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
