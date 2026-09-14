import { Platform } from 'react-native';
import { ApiError } from './types';

// Safe SecureStore import for web SSR
let SecureStore: any = null;
if (Platform.OS !== 'web') {
  SecureStore = require('expo-secure-store');
}

const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL
  ?? (Platform.OS === 'web' ? 'http://localhost:8000' : 'https://forcecast-mvp.fly.dev');

// Token storage keys
const ACCESS_TOKEN_KEY = 'forcecast_access_token';
const REFRESH_TOKEN_KEY = 'forcecast_refresh_token';

interface ApiRequestOptions {
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
  skipAuth?: boolean;
}

class ApiClient {
  private baseUrl: string;
  private isRefreshing = false;
  private refreshPromise: Promise<string> | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  // === Token Management ===

  async getAccessToken(): Promise<string | null> {
    if (!SecureStore) return null;
    return SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
  }

  async getRefreshToken(): Promise<string | null> {
    if (!SecureStore) return null;
    return SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  }

  async setTokens(accessToken: string, refreshToken: string): Promise<void> {
    if (!SecureStore) return;
    await Promise.all([
      SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken),
      SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken),
    ]);
  }

  async clearTokens(): Promise<void> {
    if (!SecureStore) return;
    await Promise.all([
      SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY),
      SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY),
    ]);
  }

  // === Token Refresh ===

  private async refreshAccessToken(): Promise<string> {
    const refreshToken = await this.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await fetch(`${this.baseUrl}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      await this.clearTokens();
      throw new Error('Token refresh failed');
    }

    const data = await response.json();
    await this.setTokens(data.access_token, data.refresh_token);
    return data.access_token;
  }

  private async getValidAccessToken(): Promise<string | null> {
    const token = await this.getAccessToken();
    if (!token) return null;

    // Check if token is expired (decode JWT and check exp)
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      const expiresAt = payload.exp * 1000;
      const now = Date.now();

      // If token expires in less than 5 minutes, refresh it
      if (expiresAt - now < 5 * 60 * 1000) {
        if (!this.isRefreshing) {
          this.isRefreshing = true;
          this.refreshPromise = this.refreshAccessToken().finally(() => {
            this.isRefreshing = false;
            this.refreshPromise = null;
          });
        }
        return this.refreshPromise;
      }

      return token;
    } catch {
      // If token is malformed, try to refresh
      if (!this.isRefreshing) {
        this.isRefreshing = true;
        this.refreshPromise = this.refreshAccessToken().finally(() => {
          this.isRefreshing = false;
          this.refreshPromise = null;
        });
      }
      return this.refreshPromise;
    }
  }

  // === Request Execution ===

  async request<T>(endpoint: string, options: ApiRequestOptions = {}): Promise<T> {
    const { method = 'GET', headers = {}, body, skipAuth = false } = options;

    // Get auth token if needed
    let authHeaders: Record<string, string> = {};
    if (!skipAuth) {
      const token = await this.getValidAccessToken();
      if (token) {
        authHeaders['Authorization'] = `Bearer ${token}`;
      }
    }

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${endpoint}`, {
        method,
        headers: {
          'Content-Type': 'application/json',
          ...authHeaders,
          ...headers,
        },
        body: body ? JSON.stringify(body) : undefined,
      });
    } catch (error) {
      const detail = error instanceof Error ? error.message : 'Network request failed';
      throw new Error(`Unable to reach Forcecast API at ${this.baseUrl}: ${detail}`);
    }

    // Handle 401 - try refresh once
    if (response.status === 401 && !skipAuth) {
      try {
        const newToken = await this.refreshAccessToken();
        const retryResponse = await fetch(`${this.baseUrl}${endpoint}`, {
          method,
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${newToken}`,
            ...headers,
          },
          body: body ? JSON.stringify(body) : undefined,
        });

        if (!retryResponse.ok) {
          const error: ApiError = await retryResponse.json();
          throw error;
        }

        return retryResponse.json();
      } catch {
        await this.clearTokens();
        throw new Error('Authentication expired');
      }
    }

    if (!response.ok) {
      const error: ApiError = await response.json();
      throw error;
    }

    return response.json();
  }

  // === HTTP Methods ===

  get<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', headers });
  }

  post<T>(endpoint: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'POST', body, headers });
  }

  patch<T>(endpoint: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'PATCH', body, headers });
  }

  // === Auth Endpoints (skip auth header) ===

  postWithoutAuth<T>(endpoint: string, body?: unknown): Promise<T> {
    return this.request<T>(endpoint, { method: 'POST', body, skipAuth: true });
  }
}

export const apiClient = new ApiClient(API_BASE_URL);
