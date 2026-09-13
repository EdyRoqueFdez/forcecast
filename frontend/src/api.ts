import type { ModelsListResponse, CompareResponse, MetaResponse, Model, FilterState } from "./types";
import type { AuthTokens } from "./contexts/AuthContext";
import { AUTH_STORAGE_KEY } from "./contexts/AuthContext";

const API_BASE = import.meta.env.VITE_API_BASE || "https://forcecast-mvp.fly.dev/api/v1";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

// Get stored tokens
function getStoredTokens(): AuthTokens | null {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      return data.tokens || null;
    }
  } catch {}
  return null;
}

// Check if token is expired (with 5 min buffer)
function isTokenExpired(): boolean {
  try {
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      const data = JSON.parse(stored);
      const expiresAt = data.expiresAt || 0;
      return Date.now() >= expiresAt - 5 * 60 * 1000;
    }
  } catch {}
  return true;
}

// Refresh access token
async function refreshAccessToken(): Promise<boolean> {
  const tokens = getStoredTokens();
  if (!tokens?.refresh_token) return false;

  try {
    const res = await fetch(`${API_BASE}/../auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: tokens.refresh_token }),
    });

    if (!res.ok) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      return false;
    }

    const data: AuthTokens = await res.json();
    const stored = localStorage.getItem(AUTH_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      parsed.tokens = data;
      parsed.expiresAt = Date.now() + (data.expires_in || 30 * 60) * 1000;
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(parsed));
    }
    return true;
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return false;
  }
}

// Get auth headers (with automatic refresh)
async function getAuthHeaders(): Promise<Record<string, string>> {
  const tokens = getStoredTokens();
  if (!tokens) return {};

  if (isTokenExpired()) {
    const refreshed = await refreshAccessToken();
    if (!refreshed) return {};
    // Get the refreshed token
    const newTokens = getStoredTokens();
    if (!newTokens) return {};
    return { Authorization: `Bearer ${newTokens.access_token}` };
  }

  return { Authorization: `Bearer ${tokens.access_token}` };
}

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new ApiError(res.status, `API error: ${res.status} ${text}`);
  }

  return res.json();
}

export const api = {
  // ── Models ──────────────────────────────────────────

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

  // ── Auth ────────────────────────────────────────────

  async login(email: string, password: string): Promise<AuthTokens> {
    return fetchJson(`${API_BASE}/../auth/login`, {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
  },

  async register(email: string, password: string, name: string): Promise<AuthTokens> {
    return fetchJson(`${API_BASE}/../auth/register`, {
      method: "POST",
      body: JSON.stringify({ email, password, name }),
    });
  },

  async refreshToken(refreshToken: string): Promise<AuthTokens> {
    return fetchJson(`${API_BASE}/../auth/refresh`, {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async logout(refreshToken: string): Promise<void> {
    await fetchJson(`${API_BASE}/../auth/logout`, {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  async getCurrentUser(): Promise<{ id: string; email: string; name: string; role: string }> {
    return fetchJson(`${API_BASE}/../auth/me`);
  },

  // ── Voting ──────────────────────────────────────────

  async getVoteEvents(params?: {
    category?: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ data: unknown[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set("category", params.category);
    if (params?.status) searchParams.set("status", params.status);
    if (params?.limit) searchParams.set("limit", String(params.limit));
    if (params?.offset) searchParams.set("offset", String(params.offset));
    return fetchJson(`${API_BASE}/../voting/events?${searchParams.toString()}`);
  },

  async createVote(eventId: string, modelSlug: string, voteType: "upvote" | "downvote", turnstileToken?: string): Promise<unknown> {
    const body: Record<string, unknown> = { event_id: eventId, model_slug: modelSlug, vote_type: voteType };
    if (turnstileToken) {
      body.turnstile_token = turnstileToken;
    }
    return fetchJson(`${API_BASE}/../voting/votes`, {
      method: "POST",
      body: JSON.stringify(body),
    });
  },

  async deleteVote(eventId: string, modelSlug: string): Promise<void> {
    await fetchJson(`${API_BASE}/../voting/votes`, {
      method: "DELETE",
      body: JSON.stringify({ event_id: eventId, model_slug: modelSlug }),
    });
  },

  async getMyVotes(): Promise<{ data: unknown[] }> {
    return fetchJson(`${API_BASE}/../voting/me/votes`);
  },
};
