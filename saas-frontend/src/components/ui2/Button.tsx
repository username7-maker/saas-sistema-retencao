import { forwardRef } from "react";

import { cn } from "./cn";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    "bg-lovable-primary text-white hover:brightness-105 focus-visible:ring-lovable-primary/30 dark:text-slate-950",
  secondary:
    "border border-lovable-border bg-lovable-surface text-lovable-ink hover:bg-lovable-primary-soft/60 focus-visible:ring-lovable-border-strong/30",
  ghost:
    "text-lovable-ink hover:bg-lovable-primary-soft/40 focus-visible:ring-lovable-border-strong/30",
  danger: "bg-lovable-danger text-white hover:brightness-105 focus-visible:ring-lovable-danger/30",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "h-8 rounded-lg px-3 text-xs",
  md: "h-10 rounded-xl px-4 text-sm",
  lg: "h-11 rounded-xl px-5 text-sm",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, variant = "primary", size = "md", type = "button", ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 font-semibold transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60",
        "ring-offset-lovable-surface dark:ring-offset-lovable-bg",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    />
  );
});
