import type { MemberConstraints } from "../../services/assessmentService";

interface ConstraintsAlertProps {
  constraints: MemberConstraints | null;
}

interface RestrictionTag {
  label: string;
  tone: "danger" | "warning";
}

function normalizeText(value: string): string {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function extractRestrictionTags(constraints: MemberConstraints): RestrictionTag[] {
  const source = normalizeText(
    [
      constraints.medical_conditions ?? "",
      constraints.injuries ?? "",
      constraints.medications ?? "",
      constraints.contraindications ?? "",
      JSON.stringify(constraints.restrictions ?? {}),
      constraints.notes ?? "",
    ].join(" "),
  );

  const tags: RestrictionTag[] = [];
  const push = (label: string, tone: RestrictionTag["tone"]) => {
    if (!tags.find((tag) => tag.label === label)) {
      tags.push({ label, tone });
    }
  };

  if (source.includes("ombro")) push("CUIDADO: OMBRO", "danger");
  if (source.includes("joelho")) push("CUIDADO: JOELHO", "danger");
  if (source.includes("coluna") || source.includes("hernia") || source.includes("l4") || source.includes("l5")) {
    push("CUIDADO: COLUNA", "danger");
  }
  if (source.includes("pressao") || source.includes("hipertens")) push("ATENCAO: PRESSAO", "danger");
  if (source.includes("diabet")) push("ATENCAO: DIABETES", "warning");
  if (source.includes("labirint")) push("ATENCAO: LABIRINTITE", "warning");

  return tags;
}

function hasAnyConstraint(constraints: MemberConstraints | null): boolean {
  if (!constraints) return false;
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
  if (!constraints || !hasAnyConstraint(constraints)) {
    return (
      <section className="rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-panel">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Restricoes</h3>
        <p className="mt-2 text-sm text-lovable-ink-muted">Nenhuma restricao critica cadastrada.</p>
      </section>
    );
  }

  const restrictionItems = Object.entries(constraints.restrictions ?? {});
  const tags = extractRestrictionTags(constraints);
  const hasCriticalTags = tags.some((tag) => tag.tone === "danger");

  return (
    <section
      className={`rounded-2xl border p-4 shadow-panel ${hasCriticalTags ? "animate-pulse border-lovable-danger/70 bg-lovable-danger/10" : "border-lovable-warning/60 bg-lovable-warning/10"}`}
    >
      <h3 className="text-sm font-semibold uppercase tracking-wider text-lovable-ink-muted">Restricoes (atencao)</h3>

      {tags.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-2">
          {tags.map((tag) => (
            <span
              key={tag.label}
              className={`rounded-full px-3 py-1 text-[10px] font-bold uppercase tracking-wider ${
                tag.tone === "danger"
                  ? "bg-lovable-danger/20 text-lovable-danger"
                  : "bg-lovable-warning/25 text-lovable-warning"
              }`}
            >
              {tag.label}
            </span>
          ))}
        </div>
      ) : null}

      <div className="mt-3 space-y-2 text-sm text-lovable-ink">
        {constraints.medical_conditions ? (
          <p>
            <span className="font-semibold">Saude:</span> {constraints.medical_conditions}
          </p>
        ) : null}
        {constraints.injuries ? (
          <p>
            <span className="font-semibold">Lesoes:</span> {constraints.injuries}
          </p>
        ) : null}
        {constraints.medications ? (
          <p>
            <span className="font-semibold">Medicacoes:</span> {constraints.medications}
          </p>
        ) : null}
        {constraints.contraindications ? (
          <p>
            <span className="font-semibold">Contraindicacoes:</span> {constraints.contraindications}
          </p>
        ) : null}
      </div>

      {restrictionItems.length > 0 ? (
        <ul className="mt-3 list-disc space-y-1 pl-5 text-xs text-lovable-ink-muted">
          {restrictionItems.map(([key, value]) => (
            <li key={key}>
              {key}: {String(value)}
            </li>
          ))}
        </ul>
      ) : null}

      {constraints.notes ? (
        <p className="mt-3 rounded-lg bg-lovable-surface-soft px-3 py-2 text-xs text-lovable-ink-muted">{constraints.notes}</p>
      ) : null}
    </section>
  );
}
