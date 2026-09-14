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

export function getProviderIcon(icon: string): string {
  const icons: Record<string, string> = {
    openai: "https://cdn.simpleicons.org/openai/10a37f",
    anthropic: "https://cdn.simpleicons.org/anthropic/d97757",
    deepseek: "https://cdn.simpleicons.org/deepseek/4d6bfe",
    meta: "https://cdn.simpleicons.org/meta/0668E1",
    google: "https://cdn.simpleicons.org/google/4285F4",
    alibaba: "https://cdn.simpleicons.org/alibaba/FF6A00",
  };
  return icons[icon] || "";
}

export function getBrowserLocale(): string {
  const lang = navigator.language.split("-")[0];
  return ["en", "es", "pt", "fr", "zh"].includes(lang) ? lang : "en";
}