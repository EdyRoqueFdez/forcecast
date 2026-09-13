import type { ModelsListResponse, CompareResponse, MetaResponse, Model, FilterState, SortField, SortOrder } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE || "https://forcecast-mvp.fly.dev/api/v1";

class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchJson<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, `API error: ${res.status} ${text}`);
  }
  return res.json();
}

export const api = {
  async getModels(filters: FilterState, limit = 20, offset = 0): Promise<ModelsListResponse> {
    const params = new URLSearchParams();
    if (filters.category) params.set("category", filters.category);
    if (filters.provider) params.set("provider", filters.provider);
    if (filters.modality) params.set("modality", filters.modality);
    if (filters.search) params.set("search", filters.search);
    params.set("sort", filters.sort);
    params.set("order", filters.order);
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    return fetchJson(`${API_BASE}/models?${params.toString()}`);
  },

  async getModel(slug: string): Promise<Model> {
    return fetchJson(`${API_BASE}/models/${encodeURIComponent(slug)}`);
  },

  async compareModels(slugs: string[]): Promise<CompareResponse> {
    const params = new URLSearchParams();
    slugs.forEach(s => params.append("slugs", s));
    return fetchJson(`${API_BASE}/models/compare?${params.toString()}`);
  },

  async getMeta(): Promise<MetaResponse> {
    return fetchJson(`${API_BASE}/meta`);
  },

  async health(): Promise<{ status: string; version: string }> {
    return fetchJson(`${API_BASE}/health`);
  },
};