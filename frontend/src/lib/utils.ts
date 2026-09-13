import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(p: number | null | undefined): string {
  if (p === null || p === undefined) return "—";
  return `$${p.toFixed(2)} / 1M tok`;
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + "M";
  if (n >= 1_000) return (n / 1_000).toFixed(1) + "K";
  return n.toLocaleString();
}

export function slugToInitials(slug: string): string {
  return slug
    .split(/[-_]/)
    .map(w => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2);
}

export function getBrowserLocale(): string {
  const lang = navigator.language.split("-")[0];
  return ["en", "es", "pt", "fr", "zh"].includes(lang) ? lang : "en";
}