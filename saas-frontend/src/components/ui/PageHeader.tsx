import type { ReactNode } from "react";

import { cn } from "../ui2";

export interface PageHeaderBreadcrumbItem {
  label: string;
  href?: string;
}

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  breadcrumb?: PageHeaderBreadcrumbItem[];
}

export function PageHeader({ title, subtitle, actions, breadcrumb }: PageHeaderProps) {
  return (
    <header className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
      <div className="min-w-0 space-y-3">
        {breadcrumb?.length ? (
          <nav aria-label="Breadcrumb">
            <ol className="flex flex-wrap items-center gap-1.5 text-[11px] uppercase tracking-[0.18em] text-lovable-ink-muted">
              {breadcrumb.map((item, index) => (
                <li key={`${item.label}-${index}`} className="inline-flex items-center gap-1">
                  {index > 0 ? <span className="text-lovable-border-strong">/</span> : null}
                  {item.href ? (
                    <a href={item.href} className="transition hover:text-lovable-ink">
                      {item.label}
                    </a>
                  ) : (
                    <span className={cn(index === breadcrumb.length - 1 ? "text-lovable-ink" : undefined)}>{item.label}</span>
                  )}
                </li>
              ))}
            </ol>
          </nav>
        ) : null}

        <div className="min-w-0 space-y-1">
          <h1 className="font-heading text-2xl font-bold tracking-tight text-lovable-ink md:text-[2rem]">{title}</h1>
          {subtitle ? <p className="text-sm text-lovable-ink-muted">{subtitle}</p> : null}
        </div>
      </div>

      {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2 lg:justify-end">{actions}</div> : null}
    </header>
  );
}
