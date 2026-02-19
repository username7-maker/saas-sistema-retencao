import type { MemberGoal } from "../../services/assessmentService";

interface GoalsProgressProps {
  goals: MemberGoal[];
}

export function GoalsProgress({ goals }: GoalsProgressProps) {
  if (goals.length === 0) {
    return (
      <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-600">Objetivos</h3>
        <p className="mt-2 text-sm text-slate-500">Nenhum objetivo cadastrado.</p>
      </section>
    );
  }

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-panel">
      <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-600">Objetivos</h3>
      <div className="mt-3 space-y-3">
        {goals.map((goal) => {
          const progress = Math.max(0, Math.min(goal.progress_pct, 100));
          const tone = goal.achieved ? "bg-emerald-500" : progress >= 70 ? "bg-brand-500" : "bg-amber-500";
          return (
            <article key={goal.id} className="rounded-xl border border-slate-200 p-3">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-slate-700">{goal.title}</p>
                  <p className="text-xs text-slate-500">
                    {goal.category} {goal.target_value !== null ? `| alvo: ${goal.target_value}` : ""}
                    {goal.unit ? ` ${goal.unit}` : ""}
                  </p>
                </div>
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                    goal.achieved ? "bg-emerald-100 text-emerald-700" : "bg-slate-100 text-slate-600"
                  }`}
                >
                  {goal.achieved ? "atingido" : goal.status}
                </span>
              </div>
              <div className="mt-3 h-2 w-full rounded-full bg-slate-100">
                <div className={`h-2 rounded-full ${tone}`} style={{ width: `${progress}%` }} />
              </div>
              <div className="mt-1 flex justify-between text-[11px] text-slate-500">
                <span>Atual: {goal.current_value}</span>
                <span>{progress.toFixed(0)}%</span>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
