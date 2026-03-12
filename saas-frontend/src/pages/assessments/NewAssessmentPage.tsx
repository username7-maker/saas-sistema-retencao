import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import { ConstraintsAlert } from "../../components/assessments/ConstraintsAlert";
import { LoadingPanel } from "../../components/common/LoadingPanel";
import { Button, FormField, Input, Select, Textarea } from "../../components/ui2";
import { assessmentService, type AssessmentCreateInput } from "../../services/assessmentService";

const assessmentSchema = z.object({
  assessment_date: z.string().optional(),
  height_cm: z.string().optional(),
  weight_kg: z.string().optional(),
  body_fat_pct: z.string().optional(),
  lean_mass_kg: z.string().optional(),
  waist_cm: z.string().optional(),
  hip_cm: z.string().optional(),
  chest_cm: z.string().optional(),
  arm_cm: z.string().optional(),
  thigh_cm: z.string().optional(),
  resting_hr: z.string().optional(),
  blood_pressure_systolic: z.string().optional(),
  blood_pressure_diastolic: z.string().optional(),
  vo2_estimated: z.string().optional(),
  strength_score: z.string().optional(),
  flexibility_score: z.string().optional(),
  cardio_score: z.string().optional(),
  goal_type: z.string().default("general"),
  goal_target_value: z.string().optional(),
  target_frequency_per_week: z.string().optional(),
  adherence_score: z.string().optional(),
  sleep_quality_score: z.string().optional(),
  stress_score: z.string().optional(),
  pain_score: z.string().optional(),
  motivation_score: z.string().optional(),
  perceived_progress_score: z.string().optional(),
  exercise_execution_score: z.string().optional(),
  main_goal_obstacle: z.string().optional(),
  routine_notes: z.string().optional(),
  observations: z.string().optional(),
});

type AssessmentForm = z.infer<typeof assessmentSchema>;

