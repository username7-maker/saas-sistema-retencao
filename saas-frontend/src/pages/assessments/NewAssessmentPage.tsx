import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

import { ConstraintsAlert } from "../../components/assessments/ConstraintsAlert";
import { LoadingPanel } from "../../components/common/LoadingPanel";
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
  };
}

function defaultDateTimeLocal(): string {
  const now = new Date();
  const tzOffsetMs = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - tzOffsetMs).toISOString().slice(0, 16);
}

export function NewAssessmentPage() {
  const { memberId } = useParams<{ memberId: string }>();
  const navigate = useNavigate();

  const profileQuery = useQuery({
    queryKey: ["assessments", "profile360", memberId],
    queryFn: () => assessmentService.profile360(memberId ?? ""),
    enabled: Boolean(memberId),
    staleTime: 60 * 1000,
  });

  const { register, handleSubmit, formState } = useForm<AssessmentForm>({
    resolver: zodResolver(assessmentSchema),
    defaultValues: {
      assessment_date: defaultDateTimeLocal(),
      observations: "",
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
          <h2 className="font-heading text-3xl font-bold text-slate-900">Nova Avaliacao</h2>
          <p className="text-sm text-slate-500">
            {profile ? `Membro: ${profile.member.full_name}` : "Preencha os dados da avaliacao fisica trimestral."}
          </p>
        </div>
        <Link
          to={`/assessments/members/${memberId}`}
          className="rounded-full border border-slate-300 px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-slate-600 hover:border-slate-400"
        >
          Voltar ao Perfil
        </Link>
      </header>

      {profile && <ConstraintsAlert constraints={profile.constraints} />}

      <form className="space-y-4" onSubmit={handleSubmit(onSubmit)}>
        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Dados basicos</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="text-xs text-slate-600">
              Data da avaliacao
              <input {...register("assessment_date")} type="datetime-local" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Altura (cm)
              <input {...register("height_cm")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Peso (kg)
              <input {...register("weight_kg")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Gordura corporal (%)
              <input {...register("body_fat_pct")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Massa magra (kg)
              <input {...register("lean_mass_kg")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              VO2 estimado
              <input {...register("vo2_estimated")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Medidas corporais</h3>
          <div className="grid gap-3 md:grid-cols-5">
            <label className="text-xs text-slate-600">
              Cintura (cm)
              <input {...register("waist_cm")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Quadril (cm)
              <input {...register("hip_cm")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Peito (cm)
              <input {...register("chest_cm")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Braco (cm)
              <input {...register("arm_cm")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Coxa (cm)
              <input {...register("thigh_cm")} type="number" step="0.01" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Performance e cardiovascular</h3>
          <div className="grid gap-3 md:grid-cols-3">
            <label className="text-xs text-slate-600">
              Forca (0-100)
              <input {...register("strength_score")} type="number" min={0} max={100} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Flexibilidade (0-100)
              <input {...register("flexibility_score")} type="number" min={0} max={100} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              Cardio (0-100)
              <input {...register("cardio_score")} type="number" min={0} max={100} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              FC repouso
              <input {...register("resting_hr")} type="number" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              PA sistolica
              <input {...register("blood_pressure_systolic")} type="number" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
            <label className="text-xs text-slate-600">
              PA diastolica
              <input {...register("blood_pressure_diastolic")} type="number" className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
            </label>
          </div>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
          <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-600">Observacoes</h3>
          <textarea
            {...register("observations")}
            rows={4}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm"
            placeholder="Observacoes gerais da avaliacao"
          />
        </section>

        <div className="flex items-center justify-end gap-3">
          {formState.errors.root && <p className="text-xs text-rose-600">{formState.errors.root.message}</p>}
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="rounded-full bg-brand-500 px-5 py-2 text-xs font-semibold uppercase tracking-wider text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {createMutation.isPending ? "Salvando..." : "Salvar avaliacao"}
          </button>
        </div>
      </form>
    </section>
  );
}
