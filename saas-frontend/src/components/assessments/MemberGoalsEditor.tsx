import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil, Plus, Save, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import toast from "react-hot-toast";
import { z } from "zod";

import { assessmentService, type MemberGoal } from "../../services/assessmentService";
import { Button, FormField, Input, Select, Textarea } from "../ui2";
import { invalidateAssessmentQueries } from "./queryUtils";

const schema = z.object({
  title: z.string().min(2, "Informe o objetivo"),
  description: z.string().optional(),
  category: z.string().default("general"),
  target_value: z.string().optional(),
  current_value: z.string().optional(),
  unit: z.string().optional(),
  target_date: z.string().optional(),
  status: z.string().default("active"),
  notes: z.string().optional(),
});

type FormValues = z.infer<typeof schema>;

interface Props {
  memberId: string;
  goals: MemberGoal[];
  defaultAssessmentId?: string | null;
}

function parseOptionalNumber(value?: string): number | undefined {
  if (!value || value.trim() === "") {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function buildDefaultValues(goal?: MemberGoal | null): FormValues {
  return {
    title: goal?.title ?? "",
    description: goal?.description ?? "",
    category: goal?.category ?? "general",
    target_value: goal?.target_value != null ? String(goal.target_value) : "",
    current_value: goal?.current_value != null ? String(goal.current_value) : "",
    unit: goal?.unit ?? "",
    target_date: goal?.target_date ?? "",
    status: goal?.status ?? "active",
    notes: goal?.notes ?? "",
  };
}

const categoryOptions = [
  { value: "general", label: "Geral" },
  { value: "fat_loss", label: "Perda de gordura" },
  { value: "muscle_gain", label: "Ganho de massa" },
  { value: "performance", label: "Performance" },
  { value: "wellness", label: "Saude" },
];

const statusOptions = [
  { value: "active", label: "Ativo" },
  { value: "paused", label: "Pausado" },
  { value: "done", label: "Concluido" },
];

export function MemberGoalsEditor({ memberId, goals, defaultAssessmentId }: Props) {
  const queryClient = useQueryClient();
  const currentGoal = goals.find((goal) => !goal.achieved && goal.status !== "done") ?? goals[0] ?? null;
  const [editingGoalId, setEditingGoalId] = useState<string | "new" | null>(goals.length === 0 ? "new" : null);
  const editingGoal = editingGoalId && editingGoalId !== "new" ? goals.find((goal) => goal.id === editingGoalId) ?? null : null;
  const defaultValues = useMemo(() => buildDefaultValues(editingGoalId === "new" ? null : editingGoal), [editingGoal, editingGoalId]);

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
    if (goals.length === 0) {
      setEditingGoalId("new");
    }
  }, [defaultValues, goals.length, reset]);

  const saveMutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        assessment_id: defaultAssessmentId || undefined,
        title: values.title.trim(),
        description: values.description?.trim() || undefined,
        category: values.category || "general",
        target_value: parseOptionalNumber(values.target_value),
        current_value: parseOptionalNumber(values.current_value) ?? 0,
        unit: values.unit?.trim() || undefined,
        target_date: values.target_date || undefined,
        status: values.status || "active",
        notes: values.notes?.trim() || undefined,
      };

      if (editingGoalId && editingGoalId !== "new") {
        return assessmentService.updateGoal(memberId, editingGoalId, payload);
      }
      return assessmentService.createGoal(memberId, payload);
    },
    onSuccess: async () => {
      await invalidateAssessmentQueries(queryClient, memberId);
      toast.success("Objetivo salvo.");
      setEditingGoalId(null);
    },
    onError: () => toast.error("Nao foi possivel salvar o objetivo."),
  });

  return (
    <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      <div className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Objetivos</h3>
          <p className="mt-1 text-xs text-lovable-ink-muted">Os objetivos salvos aqui aparecem na aba Objetivos do Perfil 360.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {currentGoal ? (
            <Button size="sm" variant="secondary" onClick={() => setEditingGoalId(currentGoal.id)}>
              <Pencil size={14} />
              Editar atual
            </Button>
          ) : null}
          <Button
            size="sm"
            variant="primary"
            onClick={() => {
              setEditingGoalId("new");
              reset(buildDefaultValues(null));
            }}
          >
            <Plus size={14} />
            Adicionar objetivo
          </Button>
        </div>
      </div>

      {editingGoalId ? (
        <form className="mt-4 space-y-3" onSubmit={handleSubmit((values) => saveMutation.mutate(values))}>
          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Titulo" error={errors.title?.message} required>
              <Input {...register("title")} placeholder="Ex: Reduzir percentual de gordura" />
            </FormField>
            <FormField label="Categoria" error={errors.category?.message}>
              <Select {...register("category")} value={watch("category") || "general"}>
                {categoryOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Valor alvo" error={errors.target_value?.message}>
              <Input {...register("target_value")} type="number" step="0.01" placeholder="Ex: 18" />
            </FormField>
            <FormField label="Valor atual" error={errors.current_value?.message}>
              <Input {...register("current_value")} type="number" step="0.01" placeholder="Ex: 24" />
            </FormField>
            <FormField label="Unidade" error={errors.unit?.message}>
              <Input {...register("unit")} placeholder="Ex: %, kg, cm" />
            </FormField>
            <FormField label="Prazo" error={errors.target_date?.message}>
              <Input {...register("target_date")} type="date" />
            </FormField>
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <FormField label="Descricao" error={errors.description?.message}>
              <Textarea {...register("description")} rows={3} placeholder="Contexto do objetivo e criterios de sucesso." />
            </FormField>
            <FormField label="Notas" error={errors.notes?.message}>
              <Textarea {...register("notes")} rows={3} placeholder="Observacoes para o professor ou aluno." />
            </FormField>
          </div>

          <div className="grid gap-3 md:grid-cols-[220px_1fr]">
            <FormField label="Status" error={errors.status?.message}>
              <Select {...register("status")} value={watch("status") || "active"}>
                {statusOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </FormField>
          </div>

          <div className="flex justify-end gap-2">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                setEditingGoalId(null);
                reset(buildDefaultValues(currentGoal));
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

      <div className="mt-4 grid gap-3">
        {goals.length === 0 ? (
          <div className="rounded-xl border border-dashed border-lovable-border bg-lovable-surface-soft p-4 text-sm text-lovable-ink-muted">
            Nenhum objetivo registrado ainda.
          </div>
        ) : (
          goals.map((goal) => (
            <article key={goal.id} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-4">
              <div className="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-base font-semibold text-lovable-ink">{goal.title}</p>
                    <span className="rounded-full bg-lovable-primary-soft px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wider text-lovable-primary">
                      {goal.category}
                    </span>
                  </div>
                  {goal.description ? <p className="mt-2 text-sm text-lovable-ink-muted">{goal.description}</p> : null}
                </div>
                <Button size="sm" variant="secondary" onClick={() => setEditingGoalId(goal.id)}>
                  <Pencil size={14} />
                  Editar
                </Button>
              </div>

              <div className="mt-3 grid gap-2 text-sm text-lovable-ink-muted md:grid-cols-4">
                <p>
                  <span className="font-semibold text-lovable-ink">Atual:</span> {goal.current_value} {goal.unit ?? ""}
                </p>
                <p>
                  <span className="font-semibold text-lovable-ink">Meta:</span> {goal.target_value ?? "-"} {goal.unit ?? ""}
                </p>
                <p>
                  <span className="font-semibold text-lovable-ink">Prazo:</span> {goal.target_date ?? "-"}
                </p>
                <p>
                  <span className="font-semibold text-lovable-ink">Progresso:</span> {goal.progress_pct}%
                </p>
              </div>

              {goal.notes ? (
                <p className="mt-3 rounded-lg bg-lovable-surface px-3 py-2 text-xs text-lovable-ink-muted">{goal.notes}</p>
              ) : null}
            </article>
          ))
        )}
      </div>
    </section>
  );
}
