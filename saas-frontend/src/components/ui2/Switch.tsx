import { forwardRef, type InputHTMLAttributes } from "react";

import { cn } from "./cn";

type SwitchProps = InputHTMLAttributes<HTMLInputElement>;

export const Switch = forwardRef<HTMLInputElement, SwitchProps>(function Switch(
  { className, checked, disabled, ...props },
  ref,
) {
  return (
    <span
      className={cn(
        "relative inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full",
        "has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-[hsl(var(--lovable-primary)/0.45)] has-[:focus-visible]:ring-offset-1 has-[:focus-visible]:ring-offset-[hsl(var(--lovable-bg))]",
        disabled && "opacity-50",
        className,
      )}
    >
      <input
        ref={ref}
        type="checkbox"
        role="switch"
        checked={checked}
        disabled={disabled}
        className="peer absolute inset-0 cursor-pointer opacity-0 disabled:cursor-not-allowed"
        {...props}
      />
      <span aria-hidden="true" className="pointer-events-none relative h-[22px] w-[38px] rounded-full border border-lovable-border bg-lovable-bg-muted/82 transition peer-checked:border-[hsl(var(--lovable-primary)/0.55)] peer-checked:bg-[hsl(var(--lovable-primary)/0.55)]">
        <span className={cn("absolute left-[2px] top-[2px] h-[16px] w-[16px] rounded-full bg-white shadow-[0_1px_3px_rgba(0,0,0,0.4)] transition-transform duration-200 ease-out", checked && "translate-x-[16px]")} />
      </span>
    </span>
  );
});
