/**
 * HeatmapGrid — visualiza check-ins por dia da semana × hora do dia.
 * Recebe HeatmapPoint[] com weekday (0=Dom..6=Sab) e hour_bucket (0–23).
 * Células coloridas por intensidade relativa ao máximo da série.
 */

interface HeatmapPoint {
  weekday: number;
  hour_bucket: number;
  total_checkins: number;
}

interface HeatmapGridProps {
  data: HeatmapPoint[];
}

const DAYS = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];
const HOURS = Array.from({ length: 24 }, (_, i) => i);

function intensityClass(ratio: number): string {
  if (ratio === 0) return "bg-lovable-surface-soft";
  if (ratio < 0.15) return "bg-lovable-primary/10";
  if (ratio < 0.30) return "bg-lovable-primary/25";
  if (ratio < 0.50) return "bg-lovable-primary/45";
  if (ratio < 0.70) return "bg-lovable-primary/65";
  if (ratio < 0.85) return "bg-lovable-primary/80";
  return "bg-lovable-primary";
}

export function HeatmapGrid({ data }: HeatmapGridProps) {
  if (!data.length) {
    return (
      <div className="flex h-32 items-center justify-center rounded-2xl border border-dashed border-lovable-border text-sm text-lovable-ink-muted">
        Sem dados de check-in para exibir heatmap.
      </div>
    );
  }

  // Build lookup map: weekday → hour_bucket → total
  const lookup = new Map<string, number>();
  let maxVal = 0;
  for (const point of data) {
    const key = `${point.weekday}:${point.hour_bucket}`;
    lookup.set(key, point.total_checkins);
    if (point.total_checkins > maxVal) maxVal = point.total_checkins;
  }

  return (
    <div className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">
        Heatmap de check-ins por hora
      </h3>

      {/* Legenda de horas no topo */}
      <div className="overflow-x-auto">
        <div
          className="grid gap-px"
          style={{ gridTemplateColumns: `3rem repeat(24, minmax(1.5rem, 1fr))` }}
        >
          {/* Header row: empty + hours */}
          <div />
          {HOURS.map((h) => (
            <div key={h} className="text-center text-[10px] text-lovable-ink-muted">
              {h}h
            </div>
          ))}

          {/* One row per weekday */}
          {DAYS.map((day, weekday) => (
            <>
              <div key={`label-${weekday}`} className="flex items-center text-xs font-medium text-lovable-ink-muted">
                {day}
              </div>
              {HOURS.map((hour) => {
                const total = lookup.get(`${weekday}:${hour}`) ?? 0;
                const ratio = maxVal > 0 ? total / maxVal : 0;
                return (
                  <div
                    key={`${weekday}-${hour}`}
                    title={`${day} ${hour}h — ${total} check-in${total !== 1 ? "s" : ""}`}
                    className={`h-5 rounded-sm transition-colors ${intensityClass(ratio)}`}
                  />
                );
              })}
            </>
          ))}
        </div>
      </div>

      {/* Escala de cores */}
      <div className="mt-3 flex items-center gap-2">
        <span className="text-[10px] text-lovable-ink-muted">Menos</span>
        {[0, 0.15, 0.35, 0.55, 0.75, 1].map((r) => (
          <div key={r} className={`h-3 w-6 rounded-sm ${intensityClass(r)}`} />
        ))}
        <span className="text-[10px] text-lovable-ink-muted">Mais</span>
        <span className="ml-auto text-[10px] text-lovable-ink-muted">Máx: {maxVal}</span>
      </div>
    </div>
  );
}
