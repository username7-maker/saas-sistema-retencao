import { Badge } from "../ui2";
import { getPreferredShiftKey, getPreferredShiftLabel } from "../../utils/preferredShift";

const PREFERRED_SHIFT_HINT =
  "Turno por check-in inferido pelo padrão recente dos horários em que o aluno treina.";

export function PreferredShiftBadge({
  preferredShift,
  prefix = false,
}: {
  preferredShift: string | null | undefined;
  prefix?: boolean;
}) {
  const label = getPreferredShiftLabel(preferredShift);
  const key = getPreferredShiftKey(preferredShift);
  if (!label) return null;

  const variant = key === "morning" ? "warning" : key === "afternoon" ? "info" : "neutral";
  return (
    <Badge
      variant={variant}
      size="sm"
      className="max-w-full tracking-normal normal-case"
      title={PREFERRED_SHIFT_HINT}
      aria-label={`${prefix ? `Turno ${label}` : label}. ${PREFERRED_SHIFT_HINT}`}
    >
      {prefix ? `Turno ${label}` : label}
    </Badge>
  );
}
