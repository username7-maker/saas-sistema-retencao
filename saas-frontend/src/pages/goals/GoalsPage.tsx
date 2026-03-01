import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import toast from "react-hot-toast";

import { LoadingPanel } from "../../components/common/LoadingPanel";
import { goalService } from "../../services/goalService";
import { Button, FormField, Input, Select } from "../../components/ui2";

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
  nps_avg: "NPS médio",
  active_members: "Alunos ativos",
};

export function GoalsPage() {
  const queryClient = useQueryClient();
  const [deletingGoalId, setDeletingGoalId] = useState<string | null>(null);

  const progressQuery = useQuery({
    queryKey: ["goals", "progress"],
    queryFn: () => goalService.progress(true),
    staleTime: 60 * 1000,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<GoalForm>({
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
      toast.success("Meta salva com sucesso!");
      void queryClient.invalidateQueries({ queryKey: ["goals", "progress"] });
      reset();
    },
    onError: () => toast.error("Erro ao salvar meta."),
  });

  const deleteMutation = useMutation({
    mutationFn: (goalId: string) => goalService.delete(goalId),
    onSuccess: () => {
      toast.success("Meta removida.");
      setDeletingGoalId(null);
      void queryClient.invalidateQueries({ queryKey: ["goals", "progress"] });
    },
    onError: () => toast.error("Erro ao remover meta."),
  });

  const onSubmit = (payload: GoalForm) => createMutation.mutate(payload);

  if (progressQuery.isLoading) {
    return <LoadingPanel text="Carregando metas..." />;
  }

  if (progressQuery.isError) {
    return <LoadingPanel text="Erro ao carregar metas. Tente novamente." />;
  }

  return (
    <section className="space-y-6">
      <header>
        <h2 className="font-heading text-3xl font-bold text-lovable-ink">Metas</h2>
        <p className="text-sm text-lovable-ink-muted">Defina metas mensais e monitore risco de não atingimento.</p>
      </header>

      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Nova meta</h3>
        <form className="grid gap-3 md:grid-cols-3" onSubmit={handleSubmit(onSubmit)}>
          <FormField label="Nome da meta" required error={errors.name?.message}>
            <Input {...register("name")} placeholder="Nome da meta" />
          </FormField>

          <FormField label="Tipo de métrica" required error={errors.metric_type?.message}>
            <Select {...register("metric_type")}>
              <option value="mrr">MRR</option>
              <option value="new_members">Novos alunos</option>
              <option value="churn_rate">Churn</option>
              <option value="nps_avg">NPS médio</option>
              <option value="active_members">Alunos ativos</option>
            </Select>
          </FormField>

          <FormField label="Comparador" required error={errors.comparator?.message}>
            <Select {...register("comparator")}>
              <option value="gte">Maior ou igual (&gt;=)</option>
              <option value="lte">Menor ou igual (&lt;=)</option>
            </Select>
          </FormField>

          <FormField label="Valor alvo" required error={errors.target_value?.message}>
            <Input {...register("target_value")} type="number" step="0.01" />
          </FormField>

          <FormField label="Início" required error={errors.period_start?.message}>
            <Input {...register("period_start")} type="date" />
          </FormField>

          <FormField label="Fim" required error={errors.period_end?.message}>
            <Input {...register("period_end")} type="date" />
          </FormField>

          <FormField label="Alerta (%)" required error={errors.alert_threshold_pct?.message}>
            <Input {...register("alert_threshold_pct")} type="number" min={1} max={100} />
          </FormField>

          <FormField label="Notas" error={errors.notes?.message}>
            <Input {...register("notes")} placeholder="Observações (opcional)" />
          </FormField>

          <div className="flex items-end">
            <Button type="submit" disabled={createMutation.isPending} className="w-full">
              {createMutation.isPending ? "Salvando..." : "Salvar meta"}
            </Button>
          </div>
        </form>
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
            <article key={item.goal.id} className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
              <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-lovable-ink">{item.goal.name}</p>
                  <p className="text-xs text-lovable-ink-muted">
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
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      setDeletingGoalId(item.goal.id);
                      deleteMutation.mutate(item.goal.id);
                    }}
                    disabled={deleteMutation.isPending && deletingGoalId === item.goal.id}
                  >
                    {deleteMutation.isPending && deletingGoalId === item.goal.id ? "Removendo..." : "Remover"}
                  </Button>
                </div>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-lovable-surface-soft">
                <div className={`h-2 rounded-full ${tone}`} style={{ width: `${progressClamped}%` }} />
              </div>
              <p className="mt-2 text-xs text-lovable-ink-muted">
                {item.status_message} ({item.progress_pct.toFixed(1)}%)
              </p>
            </article>
          );
        })}
      </section>
    </section>
  );
}
