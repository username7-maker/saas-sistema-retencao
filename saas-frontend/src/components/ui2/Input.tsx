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
        "h-11 w-full rounded-xl border border-lovable-border/80 bg-lovable-bg-muted/82 px-3 text-base text-lovable-ink shadow-[inset_0_1px_0_hsl(0_0%_100%/0.035)] backdrop-blur-sm sm:h-10 sm:text-sm",
        "placeholder:text-lovable-ink-muted/78 focus:border-[hsl(var(--lovable-primary)/0.65)] focus:outline-none focus:ring-2 focus:ring-lovable-primary/20",
        className,
      )}
      {...props}
    />
  );
});