function parseOptionalNumber(value?: string): number | undefined {
  if (!value || value.trim() === "") {
    return undefined;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function buildPayload(values: AssessmentForm): AssessmentCreateInput {
  const extraData: Record<string, unknown> = {
    goal_type: values.goal_type || "general",
    goal_target_value: parseOptionalNumber(values.goal_target_value),
    target_frequency_per_week: parseOptionalNumber(values.target_frequency_per_week),
    adherence_score: parseOptionalNumber(values.adherence_score),
    sleep_quality_score: parseOptionalNumber(values.sleep_quality_score),
    stress_score: parseOptionalNumber(values.stress_score),
    pain_score: parseOptionalNumber(values.pain_score),
    motivation_score: parseOptionalNumber(values.motivation_score),
    perceived_progress_score: parseOptionalNumber(values.perceived_progress_score),
    exercise_execution_score: parseOptionalNumber(values.exercise_execution_score),
    main_goal_obstacle: values.main_goal_obstacle || undefined,
    routine_notes: values.routine_notes || undefined,
  };

  return {
    assessment_date: values.assessment_date || undefined,
    height_cm: parseOptionalNumber(values.height_cm),
    weight_kg: parseOptionalNumber(values.weight_kg),
    body_fat_pct: parseOptionalNumber(values.body_fat_pct),
    lean_mass_kg: parseOptionalNumber(values.lean_mass_kg),
    waist_cm: parseOptionalNumber(values.waist_cm),
    hip_cm: parseOptionalNumber(values.hip_cm),
    chest_cm: parseOptionalNumber(values.chest_cm),
    arm_cm: parseOptionalNumber(values.arm_cm),
    thigh_cm: parseOptionalNumber(values.thigh_cm),
    resting_hr: parseOptionalNumber(values.resting_hr),
    blood_pressure_systolic: parseOptionalNumber(values.blood_pressure_systolic),
    blood_pressure_diastolic: parseOptionalNumber(values.blood_pressure_diastolic),
    vo2_estimated: parseOptionalNumber(values.vo2_estimated),
    strength_score: parseOptionalNumber(values.strength_score),
    flexibility_score: parseOptionalNumber(values.flexibility_score),
    cardio_score: parseOptionalNumber(values.cardio_score),
    observations: values.observations || undefined,
    extra_data: Object.fromEntries(Object.entries(extraData).filter(([, value]) => value !== undefined)),
  };
}

function defaultDateTimeLocal(): string {
  const now = new Date();
  const tzOffsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - tzOffsetMs).toISOString().slice(0, 16);
}

const goalOptions = [
  { label: "Geral", value: "general" },
  { label: "Perda de gordura", value: "fat_loss" },
  { label: "Ganho de massa", value: "muscle_gain" },
  { label: "Performance", value: "performance" },
];

export function NewAssessmentPage() {
  const { memberId } = useParams<{ memberId: string }>();
  const navigate = useNavigate();

  const profileQuery = useQuery({
    queryKey: ["assessments", "profile360", memberId],
    queryFn: () => assessmentService.profile360(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const { register, handleSubmit, formState, watch } = useForm<AssessmentForm>({
    resolver: zodResolver(assessmentSchema),
    defaultValues: {
      assessment_date: defaultDateTimeLocal(),
      observations: "",
      goal_type: "general",
      target_frequency_per_week: "3",
    },
  });

  const createMutation = useMutation({
    mutationFn: (payload: AssessmentCreateInput) => assessmentService.create(memberId ?? "", payload),
    onSuccess: () => {
      if (memberId) {
        void navigate(`/assessments/members/${memberId}`);
      }
    },
  });

  if (!memberId) {
    return <LoadingPanel text="Membro nao informado." />;
  }

  if (profileQuery.isLoading) {
    return <LoadingPanel text="Carregando dados do membro..." />;
  }

  if (profileQuery.isError) {
    return <LoadingPanel text="Erro ao carregar dados do membro. Tente novamente." />;
  }

  const profile = profileQuery.data;
  const onSubmit = (values: AssessmentForm) => {
    createMutation.mutate(buildPayload(values));
  };

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 className="font-heading text-3xl font-bold text-lovable-ink">Nova Avaliacao</h2>
          <p className="text-sm text-lovable-ink-muted">
            {profile ? `Membro: ${profile.member.full_name}` : "Preencha os dados da avaliacao fisica estruturada."}
          </p>
        </div>
        <Link
          to={`/assessments/members/${memberId}`}
          className="rounded-full border border-lovable-border px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted hover:border-lovable-border-strong"
        >
          Voltar ao Perfil
        </Link>
      </header>

      {profile && <ConstraintsAlert constraints={profile.constraints} />}

      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Dados basicos</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <FormField label="Data da avaliacao">
              <Input {...register("assessment_date")} type="datetime-local" />
            </FormField>
            <FormField label="Altura (cm)">
              <Input {...register("height_cm")} type="number" step="0.01" />
            </FormField>
            <FormField label="Peso (kg)">
              <Input {...register("weight_kg")} type="number" step="0.01" />
            </FormField>
            <FormField label="Gordura corporal (%)">
              <Input {...register("body_fat_pct")} type="number" step="0.01" />
            </FormField>
            <FormField label="Massa magra (kg)">
              <Input {...register("lean_mass_kg")} type="number" step="0.01" />
            </FormField>
            <FormField label="VO2 estimado">
              <Input {...register("vo2_estimated")} type="number" step="0.01" />
            </FormField>
          </div>
        </section>

        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Medidas corporais</h3>
          <div className="grid gap-3 md:grid-cols-5">
            <FormField label="Cintura (cm)">
              <Input {...register("waist_cm")} type="number" step="0.01" />
            </FormField>
            <FormField label="Quadril (cm)">
              <Input {...register("hip_cm")} type="number" step="0.01" />
            </FormField>
            <FormField label="Peito (cm)">
              <Input {...register("chest_cm")} type="number" step="0.01" />
            </FormField>
            <FormField label="Braco (cm)">
              <Input {...register("arm_cm")} type="number" step="0.01" />
            </FormField>
            <FormField label="Coxa (cm)">
              <Input {...register("thigh_cm")} type="number" step="0.01" />
            </FormField>
          </div>
        </section>

        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Performance e cardiovascular</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <FormField label="Forca (0-100)">
              <Input {...register("strength_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Flexibilidade (0-100)">
              <Input {...register("flexibility_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Cardio (0-100)">
              <Input {...register("cardio_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="FC repouso">
              <Input {...register("resting_hr")} type="number" />
            </FormField>
            <FormField label="PA sistolica">
              <Input {...register("blood_pressure_systolic")} type="number" />
            </FormField>
            <FormField label="PA diastolica">
              <Input {...register("blood_pressure_diastolic")} type="number" />
            </FormField>
          </div>
        </section>

        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Contexto de meta e aderencia</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <FormField label="Meta principal">
              <Select {...register("goal_type")} value={watch("goal_type") || "general"}>
                {goalOptions.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </Select>
            </FormField>
            <FormField label="Valor alvo da meta">
              <Input {...register("goal_target_value")} type="number" step="0.01" placeholder="Ex: 18 (% gordura)" />
            </FormField>
            <FormField label="Frequencia alvo / semana">
              <Input {...register("target_frequency_per_week")} type="number" min={1} max={14} />
            </FormField>
            <FormField label="Aderencia percebida (0-100)">
              <Input {...register("adherence_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Qualidade do sono (0-100)">
              <Input {...register("sleep_quality_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Estresse (0-100)">
              <Input {...register("stress_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Dor / restricao (0-100)">
              <Input {...register("pain_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Motivacao atual (0-100)">
              <Input {...register("motivation_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Percepcao de progresso (0-100)">
              <Input {...register("perceived_progress_score")} type="number" min={0} max={100} />
            </FormField>
            <FormField label="Execucao tecnica (0-100)">
              <Input {...register("exercise_execution_score")} type="number" min={0} max={100} />
            </FormField>
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <FormField label="Maior obstaculo para evolucao">
              <Textarea {...register("main_goal_obstacle")} rows={3} placeholder="Ex: rotina instavel, alimentacao, dor, baixa frequencia..." />
            </FormField>
            <FormField label="Notas sobre rotina e aderencia">
              <Textarea {...register("routine_notes")} rows={3} placeholder="Ex: trabalha em turnos, treina melhor a noite, falha no fim de semana..." />
            </FormField>
          </div>
        </section>

        <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Observacoes finais</h3>
          <Textarea
            {...register("observations")}
            rows={4}
            placeholder="Observacoes gerais da avaliacao, contexto clinico e pontos de atencao."
          />
        </section>

        <div className="flex items-center justify-end gap-3">
          {formState.errors.root && <p className="text-xs text-rose-600">{formState.errors.root.message}</p>}
          <Button type="submit" variant="primary" disabled={createMutation.isPending}>
            {createMutation.isPending ? "Salvando..." : "Salvar avaliacao"}
          </Button>
        </div>
      </form>
    </section>
  );
}
