import { useEffect, useState, useCallback } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Globe, Search, Github, LogIn } from "lucide-react";
import { getBrowserLocale } from "./lib/utils";
import { api } from "./api";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import type { Model, FilterState, MetaResponse, CompareResponse, Locale } from "./types";
import { LocaleSelector } from "./components/LocaleSelector";
import { Filters } from "./components/Filters";
import { ModelCard } from "./components/ModelCard";
import { CompareBar } from "./components/CompareBar";
import { CompareModal } from "./components/CompareModal";
import { Toast } from "./components/Toast";
import { AuthModal } from "./components/auth/AuthModal";
import { UserMenu } from "./components/auth/UserMenu";
import { AuthCallback } from "./components/auth/AuthCallback";

function AppContent() {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  console.log("Forcecast App renderizado"); // DEBUG

  // State
  const [models, setModels] = useState<Model[]>([]);
  const [meta, setMeta] = useState<MetaResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    search: "",
    category: "",
    provider: "",
    modality: "",
    sort: "release_date",
    order: "desc",
  });
  const [selectedSlugs, setSelectedSlugs] = useState<Set<string>>(new Set());
  const [compareData, setCompareData] = useState<CompareResponse | null>(null);
  const [showCompare, setShowCompare] = useState(false);
  const [locale, setLocale] = useState<Locale>(() => getBrowserLocale() as Locale);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Fetch meta on mount
  useEffect(() => {
    api.getMeta()
      .then(setMeta)
      .catch(() => setError("Failed to load categories/providers"));
  }, []);

  // Fetch models when filters change
  const fetchModels = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getModels(filters, 100, 0);
      setModels(res.data);
    } catch (e) {
      setError("Failed to load models");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // Handlers
  const handleFilterChange = (newFilters: Partial<FilterState>) => {
    setFilters(prev => ({ ...prev, ...newFilters }));
  };

  const toggleSelect = (slug: string) => {
    setSelectedSlugs(prev => {
      const next = new Set(prev);
      if (next.has(slug)) {
        next.delete(slug);
      } else {
        if (next.size >= 4) {
          showToast("Maximum 4 models for comparison", "error");
          return prev;
        }
        next.add(slug);
      }
      return next;
    });
  };

  const clearCompare = () => {
    setSelectedSlugs(new Set());
  };

  const openCompare = async () => {
    if (selectedSlugs.size < 2) return;
    try {
      const data = await api.compareModels(Array.from(selectedSlugs));
      setCompareData(data);
      setShowCompare(true);
    } catch (e) {
      showToast("Failed to load comparison", "error");
    }
  };

  const showToast = (message: string, type: "success" | "error") => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const filteredModels = models; // Already filtered by API

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)]">
      <header className="border-b border-[var(--border)] bg-[var(--bg-elevated)] sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 py-4 md:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[var(--accent)] flex items-center justify-center">
                <Globe className="w-6 h-6 text-[var(--bg)]" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-[var(--fg)] to-[var(--accent)] bg-clip-text text-transparent">
                  Forcecast
                </h1>
                <p className="text-sm text-[var(--fg-muted)]">Compare AI models by task, capability & cost</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <LocaleSelector currentLocale={locale} onChange={setLocale} />

              {authLoading ? (
                <div className="w-20 h-9 bg-[var(--border)] rounded-lg animate-pulse" />
              ) : isAuthenticated ? (
                <UserMenu />
              ) : (
                <button
                  onClick={() => setShowAuthModal(true)}
                  className="btn btn-primary gap-2"
                >
                  <LogIn className="w-4 h-4" />
                  Sign In
                </button>
              )}

              <a
                href="https://github.com/forcecast"
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary gap-2"
              >
                <Github className="w-4 h-4" />
                GitHub
              </a>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-6 md:px-6 lg:px-8">
        {error && (
          <div className="mb-6 p-4 rounded-lg bg-[var(--danger)]/10 border border-[var(--danger)]/30 text-[var(--danger)]">
            {error}
          </div>
        )}

        <section aria-labelledby="search-title">
          <div className="flex items-center justify-between mb-4">
            <h2 id="search-title" className="text-xl font-bold">Find Models</h2>
            <span className="text-sm text-[var(--fg-muted)]">{models.length} models</span>
          </div>

          <Filters
            filters={filters}
            onChange={handleFilterChange}
            categories={meta?.categories || []}
            providers={meta?.providers || []}
            modalities={meta?.modalities || []}
            locale={locale}
          />

          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {[...Array(8)].map((_, i) => (
                <div key={i} className="model-card animate-pulse">
                  <div className="h-8 bg-[var(--border)] rounded w-3/4 mb-2"></div>
                  <div className="h-4 bg-[var(--border)] rounded w-1/2 mb-4"></div>
                  <div className="flex gap-2 mb-4">
                    <div className="h-5 bg-[var(--border)] rounded-full w-20"></div>
                    <div className="h-5 bg-[var(--border)] rounded-full w-24"></div>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <div className="h-8 bg-[var(--border)] rounded"></div>
                    <div className="h-8 bg-[var(--border)] rounded"></div>
                    <div className="h-8 bg-[var(--border)] rounded"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : filteredModels.length === 0 ? (
            <div className="text-center py-16 text-[var(--fg-muted)]">
              <Search className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No models match your filters</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4" role="list">
              {filteredModels.map(model => (
                <ModelCard
                  key={model.slug}
                  model={model}
                  isSelected={selectedSlugs.has(model.slug)}
                  onClick={() => toggleSelect(model.slug)}
                  locale={locale}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      <footer className="border-t border-[var(--border)] py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center text-sm text-[var(--fg-muted)]">
          <p>Forcecast MVP — <a href="https://github.com/forcecast" target="_blank" rel="noopener" className="text-[var(--accent)] hover:underline">GitHub</a> · <a href="#" className="text-[var(--accent)] hover:underline">Give Feedback</a></p>
          <p className="mt-1">Prices are reference only (OpenRouter). Not a marketplace.</p>
        </div>
      </footer>

      <CompareBar
        count={selectedSlugs.size}
        onClear={clearCompare}
        onCompare={openCompare}
      />

      <CompareModal
        isOpen={showCompare}
        onClose={() => setShowCompare(false)}
        data={compareData}
        locale={locale}
      />

      <AuthModal
        isOpen={showAuthModal}
        onClose={() => setShowAuthModal(false)}
      />

      <Toast
        message={toast?.message ?? ""}
        type={toast?.type ?? "success"}
        onClose={() => setToast(null)}
        visible={!!toast}
      />
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/auth/callback" element={<AuthCallback />} />
          <Route path="/" element={<AppContent />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
