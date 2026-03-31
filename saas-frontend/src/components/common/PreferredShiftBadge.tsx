import { Badge } from "../ui2";
import { getPreferredShiftKey, getPreferredShiftLabel } from "../../utils/preferredShift";

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
    <Badge variant={variant} size="sm" className="tracking-normal normal-case">
      {prefix ? `Turno ${label}` : label}
    </Badge>
  );
}

