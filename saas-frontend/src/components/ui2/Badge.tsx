import { cn } from "./cn";

type BadgeVariant = "neutral" | "success" | "warning" | "danger";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const badgeClasses: Record<BadgeVariant, string> = {
  neutral: "bg-slate-100 text-slate-700 dark:bg-slate-700/60 dark:text-slate-100",
  success: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-200",
  warning: "bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-200",
  danger: "bg-rose-100 text-rose-700 dark:bg-rose-900/40 dark:text-rose-200",
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
