import { X } from "lucide-react";

import { cn } from "./cn";

interface DrawerProps {
  open: boolean;
  onClose: () => void;
  title?: string;
  side?: "left" | "right";
  children: React.ReactNode;
}

export function Drawer({ open, onClose, title, side = "left", children }: DrawerProps) {
  return (
    <>
      <div
        className={cn(
          "fixed inset-0 z-40 bg-slate-950/45 transition",
          open ? "pointer-events-auto opacity-100" : "pointer-events-none opacity-0",
        )}
        onClick={onClose}
      />
      <aside
        className={cn(
          "fixed top-0 z-50 h-full w-80 max-w-[88vw] border-lovable-border bg-lovable-surface shadow-2xl transition-transform",
          side === "left"
            ? "left-0 border-r " + (open ? "translate-x-0" : "-translate-x-full")
            : "right-0 border-l " + (open ? "translate-x-0" : "translate-x-full"),
        )}
      >
        <header className="flex items-center justify-between border-b border-lovable-border px-4 py-3">
          <h3 className="font-display text-base font-semibold text-lovable-ink">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-lovable-ink-muted transition hover:bg-lovable-primary-soft/50 hover:text-lovable-ink"
          >
            <X size={18} />
          </button>
        </header>
        <div className="h-[calc(100%-53px)] overflow-y-auto">{children}</div>
      </aside>
    </>
  );
}
