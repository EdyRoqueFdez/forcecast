import { cn, formatNumber, formatPrice, slugToInitials } from "../lib/utils";
import { tCategory } from "../types";
import type { Model, Locale } from "../types";

interface ModelCardProps {
  model: Model;
  isSelected: boolean;
  onClick: () => void;
  locale: Locale;
}

export function ModelCard({ model, isSelected, onClick, locale }: ModelCardProps) {
  return (
    <article
      className={cn("model-card", isSelected && "model-card-selected")}
      onClick={onClick}
      onKeyDown={e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onClick(); } }}
      tabIndex={0}
      role="listitem"
      data-slug={model.slug}
    >
      <div className="flex items-start gap-3 mb-3">
        <div className="model-avatar w-10 h-10 flex-shrink-0 rounded-lg bg-[var(--accent-dim)] flex items-center justify-center font-bold text-[var(--accent)] text-lg">
          {slugToInitials(model.slug)}
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-base truncate">{model.display_name}</h3>
          <p className="text-sm text-[var(--fg-muted)]">{model.provider.name}</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {model.modality.map(mod => (
          <span key={mod} className="badge badge-modality">{mod}</span>
        ))}
        {model.categories.map(cat => (
          <span key={cat} className="badge badge-category">{tCategory(cat, locale)}</span>
        ))}
      </div>

      <div className="grid grid-cols-3 gap-2 pt-4 border-t border-[var(--border)] text-sm">
        <div className="text-center">
          <div className="font-bold">{formatNumber(model.context_window)}</div>
          <div className="text-[var(--fg-muted)] text-xs uppercase">Context</div>
        </div>
        <div className="text-center">
          <div className="font-bold">{formatNumber(model.max_output_tokens)}</div>
          <div className="text-[var(--fg-muted)] text-xs uppercase">Max Out</div>
        </div>
        <div className="text-center">
          <div className="font-bold">{model.release_date}</div>
          <div className="text-[var(--fg-muted)] text-xs uppercase">Released</div>
        </div>
      </div>

      <div className="flex justify-between pt-3 border-t border-[var(--border)] text-sm text-[var(--fg-muted)]">
        <span>In: {formatPrice(model.input_price_per_mtok)}</span>
        <span>Out: {formatPrice(model.output_price_per_mtok)}</span>
      </div>
    </article>
  );
}