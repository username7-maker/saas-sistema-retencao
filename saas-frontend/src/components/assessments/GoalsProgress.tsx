import type { MemberGoal } from "../../services/assessmentService";

interface GoalsProgressProps {
  goals: MemberGoal[];
}

function formatTarget(goal: MemberGoal): string {
  if (goal.target_value === null) return "Sem valor alvo";
  return `${goal.target_value}${goal.unit ? ` ${goal.unit}` : ""}`;
}

function formatDate(value: string | null): string {
  if (!value) return "Sem data alvo";
  const parsed = Date.parse(value);
  if (Number.isNaN(parsed)) return "Sem data alvo";
  return new Date(parsed).toLocaleDateString("pt-BR");
}

function progressColor(progress: number, achieved: boolean): string {
  if (achieved) return "bg-lovable-success";
  if (progress >= 70) return "bg-lovable-primary";
  if (progress >= 35) return "bg-lovable-warning";
  return "bg-lovable-danger";
}

export function GoalsProgress({ goals }: GoalsProgressProps) {
  if (goals.length === 0) {
    return (
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Objetivos</h3>
        <p className="mt-2 text-sm text-lovable-ink-muted">Nenhum objetivo cadastrado.</p>
      </section>
    );
  }

  const ordered = [...goals].sort((a, b) => {
    if (a.achieved !== b.achieved) return a.achieved ? 1 : -1;
    const aDate = a.target_date ? Date.parse(a.target_date) : Number.MAX_SAFE_INTEGER;
    const bDate = b.target_date ? Date.parse(b.target_date) : Number.MAX_SAFE_INTEGER;
    return aDate - bDate;
  });

  const mainGoal = ordered[0];
  const mainProgress = Math.max(0, Math.min(mainGoal.progress_pct, 100));

  return (
    <section className="space-y-4">
      <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Meta principal</h3>
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-lg font-semibold text-lovable-ink">{mainGoal.title}</p>
            <p className="text-xs text-lovable-ink-muted">
              Alvo: {formatTarget(mainGoal)} | Data alvo: {formatDate(mainGoal.target_date)}
            </p>
          </div>
          <span
            className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wider ${
              mainGoal.achieved ? "bg-lovable-success/20 text-lovable-success" : "bg-lovable-surface-soft text-lovable-ink-muted"
            }`}
          >
            {mainGoal.achieved ? "atingido" : mainGoal.status}
          </span>
        </div>
        <div className="mt-4 h-3 w-full rounded-full bg-lovable-surface-soft">
          <div className={`h-3 rounded-full ${progressColor(mainProgress, mainGoal.achieved)}`} style={{ width: `${mainProgress}%` }} />
        </div>
        <div className="mt-1 flex justify-between text-xs text-lovable-ink-muted">
          <span>Atual: {mainGoal.current_value}</span>
          <span>{mainProgress.toFixed(0)}%</span>
        </div>
      </article>

      <article className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Demais objetivos</h3>
        <div className="mt-3 space-y-3">
          {ordered.map((goal) => {
            const progress = Math.max(0, Math.min(goal.progress_pct, 100));
            return (
              <div key={goal.id} className="rounded-xl border border-lovable-border px-3 py-3">
                <div className="flex items-center justify-between gap-2">
                  <div>
                    <p className="text-sm font-semibold text-lovable-ink">{goal.title}</p>
                    <p className="text-xs text-lovable-ink-muted">
                      {goal.category} | Data alvo: {formatDate(goal.target_date)}
                    </p>
                  </div>
                  <span className="text-xs font-semibold text-lovable-ink-muted">{progress.toFixed(0)}%</span>
                </div>
                <div className="mt-3 h-2 w-full rounded-full bg-lovable-surface-soft">
                  <div className={`h-2 rounded-full ${progressColor(progress, goal.achieved)}`} style={{ width: `${progress}%` }} />
                </div>
                <div className="mt-1 flex justify-between text-[11px] text-lovable-ink-muted">
                  <span>
                    Atual: {goal.current_value}
                    {goal.unit ? ` ${goal.unit}` : ""}
                  </span>
                  <span>Alvo: {formatTarget(goal)}</span>
                </div>
              </div>
            );
          })}
        </div>
      </article>
    </section>
  );
}
