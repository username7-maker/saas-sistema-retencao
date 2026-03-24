import { Sparkles } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { useAuth } from "../../hooks/useAuth";
import { npsService, type NpsResponse } from "../../services/npsService";
import { taskService } from "../../services/taskService";
import { canDispatchNps } from "../../utils/roleAccess";

function sentimentVariantClasses(sentiment: string): string {
  const s = sentiment.toLowerCase();
  if (s === "negativo" || s === "negative") return "bg-lovable-danger/15 text-lovable-danger";
  if (s === "neutro" || s === "neutral") return "bg-lovable-warning/15 text-lovable-warning";
  return "bg-lovable-success/15 text-lovable-success";
}

function sentimentLabel(sentiment: string): string {
  const s = sentiment.toLowerCase();
  if (s === "negativo" || s === "negative") return "Negativo";
  if (s === "neutro" || s === "neutral") return "Neutro";
  if (s === "positivo" || s === "positive") return "Positivo";
  return sentiment;
}

interface DetractorRowProps {
  response: NpsResponse;
}

function DetractorRow({ response }: DetractorRowProps) {
  const queryClient = useQueryClient();

  const createTaskMutation = useMutation({
    mutationFn: () =>
      taskService.createTask({
        title: `Ação NPS — Score ${response.score} (${sentimentLabel(response.sentiment)})`,
        description: response.comment ?? undefined,
        member_id: response.member_id ?? undefined,
        priority: "high",
        status: "todo",
        due_date: null,
      }),
    onSuccess: () => {
      toast.success("Tarefa criada para o detrator.");
      void queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: () => toast.error("Erro ao criar tarefa."),
  });

  return (
    <li className="py-4">
      <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between md:gap-4">
        <div className="flex-1 space-y-1.5">
          {/* Score + Sentiment chip */}
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold text-lovable-danger">Score: {response.score}</span>
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${sentimentVariantClasses(response.sentiment)}`}
            >
              {sentimentLabel(response.sentiment)}
            </span>
          </div>

          {/* Comment */}
          {response.comment && (
            <p className="text-xs text-lovable-ink-muted">"{response.comment}"</p>
          )}

          {/* AI summary blockquote */}
          {response.sentiment_summary && (
            <blockquote className="mt-1 flex items-start gap-1.5 rounded-lg border border-lovable-primary/20 bg-lovable-primary/5 px-3 py-2">
              <Sparkles size={12} className="mt-0.5 shrink-0 text-lovable-primary" />
              <p className="text-xs italic text-lovable-ink">{response.sentiment_summary}</p>
            </blockquote>
          )}
        </div>

        <div className="flex shrink-0 items-start gap-3">
          <time className="text-xs text-lovable-ink-muted">
            {new Date(response.response_date).toLocaleDateString("pt-BR")}
          </time>
          {response.member_id && (
            <button
              type="button"
              onClick={() => createTaskMutation.mutate()}
              disabled={createTaskMutation.isPending}
              className="rounded-full bg-lovable-primary px-3 py-1 text-[10px] font-semibold uppercase tracking-wider text-white hover:opacity-90 disabled:opacity-60"
            >
              {createTaskMutation.isPending ? "Criando..." : "Criar Tarefa"}
            </button>
          )}
        </div>
      </div>
    </li>
  );
}

export function NpsPage() {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const canDispatch = canDispatchNps(user?.role);

  const evolutionQuery = useQuery({
    queryKey: ["nps", "evolution"],
    queryFn: () => npsService.evolution(12),
    staleTime: 5 * 60 * 1000,
  });

  const detractorsQuery = useQuery({
    queryKey: ["nps", "detractors"],
    queryFn: () => npsService.detractors(30),
    staleTime: 5 * 60 * 1000,
  });

  const dispatchMutation = useMutation({
    mutationFn: npsService.dispatch,
    onSuccess: (result) => {
      const sent = result.sent ?? 0;
      toast.success(`Pesquisa NPS disparada para ${sent} aluno(s)`);
      void queryClient.invalidateQueries({ queryKey: ["nps"] });
    },
    onError: () => toast.error("Erro ao disparar pesquisa NPS"),
  });

  const latestScore =
    evolutionQuery.data && evolutionQuery.data.length > 0
      ? evolutionQuery.data[evolutionQuery.data.length - 1].average_score
      : null;

  const totalResponses = evolutionQuery.data?.reduce((acc, p) => acc + p.responses, 0) ?? 0;
  const detractorCount = detractorsQuery.data?.length ?? 0;

  if (evolutionQuery.isLoading) {
    return <LoadingPanel text="Carregando dados NPS..." />;
  }

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">NPS — Net Promoter Score</h2>
          <p className="text-sm text-lovable-ink-muted">Evolução mensal, detratores e disparo de pesquisa.</p>
        </div>
        {canDispatch ? (
          <button
            type="button"
            onClick={() => dispatchMutation.mutate()}
            disabled={dispatchMutation.isPending}
            className="rounded-full bg-lovable-primary px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:opacity-90 disabled:opacity-60"
          >
            {dispatchMutation.isPending ? "Disparando..." : "Disparar pesquisa NPS"}
          </button>
        ) : null}
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <StatCard
          label="NPS Atual"
          value={latestScore !== null ? latestScore.toFixed(1) : "-"}
          tone={latestScore !== null && latestScore >= 7 ? "success" : latestScore !== null && latestScore >= 5 ? "warning" : "danger"}
        />
        <StatCard label="Respostas (12m)" value={String(totalResponses)} tone="neutral" />
        <StatCard label="Detratores (30d)" value={String(detractorCount)} tone="danger" />
      </div>

      {evolutionQuery.data && evolutionQuery.data.length > 0 && (
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Evolução NPS mensal</h3>
          <LineSeriesChart data={evolutionQuery.data} xKey="month" yKey="average_score" />
        </section>
      )}

      <section className="rounded-2xl border border-lovable-danger/30 bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-danger">
          Detratores recentes (últimos 30 dias) — {detractorCount}
        </h3>
        {detractorsQuery.isLoading ? (
          <LoadingPanel text="Carregando detratores..." />
        ) : detractorCount === 0 ? (
          <p className="text-sm text-lovable-ink-muted">Nenhum detrator nos últimos 30 dias.</p>
        ) : (
          <ul className="divide-y divide-lovable-border">
            {(detractorsQuery.data ?? []).map((response) => (
              <DetractorRow key={response.id} response={response} />
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
