import { useEffect, useMemo } from "react";
import { X } from "lucide-react";
import { cn, formatNumber, formatPrice } from "../lib/utils";
import { tCategory } from "../types";
import type { Model, Locale, CompareResponse } from "../types";

interface CompareModalProps {
  isOpen: boolean;
  onClose: () => void;
  data: CompareResponse | null;
  locale: Locale;
}

export function CompareModal({ isOpen, onClose, data, locale }: CompareModalProps) {
  useEffect(() => {
    if (isOpen) document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = ""; };
  }, [isOpen]);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", handleEsc);
    return () => window.removeEventListener("keydown", handleEsc);
  }, [onClose]);

  if (!isOpen || !data) return null;

  const models = data.models;
  const missing = data.missing;

  const rows = useMemo(() => [
    { key: "slug", label: "Slug" },
    { key: "family", label: "Family" },
    { key: "version", label: "Version" },
    { key: "modality", label: "Modalities", transform: (v: string[]) => v.join(", ") },
    { key: "context_window", label: "Context Window", transform: formatNumber },
    { key: "max_output_tokens", label: "Max Output", transform: formatNumber },
    { key: "input_price_per_mtok", label: "Input Price ($/1M)", transform: formatPrice },
    { key: "output_price_per_mtok", label: "Output Price ($/1M)", transform: formatPrice },
    { key: "release_date", label: "Released" },
    { key: "categories", label: "Categories", transform: (v: string[]) => v.map(c => tCategory(c, locale)).join(", ") },
    { key: "source", label: "Source" },
  ], [locale]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="compare-title">
      <div className="card w-full max-w-5xl max-h-[90vh] overflow-auto shadow-[0_8px_32px_rgba(0,0,0,0.4)]" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-[var(--border)] sticky top-0 bg-[var(--card)] z-10">
          <h2 id="compare-title" className="text-xl font-bold">Model Comparison</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-white/10 transition-colors" aria-label="Close">
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-[var(--bg)] sticky top-0 z-10">
                <th className="px-6 py-3 text-left font-semibold text-[var(--fg-muted)] text-sm uppercase tracking-wider w-48">Attribute</th>
                {models.map(m => (
                  <th key={m.slug} className="px-6 py-3 text-center">
                    <div className="font-semibold">{m.display_name}</div>
                    <div className="text-sm text-[var(--fg-muted)]">{m.provider.name}</div>
                  </th>
                ))}
                {missing.map(m => (
                  <th key={m} className="px-6 py-3 text-center">
                    <div className="font-semibold">{m}</div>
                    <div className="text-sm text-[var(--danger)]">Not found</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map(row => (
                <tr key={row.key} className="border-b border-[var(--border)] last:border-0">
                  <td className="px-6 py-3 font-medium text-[var(--fg-muted)] w-48">{row.label}</td>
                  {models.map(m => {
                    let val: any = m[row.key as keyof Model];
                    if (row.transform) val = row.transform(val);
                    return <td key={m.slug} className="px-6 py-3 text-center font-mono text-sm">{val ?? "—"}</td>;
                  })}
                  {missing.map(() => <td key={row.key} className="px-6 py-3 text-center text-[var(--danger)] italic">—</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}