import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";

import { cn } from "./cn";

interface TabsContextValue {
  value: string;
  setValue: (value: string) => void;
}

const TabsContext = createContext<TabsContextValue | undefined>(undefined);

interface TabsProps {
  value?: string;
  defaultValue?: string;
  onValueChange?: (value: string) => void;
  className?: string;
  children: React.ReactNode;
}

export function Tabs({ value, defaultValue = "", onValueChange, className, children }: TabsProps) {
  const [internalValue, setInternalValue] = useState(defaultValue);
  const resolvedValue = value ?? internalValue;

  const contextValue = useMemo(
    () => ({
      value: resolvedValue,
      setValue: (next: string) => {
        if (value === undefined) {
          setInternalValue(next);
        }
        onValueChange?.(next);
      },
    }),
    [resolvedValue, value, onValueChange],
  );

  return (
    <TabsContext.Provider value={contextValue}>
      <div className={className}>{children}</div>
    </TabsContext.Provider>
  );
}

export function TabsList({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "relative inline-flex max-w-full overflow-x-auto rounded-2xl border border-lovable-border bg-lovable-bg-muted/72 p-1 shadow-[inset_0_1px_0_hsl(196_100%_92%/0.04)]",
        className,
      )}
      role="tablist"
      {...props}
    />
  );
}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

export function TabsTrigger({ className, value, onClick, onKeyDown, ...props }: TabsTriggerProps) {
  const context = useContext(TabsContext);
  if (!context) throw new Error("TabsTrigger must be used within Tabs");
  const active = context.value === value;
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    const trigger = triggerRef.current;
    if (active && typeof trigger?.scrollIntoView === "function") {
      trigger.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "center" });
    }
  }, [active]);

  return (
    <button
      ref={triggerRef}
      type="button"
      role="tab"
      aria-selected={active}
      tabIndex={active ? 0 : -1}
      className={cn(
        "shrink-0 rounded-xl px-3 py-1.5 text-xs font-semibold uppercase tracking-[0.14em] transition",
        active
          ? "border border-[hsl(var(--lovable-primary)/0.48)] bg-[linear-gradient(135deg,hsl(var(--lovable-primary)/0.32),hsl(var(--lovable-info)/0.14))] text-lovable-ink shadow-[0_12px_32px_-20px_hsl(var(--lovable-primary)/0.7)]"
          : "text-lovable-ink-muted hover:bg-lovable-surface-soft hover:text-lovable-ink",
        className,
      )}
      onClick={(event) => {
        context.setValue(value);
        onClick?.(event);
      }}
      onKeyDown={(event) => {
        onKeyDown?.(event);
        if (event.defaultPrevented || !["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
        const tabs = [...(event.currentTarget.closest('[role="tablist"]')?.querySelectorAll<HTMLButtonElement>('[role="tab"]') ?? [])];
        if (!tabs.length) return;
        event.preventDefault();
        const current = tabs.indexOf(event.currentTarget);
        const nextIndex = event.key === "Home" ? 0 : event.key === "End" ? tabs.length - 1 : event.key === "ArrowRight" ? (current + 1) % tabs.length : (current - 1 + tabs.length) % tabs.length;
        tabs[nextIndex]?.focus();
        tabs[nextIndex]?.click();
      }}
      {...props}
    />
  );
}

interface TabsContentProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
}

export function TabsContent({ className, value, ...props }: TabsContentProps) {
  const context = useContext(TabsContext);
  if (!context) throw new Error("TabsContent must be used within Tabs");
  if (context.value !== value) return null;
  return <div role="tabpanel" tabIndex={0} className={className} {...props} />;
}
