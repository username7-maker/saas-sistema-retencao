import { Badge } from "../ui2/Badge";

interface RiskBadgeProps {
  risk: "green" | "yellow" | "red" | null;
}

const RISK_BADGE_MAP = {
  green: { label: "Baixo risco", variant: "success" as const },
  yellow: { label: "Risco medio", variant: "warning" as const },
  red: { label: "Alto risco", variant: "danger" as const },
};

export function RiskBadge({ risk }: RiskBadgeProps) {
  if (!risk) return null;

  const config = RISK_BADGE_MAP[risk];
  return (
    <Badge variant={config.variant} size="sm">
      {config.label}
    </Badge>
  );
}
