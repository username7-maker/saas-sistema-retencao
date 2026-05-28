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
    "border-white/[0.08] bg-[linear-gradient(145deg,rgba(16,16,16,0.96),rgba(3,3,3,0.88))]",
  elevated:
    "border-[rgba(0,200,255,0.26)] bg-[linear-gradient(145deg,rgba(0,200,255,0.09),rgba(8,8,8,0.94)_42%,rgba(0,0,0,0.98))] shadow-[0_28px_80px_-44px_rgba(0,200,255,0.55)]",
  critical:
    "border-[rgba(255,59,48,0.32)] bg-[linear-gradient(145deg,rgba(255,59,48,0.13),rgba(8,8,8,0.92))]",
  success:
    "border-[rgba(34,197,94,0.28)] bg-[linear-gradient(145deg,rgba(34,197,94,0.12),rgba(8,8,8,0.92))]",
  warning:
    "border-[rgba(249,115,22,0.32)] bg-[linear-gradient(145deg,rgba(249,115,22,0.12),rgba(8,8,8,0.92))]",
  ai:
    "border-[rgba(0,200,255,0.34)] bg-[linear-gradient(145deg,rgba(0,200,255,0.13),rgba(8,8,8,0.92))]",
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
        "relative overflow-hidden rounded-[18px] border p-5 text-lovable-ink shadow-panel backdrop-blur-2xl",
        "before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-[linear-gradient(90deg,transparent,rgba(0,200,255,0.55),transparent)]",
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
