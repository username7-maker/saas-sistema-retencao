import { useEffect, useId, useRef } from "react";
import { createPortal } from "react-dom";

import { cn } from "./cn";

interface DialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children?: React.ReactNode;
  size?: "sm" | "md";
}

const sizeClasses: Record<NonNullable<DialogProps["size"]>, string> = {
  sm: "max-w-md",
  md: "max-w-2xl",
};

const focusableSelector = [
  "a[href]",
  "area[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

export function Dialog({ open, onClose, title, description, children, size = "sm" }: DialogProps) {
  const titleId = useId();
  const descriptionId = useId();
  const panelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) {
      return undefined;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    const panel = panelRef.current;
    const focusable = panel?.querySelectorAll<HTMLElement>(focusableSelector);
    const first = focusable?.[0];
    (first ?? panel)?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
        return;
      }

      if (event.key !== "Tab") {
        return;
      }

      const currentPanel = panelRef.current;
      const nodes = currentPanel?.querySelectorAll<HTMLElement>(focusableSelector);
      if (!nodes || nodes.length === 0) {
        event.preventDefault();
        currentPanel?.focus();
        return;
      }

      const firstNode = nodes[0];
      const lastNode = nodes[nodes.length - 1];
      const activeElement = document.activeElement as HTMLElement | null;

      if (event.shiftKey) {
        if (activeElement === firstNode || activeElement === currentPanel) {
          event.preventDefault();
          lastNode.focus();
        }
        return;
      }

      if (activeElement === lastNode) {
        event.preventDefault();
        firstNode.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return createPortal(
    <div className="fixed inset-0 z-[90] flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-lovable-ink/40"
        onClick={onClose}
        aria-label="Fechar dialog"
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={description ? descriptionId : undefined}
        tabIndex={-1}
        className={cn(
          "relative z-10 w-full rounded-2xl bg-lovable-surface p-5 shadow-panel outline-none transition duration-200 ease-out",
          "scale-100 opacity-100",
          sizeClasses[size],
        )}
      >
        <h3 id={titleId} className="text-lg font-semibold text-lovable-ink">
          {title}
        </h3>
        {description ? (
          <p id={descriptionId} className="mt-1 text-sm text-lovable-ink-muted">
            {description}
          </p>
        ) : null}
        {children ? <div className="mt-4">{children}</div> : null}
      </div>
    </div>,
    document.body,
  );
}
