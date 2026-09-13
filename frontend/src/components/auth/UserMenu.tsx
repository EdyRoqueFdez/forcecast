import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { User, LogOut, Settings, ChevronDown } from "lucide-react";

export function UserMenu() {
  const { user, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);

  if (!isAuthenticated || !user) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg-elevated)] hover:border-[var(--accent)] transition-colors"
      >
        {user.avatar_url ? (
          <img
            src={user.avatar_url}
            alt={user.name}
            className="w-8 h-8 rounded-full"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-[var(--accent)]/20 flex items-center justify-center">
            <User className="w-4 h-4 text-[var(--accent)]" />
          </div>
        )}
        <span className="text-sm font-medium hidden sm:block">{user.name}</span>
        <ChevronDown className="w-4 h-4 text-[var(--fg-muted)]" />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-full mt-2 w-56 py-1 bg-[var(--bg-elevated)] border border-[var(--border)] rounded-lg shadow-lg z-50">
            <div className="px-3 py-2 border-b border-[var(--border)]">
              <p className="text-sm font-medium">{user.name}</p>
              <p className="text-xs text-[var(--fg-muted)]">{user.email}</p>
            </div>

            <button
              onClick={() => {
                setIsOpen(false);
                navigate("/profile");
              }}
              className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 hover:bg-[var(--border)]/50"
            >
              <Settings className="w-4 h-4" />
              Settings
            </button>

            <button
              onClick={() => {
                setIsOpen(false);
                logout();
              }}
              className="w-full px-3 py-2 text-left text-sm flex items-center gap-2 text-[var(--danger)] hover:bg-[var(--danger)]/10"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </>
      )}
    </div>
  );
}
