import { cn } from "../lib/utils";
import type { Locale } from "../types";

interface LocaleSelectorProps {
  currentLocale: Locale;
  onChange: (locale: Locale) => void;
}

export function LocaleSelector({ currentLocale, onChange }: LocaleSelectorProps) {
  const locales: Locale[] = ["en", "es", "pt", "fr", "zh"];
  const localeNames: Record<Locale, string> = {
    en: "English",
    es: "Español",
    pt: "Português",
    fr: "Français",
    zh: "中文",
  };

  return (
    <select
      value={currentLocale}
      onChange={e => onChange(e.target.value as Locale)}
      className="select text-sm py-2 px-3 min-w-[130px]"
      aria-label="Language"
    >
      {locales.map(locale => (
        <option key={locale} value={locale}>
          {localeNames[locale]}
        </option>
      ))}
    </select>
  );
}