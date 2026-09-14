import { create } from 'zustand';

type Theme = 'dark' | 'light' | 'jedi-dark' | 'jedi-light';
type Language = 'en' | 'es';

interface UiState {
  theme: Theme;
  language: Language;
  isLoading: boolean;
  setTheme: (theme: Theme) => void;
  setLanguage: (language: Language) => void;
  setLoading: (isLoading: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  theme: 'dark',
  language: 'en',
  isLoading: false,
  setTheme: (theme) => set({ theme }),
  setLanguage: (language) => set({ language }),
  setLoading: (isLoading) => set({ isLoading }),
}));
