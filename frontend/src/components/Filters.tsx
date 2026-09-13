import { cn } from "../lib/utils";
import type { FilterState, Locale, SortField, SortOrder } from "../types";
import { tCategory } from "../types";

interface FiltersProps {
  filters: FilterState;
  onChange: (filters: Partial<FilterState>) => void;
  categories: string[];
  providers: string[];
  modalities: string[];
  locale: Locale;
}

const SORT_OPTIONS: { value: `${SortField},${SortOrder}`; label: string }[] = [
  { value: "release_date,desc", label: "Newest first" },
  { value: "release_date,asc", label: "Oldest first" },
  { value: "input_price_per_mtok,asc", label: "Cheapest input" },
  { value: "input_price_per_mtok,desc", label: "Most expensive input" },
  { value: "display_name,asc", label: "Name A–Z" },
];

export function Filters({ filters, onChange, categories, providers, modalities, locale }: FiltersProps) {
  const handleSortChange = (value: string) => {
    const [sort, order] = value.split(",") as [SortField, SortOrder];
    onChange({ sort, order });
  };

  return (
    <div className="flex flex-wrap gap-4 mb-6">
      <div className="flex-1 min-w-[200px]">
        <label className="block text-xs font-semibold text-[var(--fg-muted)] uppercase tracking-wider mb-1.5">
          Search
        </label>
        <input
          type="text"
          value={filters.search}
          onChange={e => onChange({ search: e.target.value })}
          placeholder="Model name, slug, family…"
          className="input"
        />
      </div>

      <div className="min-w-[160px]">
        <label className="block text-xs font-semibold text-[var(--fg-muted)] uppercase tracking-wider mb-1.5">
          Category
        </label>
        <select
          value={filters.category}
          onChange={e => onChange({ category: e.target.value })}
          className="select"
        >
          <option value="">All categories</option>
          {categories.map(cat => (
            <option key={cat} value={cat}>{tCategory(cat, locale)}</option>
          ))}
        </select>
      </div>

      <div className="min-w-[160px]">
        <label className="block text-xs font-semibold text-[var(--fg-muted)] uppercase tracking-wider mb-1.5">
          Provider
        </label>
        <select
          value={filters.provider}
          onChange={e => onChange({ provider: e.target.value })}
          className="select"
        >
          <option value="">All providers</option>
          {providers.map(p => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      <div className="min-w-[160px]">
        <label className="block text-xs font-semibold text-[var(--fg-muted)] uppercase tracking-wider mb-1.5">
          Modality
        </label>
        <select
          value={filters.modality}
          onChange={e => onChange({ modality: e.target.value })}
          className="select"
        >
          <option value="">All modalities</option>
          {modalities.map(m => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </div>

      <div className="min-w-[160px]">
        <label className="block text-xs font-semibold text-[var(--fg-muted)] uppercase tracking-wider mb-1.5">
          Sort by
        </label>
        <select
          value={`${filters.sort},${filters.order}`}
          onChange={e => handleSortChange(e.target.value)}
          className="select"
        >
          {SORT_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}