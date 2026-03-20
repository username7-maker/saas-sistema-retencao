import { Badge } from "../ui2";

interface StatusBadgeProps {
  status: string;
  map: Record<string, { label: string; variant: "neutral" | "success" | "warning" | "danger" }>;
}

export function StatusBadge({ status, map }: StatusBadgeProps) {
  const config = map[status];

  if (!config) {
    return <Badge variant="neutral">{status}</Badge>;
  }

  return <Badge variant={config.variant}>{config.label}</Badge>;
}
