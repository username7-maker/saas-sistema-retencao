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
          "h-10 w-full appearance-none rounded-xl border border-lovable-border bg-lovable-surface px-3 pr-9 text-sm text-lovable-ink",
          "focus:border-lovable-border-strong focus:outline-none focus:ring-2 focus:ring-lovable-primary/20",
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
