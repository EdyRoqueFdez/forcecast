import { useCallback, useState } from "react";
import { Turnstile } from "@marsidev/react-turnstile";

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY || "";

interface TurnstileWidgetProps {
  onSuccess: (token: string) => void;
  onError?: (error: string) => void;
  onExpire?: () => void;
  theme?: "light" | "dark" | "auto";
  size?: "normal" | "compact";
  className?: string;
}

export function TurnstileWidget({
  onSuccess,
  onError,
  onExpire,
  theme = "auto",
  size = "normal",
  className,
}: TurnstileWidgetProps) {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const handleSuccess = useCallback(
    (token: string) => {
      setIsLoading(false);
      setError(null);
      onSuccess(token);
    },
    [onSuccess]
  );

  const handleError = useCallback(
    (err: string) => {
      setIsLoading(false);
      setError(err);
      onError?.(err);
    },
    [onError]
  );

  const handleExpire = useCallback(() => {
    setError("Token expired");
    onExpire?.();
  }, [onExpire]);

  if (!SITE_KEY) {
    return (
      <div className={`text-sm text-amber-600 ${className || ""}`}>
        CAPTCHA not configured
      </div>
    );
  }

  return (
    <div className={`relative ${className || ""}`}>
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-[var(--bg)]/80 rounded-lg z-10">
          <div className="animate-spin w-5 h-5 border-2 border-[var(--border)] border-t-transparent rounded-full" />
        </div>
      )}
      {error && (
        <div className="text-sm text-red-600 mb-2">
          {error} — Please try again
        </div>
      )}
      <Turnstile
        siteKey={SITE_KEY}
        onSuccess={handleSuccess}
        onError={handleError}
        onExpire={handleExpire}
        theme={theme}
        size={size}
        options={{
          appearance: "interaction-only",
        }}
      />
    </div>
  );
}
