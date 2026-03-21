import type { ReactNode } from "react";
import { Search, X } from "lucide-react";

import { Button, Input, Select, cn } from "../ui2";

export interface FilterItem {
  key: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
}

interface FilterBarProps {
  search?: { value: string; onChange: (value: string) => void; placeholder?: string };
  filters?: FilterItem[];
  activeCount?: number;
  onClear?: () => void;
}

function FilterControl({ filter }: { filter: FilterItem }) {
  return (
    <label className="flex items-center gap-2">
      <span className="sr-only">{filter.label}</span>
      <Select
        aria-label={filter.label}
        value={filter.value}
        onChange={(event) => filter.onChange(event.target.value)}
        className="h-9 max-w-[180px] rounded-lg"
      >
        {filter.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </Select>
    </label>
  );
}

function SearchControl({
  search,
  trailing,
}: {
  search: NonNullable<FilterBarProps["search"]>;
  trailing?: ReactNode;
}) {
  return (
    <div className="flex min-w-[220px] flex-1 items-center gap-2 lg:mr-1 lg:border-r lg:border-lovable-border lg:pr-3">
      <div className="relative min-w-0 flex-1">
        <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-lovable-ink-muted" />
        <Input
          value={search.value}
          onChange={(event) => search.onChange(event.target.value)}
          placeholder={search.placeholder ?? "Buscar..."}
          className="h-9 rounded-lg pl-9"
        />
      </div>
      {trailing}
    </div>
  );
}

export function FilterBar({ search, filters, activeCount = 0, onClear }: FilterBarProps) {
  const hasFilters = Boolean(filters?.length);
  const canClear = activeCount > 0 && Boolean(onClear);

  return (
    <div className="flex flex-wrap items-center gap-2">
      {search ? (
        <SearchControl
          search={search}
          trailing={
            canClear ? (
              <Button size="sm" variant="ghost" onClick={onClear} className="h-9 rounded-xl px-2 text-xs text-lovable-ink-muted">
                <X size={14} />
                Limpar filtros
              </Button>
            ) : undefined
          }
        />
      ) : canClear ? (
        <Button size="sm" variant="ghost" onClick={onClear} className="h-9 rounded-xl px-2 text-xs text-lovable-ink-muted">
          <X size={14} />
          Limpar filtros
        </Button>
      ) : null}

      {hasFilters ? (
        <div className={cn("flex flex-wrap items-center gap-2", !search && canClear ? "lg:ml-1" : undefined)}>
          {filters?.map((filter) => (
            <FilterControl key={filter.key} filter={filter} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
