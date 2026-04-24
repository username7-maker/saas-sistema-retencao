import { Badge } from "../ui2";
import { getPreferredShiftKey, getPreferredShiftLabel } from "../../utils/preferredShift";

const PREFERRED_SHIFT_HINT =
  "Turno por check-in inferido pelo padrão recente dos horários em que o aluno treina.";

export function PreferredShiftBadge({
  preferredShift,
  prefix = false,
  showFallback = false,
}: {
  preferredShift: string | null | undefined;
  prefix?: boolean;
  showFallback?: boolean;
}) {
  const label = getPreferredShiftLabel(preferredShift);
  const key = getPreferredShiftKey(preferredShift);
  if (!label && !showFallback) return null;

  const displayLabel = label ?? "Sem padrão";
  const variant = key === "morning" ? "warning" : key === "afternoon" ? "info" : "neutral";
  const title = label
    ? PREFERRED_SHIFT_HINT
    : "Ainda não há check-ins suficientes para definir o turno preferido.";

  return (
    <Badge
      variant={variant}
      size="sm"
      className="max-w-full tracking-normal normal-case"
      title={title}
      aria-label={`${prefix ? `Turno ${displayLabel}` : displayLabel}. ${title}`}
    >
      {prefix ? `Turno ${displayLabel}` : displayLabel}
    </Badge>
  );
}
