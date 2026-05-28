import { forwardRef, type InputHTMLAttributes } from "react";
import { Check, Minus } from "lucide-react";

import { cn } from "./cn";

interface CheckboxProps extends InputHTMLAttributes<HTMLInputElement> {
  indeterminate?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(function Checkbox(
  { className, indeterminate, checked, disabled, ...props },
  ref,
) {
  return (
    <span
      className={cn(
        "relative inline-flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-[5px] border transition-colors duration-150",
        "border-lovable-border bg-lovable-bg-muted/82 text-white",
        "has-[:checked]:border-[hsl(var(--lovable-primary))] has-[:checked]:bg-[hsl(var(--lovable-primary))]",
        "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[hsl(var(--lovable-primary)/0.45)] has-[:focus-visible]:ring-offset-1 has-[:focus-visible]:ring-offset-[hsl(var(--lovable-bg))]",
        disabled && "opacity-50",
        className,
      )}
    >
      <input
        ref={ref}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        className="peer absolute inset-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        aria-checked={indeterminate ? "mixed" : checked}
        {...props}
      />
      {indeterminate ? (
        <Minus size={12} strokeWidth={3} className="pointer-events-none" />
      ) : checked ? (
        <Check size={12} strokeWidth={3} className="pointer-events-none" />
      ) : null}
    </span>
  );
});
