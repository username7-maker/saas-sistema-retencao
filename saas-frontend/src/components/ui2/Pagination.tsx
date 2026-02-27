import { ChevronLeft, ChevronRight } from "lucide-react";

import { cn } from "./cn";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

type PageToken = number | "...";

function buildPageTokens(page: number, totalPages: number): PageToken[] {
  if (totalPages <= 5) {
    return Array.from({ length: totalPages }, (_, index) => index + 1);
  }

  if (page <= 3) {
    return [1, 2, 3, 4, "...", totalPages];
  }

  if (page >= totalPages - 2) {
    return [1, "...", totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
  }

  return [1, "...", page - 1, page, page + 1, "...", totalPages];
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  if (totalPages <= 1) {
    return null;
  }

  const tokens = buildPageTokens(page, totalPages);

  return (
    <nav className="flex flex-wrap items-center justify-end gap-1" aria-label="Paginacao">
      <button
        type="button"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        className="inline-flex h-8 items-center gap-1 rounded-lg border border-lovable-border px-2 text-xs font-semibold text-lovable-ink disabled:cursor-not-allowed disabled:opacity-50"
      >
        <ChevronLeft size={14} />
        Anterior
      </button>

      {tokens.map((token, index) =>
        token === "..." ? (
          <span key={`ellipsis-${index}`} className="px-2 text-xs text-lovable-ink-muted">
            ...
          </span>
        ) : (
          <button
            key={token}
            type="button"
            onClick={() => onPageChange(token)}
            className={cn(
              "h-8 min-w-8 rounded-lg px-2 text-xs font-semibold transition",
              token === page
                ? "bg-lovable-primary text-white"
                : "border border-lovable-border text-lovable-ink hover:bg-lovable-surface-soft",
            )}
            aria-current={token === page ? "page" : undefined}
          >
            {token}
          </button>
        ),
      )}

      <button
        type="button"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        className="inline-flex h-8 items-center gap-1 rounded-lg border border-lovable-border px-2 text-xs font-semibold text-lovable-ink disabled:cursor-not-allowed disabled:opacity-50"
      >
        Proximo
        <ChevronRight size={14} />
      </button>
    </nav>
  );
}
