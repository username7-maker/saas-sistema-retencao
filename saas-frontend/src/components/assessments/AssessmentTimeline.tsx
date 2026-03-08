import type { Assessment } from "../../services/assessmentService";

interface AssessmentTimelineProps {
  assessments: Assessment[];
}

export function AssessmentTimeline({ assessments }: AssessmentTimelineProps) {
  if (assessments.length === 0) {
    return (
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Timeline de avaliações</h3>
        <p className="mt-2 text-sm text-lovable-ink-muted">Nenhuma avaliação cadastrada.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Timeline de avaliações</h3>
      <ol className="mt-3 space-y-3">
        {assessments.map((assessment) => (
          <li key={assessment.id} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-semibold text-lovable-ink">Avaliação #{assessment.assessment_number}</p>
              <time className="text-xs text-lovable-ink-muted">
                {new Date(assessment.assessment_date).toLocaleDateString("pt-BR")}
              </time>
            </div>
            <div className="mt-2 grid gap-1 text-xs text-lovable-ink-muted md:grid-cols-3">
              <p>Peso: {assessment.weight_kg ?? "-"} kg</p>
              <p>BF: {assessment.body_fat_pct ?? "-"}%</p>
              <p>BMI: {assessment.bmi ?? "-"}</p>
              <p>Força: {assessment.strength_score ?? "-"}</p>
              <p>Flexibilidade: {assessment.flexibility_score ?? "-"}</p>
              <p>Cardio: {assessment.cardio_score ?? "-"}</p>
            </div>
            {assessment.ai_analysis && (
              <p className="mt-2 rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-xs text-lovable-ink-muted">
                {assessment.ai_analysis}
              </p>
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
