import { X } from "lucide-react";
import { OAuthButton } from "./OAuthButton";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-[var(--bg-elevated)] border border-[var(--border)] rounded-xl p-6 shadow-xl w-full max-w-md mx-4">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[var(--fg-muted)] hover:text-[var(--fg)]"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold mb-2">Welcome to Forcecast</h2>
          <p className="text-[var(--fg-muted)]">Sign in to vote and participate</p>
        </div>

        <div className="space-y-3">
          <OAuthButton provider="github" />
          <OAuthButton provider="google" />
        </div>

        <p className="mt-6 text-center text-xs text-[var(--fg-muted)]">
          By signing in, you agree to our Terms of Service and Privacy Policy
        </p>
      </div>
    </div>
  );
}
