import { ChevronDown } from "lucide-react";
import { useEffect, useState, useSyncExternalStore } from "react";

import { cn } from "../ui2/cn";

function subscribeViewport(callback: () => void) {
  if (typeof window.matchMedia !== "function") {
    window.addEventListener("resize", callback);
    return () => window.removeEventListener("resize", callback);
  }
  const media = window.matchMedia("(min-width: 768px)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
const desktopSnapshot = () => typeof window.matchMedia === "function" ? window.matchMedia("(min-width: 768px)").matches : window.innerWidth >= 768;

type MobileSectionStatus = "complete" | "incomplete" | "error" | "idle";

interface MobileSectionProps {
  id: string;
  title: string;
  summary?: string;
  status?: MobileSectionStatus;
  defaultOpen?: boolean;
  forceOpen?: boolean;
  collapsible?: boolean;
  children: React.ReactNode;
  className?: string;
}

export function MobileSection({ id, title, summary, status = "idle", defaultOpen = false, forceOpen = false, collapsible = true, children, className }: MobileSectionProps) {
  const [open, setOpen] = useState(defaultOpen || forceOpen || !collapsible);
  const desktop = useSyncExternalStore(subscribeViewport, desktopSnapshot, () => true);
  const expanded = desktop || !collapsible || open;
  useEffect(() => { if (forceOpen || !collapsible || status === "error") setOpen(true); }, [collapsible, forceOpen, status]);

  return (
    <section id={id} className={cn("rounded-2xl border border-lovable-border bg-lovable-surface", className)}>
      <button
        type="button"
        className={cn("flex min-h-11 w-full items-center justify-between gap-3 px-4 py-3 text-left md:pointer-events-none", !collapsible && "pointer-events-none")}
        aria-expanded={expanded}
        tabIndex={desktop || !collapsible ? -1 : 0}
        aria-controls={`${id}-content`}
        onClick={() => { if (collapsible && !desktop) setOpen((current) => !current); }}
      >
        <span>
          <span className="block text-sm font-semibold text-lovable-ink">{title}</span>
          {summary ? <span className="mt-0.5 block text-xs text-lovable-ink-muted">{summary}</span> : null}
        </span>
        <span className={cn("items-center gap-2 md:hidden", collapsible ? "flex" : "hidden")}>
          <span className={cn("h-2 w-2 rounded-full", status === "complete" && "bg-lovable-success", status === "error" && "bg-lovable-danger", status === "incomplete" && "bg-lovable-warning", status === "idle" && "bg-lovable-ink-muted/50")} />
          <ChevronDown size={18} className={cn("transition", open && "rotate-180")} />
        </span>
      </button>
      <div id={`${id}-content`} hidden={!expanded} className="border-t border-lovable-border p-4 md:block md:border-t-0 md:pt-0" onInvalidCapture={(event) => {
        setOpen(true);
        const field = event.target;
        if (field instanceof HTMLElement) window.requestAnimationFrame(() => field.focus());
      }}>
        {children}
      </div>
    </section>
  );
}
