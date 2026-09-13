import { cn } from "../lib/utils";

interface CompareBarProps {
  count: number;
  onClear: () => void;
  onCompare: () => void;
}

export function CompareBar({ count, onClear, onCompare }: CompareBarProps) {
  if (count < 2) return null;

  return (
    <div
      className={cn(
        "fixed bottom-0 left-0 right-0 z-40 bg-[var(--bg)] border-t border-[var(--border)] px-4 py-3 md:px-6",
        "flex items-center justify-between gap-4"
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center gap-3 text-sm text-[var(--fg-muted)]">
        <span className="bg-[var(--accent)] text-[var(--bg)] px-3 py-1 rounded-full font-bold text-lg">
          {count}
        </span>
        <span>models selected for comparison</span>
      </div>
      <div className="flex gap-2">
        <button onClick={onClear} className="btn btn-secondary">Clear</button>
        <button onClick={onCompare} className="btn btn-primary">Compare</button>
      </div>
    </div>
  );
}