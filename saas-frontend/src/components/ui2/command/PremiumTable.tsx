import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "../cn";

export function PremiumTable({ className, ...props }: HTMLAttributes<HTMLTableElement>) {
  return (
    <div className="overflow-hidden rounded-[22px] border border-lovable-border/70 bg-lovable-surface/64">
      <table className={cn("w-full border-collapse text-sm text-lovable-ink", className)} {...props} />
    </div>
  );
}

export function PremiumTableHead({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <thead className={cn("bg-lovable-surface-soft/72 text-lovable-ink-muted", className)} {...props} />;
}

export function PremiumTableBody({ className, ...props }: HTMLAttributes<HTMLTableSectionElement>) {
  return <tbody className={cn("divide-y divide-lovable-border/55", className)} {...props} />;
}

export function PremiumTableRow({ className, ...props }: HTMLAttributes<HTMLTableRowElement>) {
  return <tr className={cn("transition hover:bg-lovable-surface-soft/42", className)} {...props} />;
}

export function PremiumTableHeader({ className, ...props }: HTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      className={cn("px-4 py-3 text-left text-[11px] font-bold uppercase tracking-[0.22em]", className)}
      {...props}
    />
  );
}

export function PremiumTableCell({ className, children, ...props }: HTMLAttributes<HTMLTableCellElement> & { children?: ReactNode }) {
  return (
    <td className={cn("px-4 py-3 align-middle text-sm", className)} {...props}>
      {children}
    </td>
  );
}
