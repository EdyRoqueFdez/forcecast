// API Types
export interface Provider {
  slug: string;
  name: string;
}

export interface Model {
  slug: string;
  display_name: string;
  provider: Provider;
  family: string;
  version: string;
  modality: string[];
  context_window: number;
  max_output_tokens: number;
  input_price_per_mtok: number | null;
  output_price_per_mtok: number | null;
  release_date: string;
  status: string;
  categories: string[];
  source: string;
  source_url: string;
}

export interface ModelsListResponse {
  data: Model[];
  total: number;
  limit: number;
  offset: number;
}

export interface CompareResponse {
  models: Model[];
  count: number;
  missing: string[];
}

export interface MetaResponse {
  categories: string[];
  providers: string[];
  modalities: string[];
  total_models: number;
  version: string;
}

export type SortField = "release_date" | "input_price_per_mtok" | "output_price_per_mtok" | "display_name";
export type SortOrder = "asc" | "desc";

export interface FilterState {
  search: string;
  category: string;
  provider: string;
  modality: string;
  sort: SortField;
  order: SortOrder;
}

export type Locale = "en" | "es" | "pt" | "fr" | "zh";

export const LOCALES: Locale[] = ["en", "es", "pt", "fr", "zh"];
export const LOCALE_NAMES: Record<Locale, string> = {
  en: "English",
  es: "Español",
  pt: "Português",
  fr: "Français",
  zh: "中文",
};

export const CATEGORY_TRANSLATIONS: Record<string, Record<Locale, string>> = {
  architecture: { en: "Architecture", es: "Arquitectura", pt: "Arquitetura", fr: "Architecture", zh: "架构" },
  system_design: { en: "System Design", es: "Diseño de Sistemas", pt: "Design de Sistemas", fr: "Conception de Systèmes", zh: "系统设计" },
  coding: { en: "Coding", es: "Programación", pt: "Programação", fr: "Programmation", zh: "编程" },
  debugging: { en: "Debugging", es: "Depuración", pt: "Depuração", fr: "Débogage", zh: "调试" },
  refactoring: { en: "Refactoring", es: "Refactorización", pt: "Refatoração", fr: "Refactorisation", zh: "重构" },
  testing: { en: "Testing", es: "Pruebas", pt: "Testes", fr: "Tests", zh: "测试" },
  documentation: { en: "Documentation", es: "Documentación", pt: "Documentação", fr: "Documentation", zh: "文档" },
  research: { en: "Research", es: "Investigación", pt: "Pesquisa", fr: "Recherche", zh: "研究" },
  math: { en: "Math", es: "Matemáticas", pt: "Matemática", fr: "Mathématiques", zh: "数学" },
  logical_reasoning: { en: "Logical Reasoning", es: "Razonamiento Lógico", pt: "Raciocínio Lógico", fr: "Raisonnement Logique", zh: "逻辑推理" },
  creative_writing: { en: "Creative Writing", es: "Escritura Creativa", pt: "Escrita Criativa", fr: "Écriture Créative", zh: "创意写作" },
  translation: { en: "Translation", es: "Traducción", pt: "Tradução", fr: "Traduction", zh: "翻译" },
  multimodal: { en: "Multimodal", es: "Multimodal", pt: "Multimodal", fr: "Multimodal", zh: "多模态" },
  security: { en: "Security", es: "Seguridad", pt: "Segurança", fr: "Sécurité", zh: "安全" },
  devops: { en: "DevOps", es: "DevOps", pt: "DevOps", fr: "DevOps", zh: "DevOps" },
  ux_product: { en: "UX & Product", es: "UX y Producto", pt: "UX e Produto", fr: "UX et Produit", zh: "用户体验与产品" },
  data_analysis: { en: "Data Analysis", es: "Análisis de Datos", pt: "Análise de Dados", fr: "Analyse de Données", zh: "数据分析" },
};

export function tCategory(slug: string, locale: Locale): string {
  return CATEGORY_TRANSLATIONS[slug]?.[locale] || slug;
}