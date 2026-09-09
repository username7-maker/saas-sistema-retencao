import { useLayoutEffect, useRef } from "react";

import { cn } from "../ui2/cn";

export function MobileActionBar({ children, className }: { children: React.ReactNode; className?: string }) {
  const barRef = useRef<HTMLDivElement | null>(null);
  useLayoutEffect(() => {
    const bar = barRef.current;
    const parent = bar?.parentElement;
    if (!bar || !parent || typeof ResizeObserver === "undefined") return;
    const update = () => parent.style.setProperty("--mobile-action-height", `${bar.offsetHeight}px`);
    const observer = new ResizeObserver(update);
    observer.observe(bar);
    update();
    return () => observer.disconnect();
  }, []);
  return (
    <div ref={barRef} className={cn("sticky z-30 -mx-4 flex min-h-16 gap-2 border-t border-lovable-border bg-lovable-surface/95 px-4 pb-[calc(0.75rem+env(safe-area-inset-bottom))] pt-3 backdrop-blur md:hidden", className)} style={{ bottom: "var(--keyboard-inset, 0px)" }}>
      {children}
    </div>
  );
}
