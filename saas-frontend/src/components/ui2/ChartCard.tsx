import { cn } from "./cn";

interface ChartCardProps {
  title: string;
  description?: string;
  className?: string;
  children: React.ReactNode;
}

export function ChartCard({ title, description, className, children }: ChartCardProps) {
  return (
    <section className={cn("rounded-2xl border border-lovable-border bg-lovable-surface p-4 shadow-lovable", className)}>
      <header className="mb-3">
        <h3 className="font-display text-base font-semibold text-lovable-ink">{title}</h3>
        {description ? <p className="text-xs text-lovable-ink-muted">{description}</p> : null}
      </header>
      <div className="h-72">{children}</div>
    </section>
  );
}
