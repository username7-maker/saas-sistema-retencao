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
        "relative inline-flex h-11 w-11 shrink-0 items-center justify-center text-white",
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
      <span className="pointer-events-none inline-flex h-[18px] w-[18px] items-center justify-center rounded-[5px] border border-lovable-border bg-lovable-bg-muted/82 peer-checked:border-[hsl(var(--lovable-primary))] peer-checked:bg-[hsl(var(--lovable-primary))]">
        {indeterminate ? <Minus size={12} strokeWidth={3} /> : checked ? <Check size={12} strokeWidth={3} /> : null}
      </span>
    </span>
  );
});
