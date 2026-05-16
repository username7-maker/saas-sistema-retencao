import { forwardRef } from "react";

import { cn } from "./cn";

export const Textarea = forwardRef<HTMLTextAreaElement, React.TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, ...props }, ref) {
    return (
      <textarea
        ref={ref}
        className={cn(
          "min-h-[80px] w-full resize-y rounded-xl border border-lovable-border/80 bg-lovable-bg-muted/82 px-3 py-2 text-sm text-lovable-ink shadow-[inset_0_1px_0_hsl(0_0%_100%/0.035)] backdrop-blur-sm",
          "placeholder:text-lovable-ink-muted/78 focus:border-[hsl(var(--lovable-primary)/0.65)] focus:outline-none focus:ring-2 focus:ring-lovable-primary/20",
          className,
        )}
        {...props}
      />
    );
  },
);
