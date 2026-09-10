import { useEffect, useRef, useState } from "react";

import { cn } from "../ui2/cn";

export function KeyboardAwareContainer({ children, className }: { children: React.ReactNode; className?: string }) {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const [keyboardInset, setKeyboardInset] = useState(0);

  useEffect(() => {
    const viewport = window.visualViewport;
    let timer: number | undefined;
    let originalScroll: number | null = null;
    const update = () => {
      const inset = viewport ? Math.max(0, window.innerHeight - viewport.height - viewport.offsetTop) : 0;
      setKeyboardInset(inset);
    };
    const focus = (event: FocusEvent) => {
      const target = event.target;
      if (!(target instanceof HTMLElement) || !target.matches("input, textarea, select, [contenteditable=true]") || !rootRef.current?.contains(target)) return;
      if (originalScroll === null) originalScroll = window.scrollY;
      window.clearTimeout(timer);
      timer = window.setTimeout(() => target.isConnected && target.scrollIntoView({ block: "center", behavior: "smooth" }), 250);
    };
    const blur = () => {
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        if (rootRef.current?.contains(document.activeElement) && document.activeElement?.matches("input, textarea, select")) return;
        if (originalScroll !== null) window.scrollTo({ top: originalScroll });
        originalScroll = null;
        update();
      }, 250);
    };
    update();
    viewport?.addEventListener("resize", update);
    viewport?.addEventListener("scroll", update);
    window.addEventListener("resize", update);
    document.addEventListener("focusin", focus);
    document.addEventListener("focusout", blur);
    return () => {
      window.clearTimeout(timer);
      viewport?.removeEventListener("resize", update);
      viewport?.removeEventListener("scroll", update);
      window.removeEventListener("resize", update);
      document.removeEventListener("focusin", focus);
      document.removeEventListener("focusout", blur);
    };
  }, []);

  return <div ref={rootRef} className={cn("min-h-0", className)} style={{ "--keyboard-inset": `${keyboardInset}px` } as React.CSSProperties}>{children}</div>;
}
