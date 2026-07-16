import type { Assessment } from "../../services/assessmentService";

interface AssessmentTimelineProps {
  assessments: Assessment[];
}

export function AssessmentTimeline({ assessments }: AssessmentTimelineProps) {
  if (assessments.length === 0) {
    return (
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Timeline de avaliacoes</h3>
        <p className="mt-2 text-sm text-lovable-ink-muted">Nenhuma avaliacao cadastrada.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Timeline de avaliacoes</h3>
      <ol className="mt-3 space-y-3">
        {assessments.map((assessment) => (
          <li key={assessment.id} className="rounded-xl border border-lovable-border bg-lovable-surface-soft p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-lovable-ink">
                  {assessment.history_badge ?? "Avaliacao"} {assessment.assessment_number ? `#${assessment.assessment_number}` : ""}
                </p>
                {assessment.measurement_protocol ? (
                  <p className="text-xs text-lovable-ink-muted">Protocolo: {assessment.measurement_protocol}</p>
                ) : null}
              </div>
              <time className="text-xs text-lovable-ink-muted">
                {new Date(assessment.assessment_date).toLocaleDateString("pt-BR")}
              </time>
            </div>
            {assessment.comparison_warning ? (
              <p className="mt-2 rounded-lg border border-lovable-warning/25 bg-lovable-warning/10 px-3 py-2 text-xs text-lovable-warning">
                {assessment.comparison_warning}
              </p>
            ) : null}
            <div className="mt-2 grid gap-1 text-xs text-lovable-ink-muted md:grid-cols-3">
              <p>Peso: {assessment.weight_kg ?? "-"} kg</p>
              <p>BF: {assessment.body_fat_pct ?? "-"}%</p>
              <p>BMI: {assessment.bmi ?? "-"}</p>
              <p>Forca: {assessment.strength_score ?? "-"}</p>
              <p>Flexibilidade: {assessment.flexibility_score ?? "-"}</p>
              <p>Cardio: {assessment.cardio_score ?? "-"}</p>
            </div>
            {assessment.ai_analysis ? (
              <p className="mt-2 rounded-lg border border-lovable-border bg-lovable-surface px-3 py-2 text-xs text-lovable-ink-muted">
                {assessment.ai_analysis}
              </p>
            ) : null}
          </li>
        ))}
      </ol>
    </section>
  );
}
