import { forwardRef } from "react";

import { cn } from "./cn";

export const Input = forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function Input(
  { className, ...props },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 text-sm text-lovable-ink",
        "placeholder:text-lovable-ink-muted focus:border-lovable-border-strong focus:outline-none focus:ring-2 focus:ring-lovable-primary/20",
        className,
      )}
      {...props}
    />
  );
});
