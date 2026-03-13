import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Dumbbell, Pencil, Plus, Save, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { z } from "zod";

import { assessmentService, type TrainingPlan } from "../../services/assessmentService";
import { Button, FormField, Input, Select, Textarea } from "../ui2";
import { invalidateAssessmentQueries } from "./queryUtils";

const schema = z.object({
  name: z.string().min(3, "Informe o nome do treino"),
  objective: z.string().optional(),
  sessions_per_week: z.string().default("3"),
  split_type: z.string().optional(),
  start_date: z.string().min(1, "Informe a data de inicio"),
  end_date: z.string().optional(),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  memberId: string;
  trainingPlan: TrainingPlan | null;
  defaultAssessmentId?: string | null;
}

function buildDefaultValues(plan: TrainingPlan | null): FormValues {
  return {
    name: plan?.name ?? "",
    objective: plan?.objective ?? "",
    sessions_per_week: plan?.sessions_per_week != null ? String(plan.sessions_per_week) : "3",
    split_type: plan?.split_type ?? "",
    start_date: plan?.start_date ?? new Date().toISOString().split("T")[0],
    end_date: plan?.end_date ?? "",
    notes: plan?.notes ?? "",
  };
}

const splitOptions = ["AB", "ABC", "ABCD", "Full Body", "Upper/Lower", "Outro"];

export function MemberTrainingPlanEditor({ memberId, trainingPlan, defaultAssessmentId }: Props) {
  const queryClient = useQueryClient();
  const [editingMode, setEditingMode] = useState<"current" | "new" | null>(trainingPlan ? null : "new");
  const isEditing = editingMode !== null;
  const defaultValues = useMemo(() => buildDefaultValues(trainingPlan), [trainingPlan]);

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors, isDirty },
  } = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues,
  });

  useEffect(() => {
    reset(defaultValues);
    if (!trainingPlan) {
      setEditingMode("new");
    }
  }, [defaultValues, reset, trainingPlan]);

  const saveMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        assessment_id: defaultAssessmentId || undefined,
        name: values.name.trim(),
        objective: values.objective?.trim() || undefined,
        sessions_per_week: Math.max(1, Number(values.sessions_per_week) || 3),
        split_type: values.split_type?.trim() || undefined,
        start_date: values.start_date,
        end_date: values.end_date || undefined,
        is_active: true,
        notes: values.notes?.trim() || undefined,
      };

      if (editingMode === "current" && trainingPlan) {
        return assessmentService.updateTrainingPlan(memberId, trainingPlan.id, payload);
      }
      return assessmentService.createTrainingPlan(memberId, payload);
    },
    onSuccess: async () => {
      await invalidateAssessmentQueries(queryClient, memberId);
      toast.success("Treino salvo.");
      setEditingMode(null);
    },
    onError: () => toast.error("Nao foi possivel salvar o treino."),
  });

  return (
    <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Treino</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted">Esse bloco alimenta diretamente a aba Treino do Perfil 360.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {trainingPlan ? (
            <Button size="sm" variant="secondary" onClick={() => setEditingMode("current")}>
              <Pencil size={14} />
              Editar treino
            </Button>
          ) : null}
          <Button
            size="sm"
            variant="primary"
            onClick={() => {
              setEditingMode("new");
              reset(buildDefaultValues(null));
            }}
          >
            <Plus size={14} />
            {trainingPlan ? "Novo treino" : "Adicionar treino"}
          </Button>
        </div>
      </div>

      {trainingPlan ? (
        <div className="mt-4 grid gap-3 md:grid-cols-4">
          <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Nome</p>
            <p className="mt-1 text-sm font-semibold text-lovable-ink">{trainingPlan.name}</p>
          </article>
          <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Objetivo</p>
            <p className="mt-1 text-sm font-semibold text-lovable-ink">{trainingPlan.objective ?? "-"}</p>
          </article>
          <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Divisao</p>
            <p className="mt-1 text-sm font-semibold text-lovable-ink">{trainingPlan.split_type ?? "-"}</p>
          </article>
          <article className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <p className="text-xs uppercase tracking-wider text-lovable-ink-muted">Frequencia</p>
            <p className="mt-1 text-sm font-semibold text-lovable-ink">{trainingPlan.sessions_per_week}x / semana</p>
          </article>
        </div>
      ) : (
        <div className="mt-4 rounded-xl border border-dashed border-lovable-border bg-lovable-surface-soft p-4 text-sm text-lovable-ink-muted">
          Nenhum treino ativo registrado ainda.
        </div>
      )}

      {isEditing ? (
        <form className="mt-4 space-y-3" onSubmit={handleSubmit((values) => saveMutation.mutate(values))}>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Nome do treino" error={errors.name?.message} required>
              <Input {...register("name")} placeholder="Ex: Treino ABC - adaptacao" />
            </FormField>
            <FormField label="Objetivo" error={errors.objective?.message}>
              <Input {...register("objective")} placeholder="Ex: hipertrofia com foco em membros inferiores" />
            </FormField>
            <FormField label="Sessoes por semana" error={errors.sessions_per_week?.message}>
              <Input {...register("sessions_per_week")} type="number" min={1} max={14} />
            </FormField>
            <FormField label="Divisao" error={errors.split_type?.message}>
              <Select {...register("split_type")} value={watch("split_type") || ""}>
                <option value="">Selecione</option>
                {splitOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Inicio" error={errors.start_date?.message} required>
              <Input {...register("start_date")} type="date" />
            </FormField>
            <FormField label="Fim" error={errors.end_date?.message}>
              <Input {...register("end_date")} type="date" />
            </FormField>
          </div>

          <FormField label="Observacoes" error={errors.notes?.message}>
            <Textarea {...register("notes")} rows={4} placeholder="Series, alertas, adaptacoes e observacoes gerais." />
          </FormField>

          <div className="flex justify-end gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setEditingMode(null);
                reset(editingMode === "new" ? buildDefaultValues(trainingPlan) : defaultValues);
              }}
              disabled={saveMutation.isPending}
            >
              <X size={14} />
              Cancelar
            </Button>
            <Button size="sm" type="submit" variant="primary" disabled={saveMutation.isPending || !isDirty}>
              <Save size={14} />
              {saveMutation.isPending ? "Salvando..." : "Salvar"}
            </Button>
          </div>
        </form>
      ) : null}

      {trainingPlan?.notes ? (
        <div className="mt-4 rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
          <div className="flex items-center gap-2">
            <Dumbbell size={14} className="text-lovable-primary" />
            <p className="text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted">Notas do treino</p>
          </div>
          <p className="mt-2 text-sm text-lovable-ink-muted">{trainingPlan.notes}</p>
        </div>
      ) : null}
    </section>
  );
}
