import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";

export function AuthCallback() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { handleOAuthCallback } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const errorParam = searchParams.get("error");
    if (errorParam) {
      setError(errorParam);
      return;
    }

    // Try to get tokens from cookies (set by backend callback)
    // The backend redirects to /auth/callback after setting cookies
    // We need to verify the session exists
    handleOAuthCallback()
      .then(() => {
        navigate("/");
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Authentication failed");
      });
  }, [searchParams, navigate, handleOAuthCallback]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-[var(--danger)] mb-4">Authentication Error</h2>
          <p className="text-[var(--fg-muted)] mb-6">{error}</p>
          <button
            onClick={() => navigate("/")}
            className="px-4 py-2 rounded-lg bg-[var(--accent)] text-[var(--bg)] font-medium"
          >
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
      <div className="text-center">
        <div className="w-12 h-12 border-4 border-[var(--accent)] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-[var(--fg-muted)]">Completing authentication...</p>
      </div>
    </div>
  );
}
