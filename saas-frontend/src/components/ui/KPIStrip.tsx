import { Badge, cn } from "../ui2";

export interface KPIItem {
  label: string;
  value: string | number;
  trend?: { value: number; positive?: boolean };
  tone?: "neutral" | "success" | "warning" | "danger";
  onClick?: () => void;
}

interface KPIStripProps {
  items: KPIItem[];
}

const toneAccentClasses: Record<NonNullable<KPIItem["tone"]>, string> = {
  neutral: "bg-lovable-border-strong",
  success: "bg-[hsl(var(--lovable-success))]",
  warning: "bg-[hsl(var(--lovable-warning))]",
  danger: "bg-[hsl(var(--lovable-danger))]",
};

function formatTrendValue(value: number): string {
  return `${value > 0 ? "+" : ""}${value}%`;
}

function getTrendVariant(trend?: KPIItem["trend"]): "neutral" | "success" | "danger" {
  if (!trend) return "neutral";
  if (trend.positive === true) return "success";
  if (trend.positive === false) return "danger";
  return trend.value >= 0 ? "success" : "danger";
}

function KPIItemCard({ item }: { item: KPIItem }) {
  const tone = item.tone ?? "neutral";
  const sharedClassName = cn(
    "rounded-xl border border-lovable-border bg-lovable-surface px-4 py-3 text-left transition",
    item.onClick ? "hover:border-lovable-border-strong hover:bg-lovable-surface-soft" : undefined,
  );

  const content = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-2">
          <div className="inline-flex items-center gap-2">
            <span className={cn("h-2 w-2 rounded-full", toneAccentClasses[tone])} aria-hidden="true" />
            <p className="text-[11px] uppercase tracking-widest text-lovable-ink-muted">{item.label}</p>
          </div>
          <p className="font-display text-2xl font-bold text-lovable-ink">{item.value}</p>
        </div>

        {item.trend ? (
          <Badge variant={getTrendVariant(item.trend)} className="px-2 py-0.5 text-[11px] normal-case tracking-normal">
            {formatTrendValue(item.trend.value)}
          </Badge>
        ) : null}
      </div>
    </>
  );

  if (item.onClick) {
    return (
      <button type="button" onClick={item.onClick} className={sharedClassName}>
        {content}
      </button>
    );
  }

  return <div className={sharedClassName}>{content}</div>;
}

export function KPIStrip({ items }: KPIStripProps) {
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
      {items.map((item, index) => (
        <KPIItemCard key={`${item.label}-${index}`} item={item} />
      ))}
    </div>
  );
}
