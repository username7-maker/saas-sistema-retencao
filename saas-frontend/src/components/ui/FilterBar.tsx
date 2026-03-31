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
    <label className="flex w-full items-center gap-2 sm:w-auto">
      <span className="sr-only">{filter.label}</span>
      <Select
        aria-label={filter.label}
        value={filter.value}
        onChange={(event) => filter.onChange(event.target.value)}
        className="h-9 w-full rounded-lg sm:max-w-[180px]"
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
    <div className="flex w-full min-w-0 flex-col gap-2 sm:flex-row sm:items-center lg:mr-1 lg:border-r lg:border-lovable-border lg:pr-3">
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
    <div className="flex flex-col items-stretch gap-2 xl:flex-row xl:items-center">
      {search ? (
        <SearchControl
          search={search}
          trailing={
            canClear ? (
              <Button
                size="sm"
                variant="ghost"
                onClick={onClear}
                className="h-9 w-full rounded-xl px-2 text-xs text-lovable-ink-muted sm:w-auto"
              >
                <X size={14} />
                Limpar filtros
              </Button>
            ) : undefined
          }
        />
      ) : canClear ? (
        <Button
          size="sm"
          variant="ghost"
          onClick={onClear}
          className="h-9 w-full rounded-xl px-2 text-xs text-lovable-ink-muted sm:w-auto"
        >
          <X size={14} />
          Limpar filtros
        </Button>
      ) : null}

      {hasFilters ? (
        <div
          className={cn(
            "grid grid-cols-1 gap-2 sm:grid-cols-2 xl:flex xl:flex-wrap xl:items-center",
            !search && canClear ? "lg:ml-1" : undefined,
          )}
        >
          {filters?.map((filter) => (
            <FilterControl key={filter.key} filter={filter} />
          ))}
        </div>
      ) : null}
    </div>
  );
}
