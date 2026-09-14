// Theme Variants for Forcecast Mobile App

import { colors } from './theme';

export type ThemeMode = 'dark' | 'light';
export type ThemeAccent = 'emerald' | 'jedi';

export interface ThemeColors {
  // Background
  background: string;
  backgroundSecondary: string;
  backgroundTertiary: string;

  // Surface
  surface: string;
  surfaceSecondary: string;
  surfaceHover: string;

  // Text
  text: string;
  textSecondary: string;
  textTertiary: string;
  textInverse: string;

  // Border
  border: string;
  borderSecondary: string;

  // Primary (accent)
  primary: string;
  primaryHover: string;
  primaryText: string;

  // Status
  success: string;
  warning: string;
  error: string;
  info: string;

  // Tab bar
  tabBar: string;
  tabBarBorder: string;
  tabActive: string;
  tabInactive: string;
}

// === Dark Theme ===
const darkTheme: ThemeColors = {
  background: '#080b10',
  backgroundSecondary: '#10151d',
  backgroundTertiary: '#1a232e',

  surface: '#141b24',
  surfaceSecondary: '#1a232e',
  surfaceHover: '#202c38',

  text: '#f3f6f4',
  textSecondary: '#b2c0c1',
  textTertiary: '#8d9aa5',
  textInverse: '#080b10',

  border: '#273340',
  borderSecondary: '#344352',

  primary: '#00d4aa',
  primaryHover: '#00efc0',
  primaryText: '#080b10',

  success: colors.success,
  warning: colors.warning,
  error: colors.error,
  info: colors.info,

  tabBar: '#10151de8',
  tabBarBorder: '#273340',
  tabActive: '#00d4aa',
  tabInactive: '#8d9aa5',
};

// === Light Theme ===
const lightTheme: ThemeColors = {
  background: '#edf2f0',
  backgroundSecondary: '#f6faf8',
  backgroundTertiary: '#e7f1ed',

  surface: '#ffffff',
  surfaceSecondary: '#f2f7f5',
  surfaceHover: '#e7f1ed',

  text: '#14221e',
  textSecondary: '#536660',
  textTertiary: '#667771',
  textInverse: '#ffffff',

  border: '#d7e2dd',
  borderSecondary: '#c1d1ca',

  primary: '#008f76',
  primaryHover: '#007d68',
  primaryText: '#ffffff',

  success: colors.success,
  warning: colors.warning,
  error: colors.error,
  info: colors.info,

  tabBar: '#f6faf8f2',
  tabBarBorder: '#d7e2dd',
  tabActive: '#008f76',
  tabInactive: '#667771',
};

// === Jedi Dark Theme ===
const jediDarkTheme: ThemeColors = {
  ...darkTheme,
  primary: colors.jedi[500],
  primaryHover: colors.jedi[400],
  tabActive: colors.jedi[500],
};

// === Jedi Light Theme ===
const jediLightTheme: ThemeColors = {
  ...lightTheme,
  primary: colors.jedi[600],
  primaryHover: colors.jedi[500],
  tabActive: colors.jedi[600],
};

// === Theme Map ===
export const themes: Record<`${ThemeMode}-${ThemeAccent}`, ThemeColors> = {
  'dark-emerald': darkTheme,
  'dark-jedi': jediDarkTheme,
  'light-emerald': lightTheme,
  'light-jedi': jediLightTheme,
};

export function getTheme(mode: ThemeMode, accent: ThemeAccent): ThemeColors {
  return themes[`${mode}-${accent}`];
}
