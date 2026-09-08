import { forwardRef } from "react";
import { ChevronDown } from "lucide-react";

import { cn } from "./cn";

export const Select = forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(function Select(
  { className, children, ...props },
  ref,
) {
  return (
    <div className="relative">
      <select
        ref={ref}
        className={cn(
          "h-11 w-full appearance-none rounded-xl border border-lovable-border/80 bg-lovable-bg-muted/82 px-3 pr-9 text-base text-lovable-ink shadow-[inset_0_1px_0_hsl(0_0%_100%/0.035)] backdrop-blur-sm sm:h-10 sm:text-sm",
          "focus:border-[hsl(var(--lovable-primary)/0.65)] focus:outline-none focus:ring-2 focus:ring-lovable-primary/20",
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        size={16}
        className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted"
        aria-hidden="true"
      />
    </div>
  );
});
