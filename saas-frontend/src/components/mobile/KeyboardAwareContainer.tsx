import { useEffect, useRef, useState } from "react";

import { cn } from "../ui2/cn";

export function KeyboardAwareContainer({ children, className }: { children: React.ReactNode; className?: string }) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [keyboardInset, setKeyboardInset] = useState(0);

  useEffect(() => {
    const viewport = window.visualViewport;
    if (!viewport) return;
    const update = () => setKeyboardInset(Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop));
    const focus = (event: FocusEvent) => {
      if (!(event.target instanceof HTMLElement) || !rootRef.current?.contains(event.target)) return;
      window.setTimeout(() => event.target instanceof HTMLElement && event.target.scrollIntoView({ block: "center", behavior: "smooth" }), 80);
    };
    update();
    viewport.addEventListener("resize", update);
    viewport.addEventListener("scroll", update);
    document.addEventListener("focusin", focus);
    return () => {
      viewport.removeEventListener("resize", update);
      viewport.removeEventListener("scroll", update);
      document.removeEventListener("focusin", focus);
    };
  }, []);

  return <div ref={rootRef} className={cn("min-h-0", className)} style={{ "--keyboard-inset": `${keyboardInset}px` } as React.CSSProperties}>{children}</div>;
}
