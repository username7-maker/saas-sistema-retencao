import { cn } from "./cn";

type BadgeVariant = "neutral" | "success" | "warning" | "danger";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const badgeClasses: Record<BadgeVariant, string> = {
  neutral: "bg-lovable-surface-soft text-lovable-ink-muted",
  success: "bg-[hsl(var(--lovable-success)/0.15)] text-[hsl(var(--lovable-success))]",
  warning: "bg-[hsl(var(--lovable-warning)/0.15)] text-[hsl(var(--lovable-warning))]",
  danger: "bg-[hsl(var(--lovable-danger)/0.15)] text-[hsl(var(--lovable-danger))]",
};

export function Badge({ className, variant = "neutral", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide",
        badgeClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
