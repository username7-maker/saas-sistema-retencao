import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../cn";

type CommandCardVariant = "default" | "elevated" | "critical" | "success" | "warning" | "ai";

interface CommandCardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CommandCardVariant;
  interactive?: boolean;
  header?: ReactNode;
  footer?: ReactNode;
}

const variantClasses: Record<CommandCardVariant, string> = {
  default:
    "border-lovable-border/70 bg-[linear-gradient(145deg,hsl(var(--lovable-surface)/0.94),hsl(var(--lovable-bg-muted)/0.76))]",
  elevated:
    "border-[hsl(var(--lovable-primary)/0.24)] bg-[linear-gradient(145deg,hsl(var(--lovable-surface-soft)/0.95),hsl(var(--lovable-surface)/0.82))] shadow-[0_28px_80px_-44px_hsl(var(--lovable-primary)/0.55)]",
  critical:
    "border-[hsl(var(--lovable-danger)/0.3)] bg-[linear-gradient(145deg,hsl(var(--lovable-danger)/0.14),hsl(var(--lovable-surface)/0.88))]",
  success:
    "border-[hsl(var(--lovable-success)/0.28)] bg-[linear-gradient(145deg,hsl(var(--lovable-success)/0.12),hsl(var(--lovable-surface)/0.88))]",
  warning:
    "border-[hsl(var(--lovable-warning)/0.32)] bg-[linear-gradient(145deg,hsl(var(--lovable-warning)/0.13),hsl(var(--lovable-surface)/0.88))]",
  ai:
    "border-[hsl(var(--lovable-ai)/0.34)] bg-[linear-gradient(145deg,hsl(var(--lovable-ai)/0.18),hsl(var(--lovable-surface)/0.88))]",
};

export function CommandCard({
  children,
  className,
  variant = "default",
  interactive = false,
  header,
  footer,
  ...props
}: CommandCardProps) {
  return (
    <section
      className={cn(
        "relative overflow-hidden rounded-[26px] border p-5 text-lovable-ink shadow-panel backdrop-blur-2xl",
        "before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-[linear-gradient(90deg,transparent,hsl(var(--lovable-primary)/0.45),transparent)]",
        interactive
          ? "transition duration-200 hover:-translate-y-0.5 hover:border-lovable-border-strong/70 hover:shadow-[0_32px_92px_-46px_hsl(var(--lovable-primary)/0.72)]"
          : "",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {header ? <div className="relative mb-4">{header}</div> : null}
      <div className="relative">{children}</div>
      {footer ? <div className="relative mt-5 border-t border-lovable-border/55 pt-4">{footer}</div> : null}
    </section>
  );
}
