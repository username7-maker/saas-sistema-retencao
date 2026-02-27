import { createContext, useContext, useMemo, useState } from "react";

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
      className={cn("inline-flex rounded-xl border border-lovable-border bg-lovable-surface-soft p-1", className)}
      {...props}
    />
  );
}

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
}

export function TabsTrigger({ className, value, ...props }: TabsTriggerProps) {
  const context = useContext(TabsContext);
  if (!context) throw new Error("TabsTrigger must be used within Tabs");
  const active = context.value === value;

  return (
    <button
      type="button"
      className={cn(
        "rounded-lg px-3 py-1.5 text-xs font-semibold uppercase tracking-wide transition",
        active ? "bg-lovable-primary text-white" : "text-lovable-ink-muted hover:text-lovable-ink",
        className,
      )}
      onClick={() => context.setValue(value)}
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
  return <div className={className} {...props} />;
}
