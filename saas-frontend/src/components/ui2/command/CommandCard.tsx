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
    "border-white/[0.07] bg-[linear-gradient(145deg,rgba(14,16,24,0.97),rgba(10,11,15,0.93))]",
  elevated:
    // Blue accent — primary identity
    "border-[rgba(59,130,246,0.26)] bg-[linear-gradient(145deg,rgba(59,130,246,0.08),rgba(10,11,15,0.95)_42%,rgba(10,11,15,0.99))] shadow-[0_28px_80px_-44px_rgba(59,130,246,0.45)]",
  critical:
    "border-[rgba(255,59,59,0.32)] bg-[linear-gradient(145deg,rgba(255,59,59,0.10),rgba(10,11,15,0.94))]",
  success:
    "border-[rgba(16,185,129,0.26)] bg-[linear-gradient(145deg,rgba(16,185,129,0.09),rgba(10,11,15,0.94))]",
  warning:
    "border-[rgba(245,158,11,0.30)] bg-[linear-gradient(145deg,rgba(245,158,11,0.09),rgba(10,11,15,0.94))]",
  ai:
    // Violet = IA identity; radial concentrated at top-right, not flat fill
    "border-[rgba(139,92,246,0.30)] bg-[radial-gradient(ellipse_80%_60%_at_85%_10%,rgba(139,92,246,0.10),transparent_65%),linear-gradient(145deg,rgba(14,16,24,0.97),rgba(10,11,15,0.96))]",
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
        "before:pointer-events-none before:absolute before:inset-x-0 before:top-0 before:h-px before:bg-[linear-gradient(90deg,transparent,rgba(59,130,246,0.50),transparent)]",
        interactive
          ? "cursor-pointer transition-all duration-200 hover:-translate-y-[1px] hover:border-lovable-border-strong/60 hover:shadow-[var(--glow-blue)]"
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
