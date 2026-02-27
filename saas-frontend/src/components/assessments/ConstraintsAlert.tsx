import type { MemberConstraints } from "../../services/assessmentService";

interface ConstraintsAlertProps {
  constraints: MemberConstraints | null;
}

function hasAnyConstraint(constraints: MemberConstraints | null): boolean {
  if (!constraints) {
    return false;
  }
  return Boolean(
    constraints.medical_conditions ||
      constraints.injuries ||
      constraints.medications ||
      constraints.contraindications ||
      constraints.notes ||
      Object.keys(constraints.restrictions ?? {}).length > 0,
  );
}

export function ConstraintsAlert({ constraints }: ConstraintsAlertProps) {
  if (!constraints) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-600">Restricoes medicas</h3>
        <p className="mt-2 text-sm text-slate-500">Nenhuma restricao cadastrada.</p>
      </section>
    );
  }

  const hasRisk = hasAnyConstraint(constraints);
  const restrictionItems = Object.entries(constraints.restrictions ?? {});

  return (
    <section
      className={`rounded-2xl border p-4 shadow-panel ${
        hasRisk ? "border-amber-300 bg-amber-50" : "border-emerald-200 bg-emerald-50"
      }`}
    >
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-700">Restricoes medicas</h3>

      {hasRisk ? (
        <div className="mt-3 space-y-2 text-sm text-slate-700">
          {constraints.medical_conditions && (
            <p>
              <span className="font-semibold">Condicoes:</span> {constraints.medical_conditions}
            </p>
          )}
          {constraints.injuries && (
            <p>
              <span className="font-semibold">Lesoes:</span> {constraints.injuries}
            </p>
          )}
          {constraints.medications && (
            <p>
              <span className="font-semibold">Medicacoes:</span> {constraints.medications}
            </p>
          )}
          {constraints.contraindications && (
            <p>
              <span className="font-semibold">Contraindicacoes:</span> {constraints.contraindications}
            </p>
          )}
          {constraints.preferred_training_times && (
            <p>
              <span className="font-semibold">Horario preferido:</span> {constraints.preferred_training_times}
            </p>
          )}
          {restrictionItems.length > 0 && (
            <ul className="list-disc space-y-1 pl-5 text-xs text-slate-600">
              {restrictionItems.map(([key, value]) => (
                <li key={key}>
                  {key}: {String(value)}
                </li>
              ))}
            </ul>
          )}
          {constraints.notes && (
            <p className="rounded-lg bg-white/80 px-3 py-2 text-xs text-slate-600">{constraints.notes}</p>
          )}
        </div>
      ) : (
        <p className="mt-2 text-sm text-emerald-700">Sem alertas medicos relevantes no momento.</p>
      )}
    </section>
  );
}
