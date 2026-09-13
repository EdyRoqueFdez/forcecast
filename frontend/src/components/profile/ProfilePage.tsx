import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../contexts/AuthContext";
import { Save, ArrowLeft } from "lucide-react";

interface Profile {
  id: string;
  email: string | null;
  display_name: string;
  avatar_url: string | null;
  role: string;
  reputation_score: number;
  email_verified: boolean;
  bio: string | null;
  preferred_locale: string;
  visibility_mode: string;
  created_at: string;
  updated_at: string;
}

const API_BASE = import.meta.env.VITE_API_BASE || "https://forcecast-mvp.fly.dev";

export function ProfilePage() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Editable fields
  const [displayName, setDisplayName] = useState("");
  const [bio, setBio] = useState("");
  const [preferredLocale, setPreferredLocale] = useState("en");
  const [visibilityMode, setVisibilityMode] = useState("pseudonym");

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate("/");
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchProfile();
    }
  }, [isAuthenticated]);

  const fetchProfile = async () => {
    try {
      const res = await fetch(`${API_BASE}/../auth/me`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to fetch profile");
      const data: Profile = await res.json();
      setProfile(data);
      setDisplayName(data.display_name);
      setBio(data.bio || "");
      setPreferredLocale(data.preferred_locale);
      setVisibilityMode(data.visibility_mode);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load profile");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      const res = await fetch(`${API_BASE}/../auth/me`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({
          display_name: displayName,
          bio: bio || null,
          preferred_locale: preferredLocale,
          visibility_mode: visibilityMode,
        }),
      });

      if (!res.ok) throw new Error("Failed to update profile");
      const data = await res.json();
      setProfile(data.profile);
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update profile");
    } finally {
      setSaving(false);
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
        <div className="w-12 h-12 border-4 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
        <p className="text-[var(--fg-muted)]">Profile not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--bg)]">
      <header className="border-b border-[var(--border)] bg-[var(--bg-elevated)]">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center gap-4">
          <button
            onClick={() => navigate("/")}
            className="p-2 rounded-lg hover:bg-[var(--border)]/50 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <h1 className="text-xl font-bold">Edit Profile</h1>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-[var(--danger)]/10 border border-[var(--danger)]/30 text-[var(--danger)]">
            {error}
          </div>
        )}

        {success && (
          <div className="mb-6 p-4 rounded-lg bg-green-500/10 border border-green-500/30 text-green-500">
            Profile updated successfully!
          </div>
        )}

        <div className="space-y-6">
          {/* Avatar */}
          <div className="flex items-center gap-4">
            {profile.avatar_url ? (
              <img
                src={profile.avatar_url}
                alt={profile.display_name}
                className="w-20 h-20 rounded-full"
              />
            ) : (
              <div className="w-20 h-20 rounded-full bg-[var(--accent)]/20 flex items-center justify-center text-2xl font-bold text-[var(--accent)]">
                {profile.display_name.charAt(0).toUpperCase()}
              </div>
            )}
            <div>
              <p className="font-medium">{profile.display_name}</p>
              <p className="text-sm text-[var(--fg-muted)]">{profile.email}</p>
            </div>
          </div>

          {/* Display Name */}
          <div>
            <label className="block text-sm font-medium mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--fg)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            />
          </div>

          {/* Bio */}
          <div>
            <label className="block text-sm font-medium mb-1">Bio</label>
            <textarea
              value={bio}
              onChange={(e) => setBio(e.target.value)}
              rows={3}
              maxLength={500}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--fg)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] resize-none"
              placeholder="Tell us about yourself..."
            />
            <p className="mt-1 text-xs text-[var(--fg-muted)]">{bio.length}/500</p>
          </div>

          {/* Locale */}
          <div>
            <label className="block text-sm font-medium mb-1">Preferred Language</label>
            <select
              value={preferredLocale}
              onChange={(e) => setPreferredLocale(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--fg)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            >
              <option value="en">English</option>
              <option value="es">Español</option>
              <option value="pt">Português</option>
              <option value="fr">Français</option>
              <option value="zh">中文</option>
            </select>
          </div>

          {/* Visibility */}
          <div>
            <label className="block text-sm font-medium mb-1">Profile Visibility</label>
            <select
              value={visibilityMode}
              onChange={(e) => setVisibilityMode(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-[var(--border)] bg-[var(--bg)] text-[var(--fg)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]"
            >
              <option value="pseudonym">Pseudonym (hide identity)</option>
              <option value="public">Public (show identity)</option>
            </select>
          </div>

          {/* Read-only info */}
          <div className="pt-4 border-t border-[var(--border)]">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-[var(--fg-muted)]">Role:</span>{" "}
                <span className="font-medium capitalize">{profile.role}</span>
              </div>
              <div>
                <span className="text-[var(--fg-muted)]">Reputation:</span>{" "}
                <span className="font-medium">{profile.reputation_score.toFixed(1)}</span>
              </div>
              <div>
                <span className="text-[var(--fg-muted)]">Email verified:</span>{" "}
                <span className={profile.email_verified ? "text-green-500" : "text-[var(--danger)"}>
                  {profile.email_verified ? "Yes" : "No"}
                </span>
              </div>
              <div>
                <span className="text-[var(--fg-muted)]">Member since:</span>{" "}
                <span className="font-medium">
                  {new Date(profile.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          </div>

          {/* Save button */}
          <button
            onClick={handleSave}
            disabled={saving}
            className="w-full py-3 px-4 rounded-lg bg-[var(--accent)] text-[var(--bg)] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity flex items-center justify-center gap-2"
          >
            <Save className="w-4 h-4" />
            {saving ? "Saving..." : "Save Changes"}
          </button>
        </div>
      </main>
    </div>
  );
}
