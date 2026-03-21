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
        "h-10 w-full rounded-xl border border-lovable-border bg-lovable-bg-muted/80 px-3 text-sm text-lovable-ink shadow-[inset_0_1px_0_hsl(0_0%_100%/0.03)] backdrop-blur-sm",
        "placeholder:text-lovable-ink-muted/80 focus:border-[hsl(var(--lovable-primary)/0.55)] focus:outline-none focus:ring-2 focus:ring-lovable-primary/18",
        className,
      )}
      {...props}
    />
  );
});
