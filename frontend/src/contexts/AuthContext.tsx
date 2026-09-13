import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";

// Auth types
export interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: "user" | "admin";
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in?: number;
}

export interface AuthContextType {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  handleOAuthCallback: () => Promise<void>;
  logout: () => Promise<void>;
  refreshAccessToken: () => Promise<boolean>;
}

const AuthContext = createContext<AuthContextType | null>(null);

const AUTH_STORAGE_KEY = "forcecast_auth";
const API_BASE = import.meta.env.VITE_API_BASE || "https://forcecast-mvp.fly.dev";

// Token expiry buffer (5 minutes before expiry)
const TOKEN_BUFFER_MS = 5 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [tokens, setTokens] = useState<AuthTokens | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Load tokens from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(AUTH_STORAGE_KEY);
      if (stored) {
        const data = JSON.parse(stored);
        // Check if access token is expired
        if (data.tokens && data.user) {
          const expiresAt = data.expiresAt || 0;
          if (Date.now() < expiresAt - TOKEN_BUFFER_MS) {
            setUser(data.user);
            setTokens(data.tokens);
          } else {
            // Token expired, try refresh
            refreshAccessToken();
          }
        }
      }
    } catch (e) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Persist tokens to localStorage
  useEffect(() => {
    if (tokens && user) {
      // For OAuth, we don't have expires_in from cookies
      // Default to 30 minutes for access token
      const expiresAt = Date.now() + (tokens.expires_in || 30 * 60) * 1000;
      localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify({ tokens, user, expiresAt }));
    }
  }, [tokens, user]);

  const handleOAuthCallback = useCallback(async () => {
    // After backend callback redirects to /auth/callback,
    // the cookies are set. We need to verify the session.
    // Try to fetch user info from the backend
    try {
      const res = await fetch(`${API_BASE}/../auth/me`, {
        credentials: "include", // Include cookies
      });

      if (res.ok) {
        const userData = await res.json();
        setUser({
          id: userData.id,
          email: userData.email,
          name: userData.display_name || userData.name,
          avatar_url: userData.avatar_url,
          role: userData.role || "user",
        });
        // Tokens are in cookies, we don't need to store them in localStorage
        // But we need a dummy token object for isAuthenticated check
        setTokens({
          access_token: "cookie-based",
          refresh_token: "cookie-based",
          token_type: "bearer",
        });
      } else {
        throw new Error("Failed to get user info");
      }
    } catch (error) {
      throw error;
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch(`${API_BASE}/../auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (e) {
      // Ignore errors on logout
    }

    setUser(null);
    setTokens(null);
    localStorage.removeItem(AUTH_STORAGE_KEY);
  }, []);

  const refreshAccessToken = useCallback(async (): Promise<boolean> => {
    try {
      const res = await fetch(`${API_BASE}/../auth/refresh`, {
        method: "POST",
        credentials: "include",
      });

      if (!res.ok) {
        logout();
        return false;
      }

      const data: AuthTokens = await res.json();
      setTokens(data);
      return true;
    } catch {
      logout();
      return false;
    }
  }, [logout]);

  return (
    <AuthContext.Provider
      value={{
        user,
        tokens,
        isAuthenticated: !!user,
        isLoading,
        handleOAuthCallback,
        logout,
        refreshAccessToken,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

export { AUTH_STORAGE_KEY, API_BASE };
