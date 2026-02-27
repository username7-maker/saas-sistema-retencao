import { cn } from "./cn";

export function Table({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("overflow-hidden rounded-2xl border border-lovable-border bg-lovable-surface", className)} {...props} />
  );
}

export function TableInner({ className, ...props }: React.TableHTMLAttributes<HTMLTableElement>) {
  return <table className={cn("min-w-full divide-y divide-lovable-border", className)} {...props} />;
}

export function TableHead({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("bg-lovable-surface-soft", className)} {...props} />;
}

export function TableBody({ className, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("divide-y divide-lovable-border", className)} {...props} />;
}

export function TableRow({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("transition hover:bg-lovable-primary-soft/40", className)} {...props} />;
}

export function TableHeaderCell({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-lovable-ink-muted", className)}
      {...props}
    />
  );
}

export function TableCell({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-3 text-sm text-lovable-ink", className)} {...props} />;
}
