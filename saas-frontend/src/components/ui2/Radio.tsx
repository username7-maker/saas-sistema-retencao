import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "./cn";

type RadioProps = InputHTMLAttributes<HTMLInputElement>;

export const Radio = forwardRef<HTMLInputElement, RadioProps>(function Radio(
  { className, checked, disabled, ...props },
  ref,
) {
  return (
    <span
      className={cn(
        "relative inline-flex h-[18px] w-[18px] shrink-0 items-center justify-center rounded-full border transition-colors duration-150",
        "border-lovable-border bg-lovable-bg-muted/82",
        "has-[:checked]:border-[hsl(var(--lovable-primary))]",
        "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[hsl(var(--lovable-primary)/0.45)] has-[:focus-visible]:ring-offset-1 has-[:focus-visible]:ring-offset-[hsl(var(--lovable-bg))]",
        disabled && "opacity-50",
        className,
      )}
    >
      <input
        ref={ref}
        type="radio"
        checked={checked}
        disabled={disabled}
        className="peer absolute inset-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        {...props}
      />
      {checked ? (
        <span className="pointer-events-none h-[8px] w-[8px] rounded-full bg-[hsl(var(--lovable-primary))]" />
      ) : null}
    </span>
  );
});
