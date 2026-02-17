import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { goalService } from "../../services/goalService";

const goalSchema = z.object({
  name: z.string().min(3),
  metric_type: z.enum(["mrr", "new_members", "churn_rate", "nps_avg", "active_members"]),
  comparator: z.enum(["gte", "lte"]),
  target_value: z.coerce.number().min(0),
  period_start: z.string().min(1),
  period_end: z.string().min(1),
  alert_threshold_pct: z.coerce.number().int().min(1).max(100),
  notes: z.string().optional(),
});

type GoalForm = z.infer<typeof goalSchema>;

const metricLabel: Record<string, string> = {
  mrr: "MRR",
  new_members: "Novos alunos",
  churn_rate: "Churn",
  nps_avg: "NPS medio",
  active_members: "Alunos ativos",
};

export function GoalsPage() {
  const queryClient = useQueryClient();
  const progressQuery = useQuery({
    queryKey: ["goals", "progress"],
    queryFn: () => goalService.progress(true),
    staleTime: 60 * 1000,
  });

  const { register, handleSubmit, reset, formState } = useForm<GoalForm>({
    resolver: zodResolver(goalSchema),
    defaultValues: {
      name: "",
      metric_type: "mrr",
      comparator: "gte",
      target_value: 0,
      period_start: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10),
      period_end: new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().slice(0, 10),
      alert_threshold_pct: 80,
      notes: "",
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: GoalForm) => goalService.create(payload),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["goals", "progress"] });
      reset();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (goalId: string) => goalService.delete(goalId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["goals", "progress"] });
    },
  });

  const onSubmit = (payload: GoalForm) => createMutation.mutate(payload);

  if (progressQuery.isLoading) {
    return <LoadingPanel text="Carregando metas..." />;
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-slate-900">Metas</h2>
        <p className="text-sm text-slate-500">Defina metas mensais e monitore risco de nao atingimento.</p>
      </header>

      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Nova meta</h3>
        <form className="grid gap-3 md:grid-cols-3" onSubmit={handleSubmit(onSubmit)}>
          <input
            {...register("name")}
            placeholder="Nome da meta"
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <select {...register("metric_type")} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="mrr">MRR</option>
            <option value="new_members">Novos alunos</option>
            <option value="churn_rate">Churn</option>
            <option value="nps_avg">NPS medio</option>
            <option value="active_members">Alunos ativos</option>
          </select>
          <select {...register("comparator")} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
            <option value="gte">Maior ou igual (>=)</option>
            <option value="lte">Menor ou igual (<=)</option>
          </select>
          <input {...register("target_value")} type="number" step="0.01" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input {...register("period_start")} type="date" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input {...register("period_end")} type="date" className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input {...register("alert_threshold_pct")} type="number" min={1} max={100} className="rounded-lg border border-slate-300 px-3 py-2 text-sm" />
          <input {...register("notes")} placeholder="Notas (opcional)" className="rounded-lg border border-slate-300 px-3 py-2 text-sm md:col-span-2" />
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-lg bg-brand-500 px-3 py-2 text-sm font-semibold text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {createMutation.isPending ? "Salvando..." : "Salvar meta"}
          </button>
        </form>
        {formState.errors.root && <p className="mt-2 text-xs text-rose-600">{formState.errors.root.message}</p>}
      </section>

      <section className="space-y-3">
        {(progressQuery.data ?? []).map((item) => {
          const progressClamped = Math.max(0, Math.min(100, item.progress_pct));
          const tone =
            item.status === "achieved"
              ? "bg-emerald-500"
              : item.status === "at_risk"
                ? "bg-rose-500"
                : "bg-amber-500";

          return (
            <article key={item.goal.id} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-slate-800">{item.goal.name}</p>
                  <p className="text-xs text-slate-500">
                    {metricLabel[item.goal.metric_type]} | alvo {item.goal.comparator} {item.goal.target_value} | atual {item.current_value}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                      item.status === "achieved"
                        ? "bg-emerald-100 text-emerald-700"
                        : item.status === "at_risk"
                          ? "bg-rose-100 text-rose-700"
                          : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {item.status}
                  </span>
                  <button
                    type="button"
                    onClick={() => deleteMutation.mutate(item.goal.id)}
                    className="rounded-full border border-slate-300 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-slate-600 hover:border-slate-400"
                  >
                    Remover
                  </button>
                </div>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-slate-100">
                <div className={`h-2 rounded-full ${tone}`} style={{ width: `${progressClamped}%` }} />
              </div>
              <p className="mt-2 text-xs text-slate-500">
                {item.status_message} ({item.progress_pct.toFixed(1)}%)
              </p>
            </article>
          );
        })}
      </section>
    </section>
  );
}
