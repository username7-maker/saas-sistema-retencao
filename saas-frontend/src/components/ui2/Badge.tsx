import { cn } from "./cn";

type BadgeVariant = "neutral" | "success" | "warning" | "danger" | "info";
type BadgeSize = "sm" | "md";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
}

const badgeClasses: Record<BadgeVariant, string> = {
  neutral: "border border-lovable-border/70 bg-lovable-surface-soft/80 text-lovable-ink-muted",
  success: "bg-[hsl(var(--lovable-success)/0.15)] text-[hsl(var(--lovable-success))]",
  warning: "bg-[hsl(var(--lovable-warning)/0.15)] text-[hsl(var(--lovable-warning))]",
  danger: "bg-[hsl(var(--lovable-danger)/0.15)] text-[hsl(var(--lovable-danger))]",
  info: "border border-[hsl(var(--lovable-primary)/0.28)] bg-[hsl(var(--lovable-primary)/0.14)] text-[hsl(var(--lovable-info))]",
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: "px-2 py-0.5 text-[10px]",
  md: "px-2.5 py-1 text-xs",
};

export function Badge({ className, variant = "neutral", size = "md", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full font-semibold uppercase tracking-wide",
        sizeClasses[size],
        badgeClasses[variant],
        className,
      )}
      {...props}
    />
  );
}
