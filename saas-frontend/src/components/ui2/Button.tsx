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
    "border border-[hsl(var(--lovable-primary)/0.7)] bg-lovable-primary text-white shadow-[0_18px_42px_-24px_hsl(var(--lovable-primary)/0.8)] hover:-translate-y-0.5 hover:brightness-110 focus-visible:ring-lovable-primary/30",
  secondary:
    "border border-lovable-border bg-lovable-surface-soft text-lovable-ink hover:border-lovable-border-strong hover:bg-lovable-surface focus-visible:ring-lovable-border-strong/30",
  ghost:
    "border border-transparent text-lovable-ink-muted hover:bg-lovable-surface-soft hover:text-lovable-ink focus-visible:ring-lovable-border-strong/30",
  danger:
    "border border-[hsl(var(--lovable-danger)/0.5)] bg-[hsl(var(--lovable-danger)/0.16)] text-[hsl(var(--lovable-danger))] hover:bg-[hsl(var(--lovable-danger)/0.22)] focus-visible:ring-lovable-danger/30",
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
