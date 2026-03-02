import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { StatCard } from "../../components/common/StatCard";
import { LineSeriesChart } from "../../components/charts/LineSeriesChart";
import { npsService } from "../../services/npsService";

export function NpsPage() {
  const queryClient = useQueryClient();

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
        <button
          type="button"
          onClick={() => dispatchMutation.mutate()}
          disabled={dispatchMutation.isPending}
          className="rounded-full bg-lovable-primary px-4 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:opacity-90 disabled:opacity-60"
        >
          {dispatchMutation.isPending ? "Disparando..." : "Disparar pesquisa NPS"}
        </button>
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
              <li key={response.id} className="py-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">
                      Score: <span className="text-lovable-danger">{response.score}</span>
                      {" — "}
                      <span className="text-lovable-ink-muted capitalize">{response.sentiment}</span>
                    </p>
                    {response.comment && (
                      <p className="mt-0.5 text-xs text-lovable-ink-muted">"{response.comment}"</p>
                    )}
                    {response.sentiment_summary && (
                      <p className="mt-0.5 text-xs italic text-lovable-ink-muted">{response.sentiment_summary}</p>
                    )}
                  </div>
                  <time className="shrink-0 text-xs text-lovable-ink-muted">
                    {new Date(response.response_date).toLocaleDateString("pt-BR")}
                  </time>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  );
}
