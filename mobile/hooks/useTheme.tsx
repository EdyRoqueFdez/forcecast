import React, { createContext, useContext, useEffect, useState } from 'react';
import { Platform, useColorScheme } from 'react-native';
import { ThemeColors, ThemeMode, ThemeAccent, getTheme } from '../lib/themeVariants';

// Safe AsyncStorage import for web SSR
let AsyncStorage: any = null;
if (Platform.OS !== 'web') {
  AsyncStorage = require('@react-native-async-storage/async-storage').default;
}

const THEME_MODE_KEY = 'forcecast_theme_mode';
const THEME_ACCENT_KEY = 'forcecast_theme_accent';

interface ThemeContextType {
  colors: ThemeColors;
  mode: ThemeMode;
  accent: ThemeAccent;
  setMode: (mode: ThemeMode) => void;
  setAccent: (accent: ThemeAccent) => void;
  toggleMode: () => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const systemColorScheme = useColorScheme();
  const [mode, setModeState] = useState<ThemeMode>(systemColorScheme === 'dark' ? 'dark' : 'light');
  const [accent, setAccentState] = useState<ThemeAccent>('emerald');
  const [isLoaded, setIsLoaded] = useState(false);

  // Load saved theme on mount
  useEffect(() => {
    loadTheme();
  }, []);

  // Save theme when it changes
  useEffect(() => {
    if (isLoaded) {
      saveTheme();
    }
  }, [mode, accent, isLoaded]);

  const loadTheme = async () => {
    if (!AsyncStorage) {
      setIsLoaded(true);
      return;
    }
    try {
      const [savedMode, savedAccent] = await Promise.all([
        AsyncStorage.getItem(THEME_MODE_KEY),
        AsyncStorage.getItem(THEME_ACCENT_KEY),
      ]);

      if (savedMode) setModeState(savedMode as ThemeMode);
      if (savedAccent) setAccentState(savedAccent as ThemeAccent);
    } catch (error) {
      console.error('Failed to load theme:', error);
    } finally {
      setIsLoaded(true);
    }
  };

  const saveTheme = async () => {
    if (!AsyncStorage) return;
    try {
      await Promise.all([
        AsyncStorage.setItem(THEME_MODE_KEY, mode),
        AsyncStorage.setItem(THEME_ACCENT_KEY, accent),
      ]);
    } catch (error) {
      console.error('Failed to save theme:', error);
    }
  };

  const setMode = (newMode: ThemeMode) => setModeState(newMode);
  const setAccent = (newAccent: ThemeAccent) => setAccentState(newAccent);
  const toggleMode = () => setModeState(mode === 'dark' ? 'light' : 'dark');

  const colors = getTheme(mode, accent);

  return (
    <ThemeContext.Provider value={{ colors, mode, accent, setMode, setAccent, toggleMode }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}
