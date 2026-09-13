import { useState, useCallback } from "react";
import { ThumbsUp, ThumbsDown, Loader2 } from "lucide-react";
import { TurnstileWidget } from "../auth/TurnstileWidget";
import { api } from "../../api";

interface VoteButtonProps {
  eventId: string;
  modelSlug: string;
  isFirstVote?: boolean;
  isBurst?: boolean;
  currentVote?: "upvote" | "downvote" | null;
  onVoteChange?: (vote: "upvote" | "downvote" | null) => void;
}

export function VoteButton({
  eventId,
  modelSlug,
  isFirstVote = false,
  isBurst = false,
  currentVote = null,
  onVoteChange,
}: VoteButtonProps) {
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const [showTurnstile, setShowTurnstile] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const needsTurnstile = isFirstVote || isBurst;

  const handleVote = useCallback(
    async (voteType: "upvote" | "downvote") => {
      // If Turnstile is needed and token not yet obtained, show it
      if (needsTurnstile && !turnstileToken) {
        setShowTurnstile(true);
        return;
      }

      setLoading(true);
      setError(null);

      try {
        if (currentVote === voteType) {
          // Remove vote
          await api.deleteVote(eventId, modelSlug);
          onVoteChange?.(null);
        } else {
          // Create or change vote
          await api.createVote(eventId, modelSlug, voteType, turnstileToken || undefined);
          onVoteChange?.(voteType);
        }
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "Vote failed";
        
        // Handle 403 (CAPTCHA required)
        if (message.includes("403") || message.includes("CAPTCHA")) {
          setShowTurnstile(true);
          setError("Please verify you're human");
        } else {
          setError(message);
        }
      } finally {
        setLoading(false);
      }
    },
    [eventId, modelSlug, currentVote, needsTurnstile, turnstileToken, onVoteChange]
  );

  const handleTurnstileSuccess = useCallback(
    (token: string) => {
      setTurnstileToken(token);
      setShowTurnstile(false);
      setError(null);
      // Auto-retry vote after successful verification
    },
    []
  );

  const handleTurnstileError = useCallback((err: string) => {
    setError(`Verification failed: ${err}`);
  }, []);

  return (
    <div className="flex flex-col gap-2">
      {showTurnstile && (
        <div className="p-3 border border-[var(--border)] rounded-lg bg-[var(--bg)]">
          <p className="text-sm text-[var(--fg-muted)] mb-2">
            Please verify you're human to vote
          </p>
          <TurnstileWidget
            onSuccess={handleTurnstileSuccess}
            onError={handleTurnstileError}
          />
        </div>
      )}

      {error && (
        <p className="text-sm text-red-600">{error}</p>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => handleVote("upvote")}
          disabled={loading}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
            currentVote === "upvote"
              ? "bg-green-500/10 border-green-500/30 text-green-600"
              : "border-[var(--border)] hover:bg-[var(--border)]/50"
          }`}
          aria-label="Upvote"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ThumbsUp className="w-4 h-4" />
          )}
          <span className="text-sm font-medium">Upvote</span>
        </button>

        <button
          onClick={() => handleVote("downvote")}
          disabled={loading}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors ${
            currentVote === "downvote"
              ? "bg-red-500/10 border-red-500/30 text-red-600"
              : "border-[var(--border)] hover:bg-[var(--border)]/50"
          }`}
          aria-label="Downvote"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <ThumbsDown className="w-4 h-4" />
          )}
          <span className="text-sm font-medium">Downvote</span>
        </button>
      </div>
    </div>
  );
}
