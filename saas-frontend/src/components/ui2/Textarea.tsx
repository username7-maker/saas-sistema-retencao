import { forwardRef } from "react";

import { cn } from "./cn";

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        className={cn(
          "min-h-[80px] w-full rounded-xl border border-lovable-border bg-lovable-surface px-3 py-2 text-sm text-lovable-ink resize-y",
          "placeholder:text-lovable-ink-muted focus:border-lovable-border-strong focus:outline-none focus:ring-2 focus:ring-lovable-primary/20",
          className,
        )}
        {...props}
      />
    );
  },
);
