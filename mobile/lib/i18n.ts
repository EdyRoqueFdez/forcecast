import { Platform } from 'react-native';

// Safe AsyncStorage import for web SSR
let AsyncStorage: any = null;
if (Platform.OS !== 'web') {
  AsyncStorage = require('@react-native-async-storage/async-storage').default;
}

export type Language = 'en' | 'es';

const LANGUAGE_KEY = 'forcecast_language';

// === Translations ===
const translations = {
  en: {
    // Tab names
    tabVote: 'Vote',
    tabRankings: 'Rankings',
    tabModels: 'Models',
    tabProfile: 'Profile',

    // Vote screen
    voteTitle: 'Compare AI Models',
    voteSubtitle: 'Choose the better model',
    voteSkip: 'Skip',
    voteDontKnow: "Don't Know",
    voteProgress: '{count} / 50',

    // Rankings screen
    rankingsTitle: 'Leaderboard',
    rankingsEmpty: 'No votes in this category yet',
    rankingsElo: 'ELO',
    rankingsDelta: '{delta} this week',

    // Models screen
    modelsTitle: 'Browse Models',
    modelsSearch: 'Search models...',
    modelsEmpty: 'No models match your search',
    modelsCompare: 'Compare',

    // Profile screen
    profileTitle: 'Profile',
    profileStats: 'Your Stats',
    profileVotes: 'Votes Cast',
    profileCategories: 'Categories',
    profileStreak: 'Day Streak',
    profileRecent: 'Recent Votes',
    profileSignOut: 'Sign Out',
    profileEdit: 'Edit Profile',

    // Auth screens
    loginTitle: 'Welcome Back',
    loginSubtitle: 'Sign in to continue',
    loginEmail: 'Email',
    loginPassword: 'Password',
    loginButton: 'Sign In',
    loginGithub: 'Sign in with GitHub',
    loginGoogle: 'Sign in with Google',
    loginNoAccount: "Don't have an account?",
    loginSignUp: 'Sign Up',

    registerTitle: 'Create Account',
    registerSubtitle: 'Join the community',
    registerName: 'Name',
    registerEmail: 'Email',
    registerPassword: 'Password',
    registerButton: 'Sign Up',
    registerGithub: 'Sign up with GitHub',
    registerGoogle: 'Sign up with Google',
    registerHasAccount: 'Already have an account?',
    registerSignIn: 'Sign In',

    // Common
    loading: 'Loading...',
    error: 'Error',
    retry: 'Retry',
    cancel: 'Cancel',
    save: 'Save',
    delete: 'Delete',
    confirm: 'Confirm',
    back: 'Back',
    next: 'Next',
  },
  es: {
    // Tab names
    tabVote: 'Votar',
    tabRankings: 'Rankings',
    tabModels: 'Modelos',
    tabProfile: 'Perfil',

    // Vote screen
    voteTitle: 'Comparar Modelos de IA',
    voteSubtitle: 'Elige el mejor modelo',
    voteSkip: 'Saltar',
    voteDontKnow: 'No Sé',
    voteProgress: '{count} / 50',

    // Rankings screen
    rankingsTitle: 'Clasificación',
    rankingsEmpty: 'No hay votos en esta categoría aún',
    rankingsElo: 'ELO',
    rankingsDelta: '{delta} esta semana',

    // Models screen
    modelsTitle: 'Explorar Modelos',
    modelsSearch: 'Buscar modelos...',
    modelsEmpty: 'Ningún modelo coincide con tu búsqueda',
    modelsCompare: 'Comparar',

    // Profile screen
    profileTitle: 'Perfil',
    profileStats: 'Tus Estadísticas',
    profileVotes: 'Votos Realizados',
    profileCategories: 'Categorías',
    profileStreak: 'Racha de Días',
    profileRecent: 'Votos Recientes',
    profileSignOut: 'Cerrar Sesión',
    profileEdit: 'Editar Perfil',

    // Auth screens
    loginTitle: 'Bienvenido',
    loginSubtitle: 'Inicia sesión para continuar',
    loginEmail: 'Correo electrónico',
    loginPassword: 'Contraseña',
    loginButton: 'Iniciar Sesión',
    loginGithub: 'Iniciar sesión con GitHub',
    loginGoogle: 'Iniciar sesión con Google',
    loginNoAccount: '¿No tienes una cuenta?',
    loginSignUp: 'Regístrate',

    registerTitle: 'Crear Cuenta',
    registerSubtitle: 'Únete a la comunidad',
    registerName: 'Nombre',
    registerEmail: 'Correo electrónico',
    registerPassword: 'Contraseña',
    registerButton: 'Regístrate',
    registerGithub: 'Regístrate con GitHub',
    registerGoogle: 'Regístrate con Google',
    registerHasAccount: '¿Ya tienes una cuenta?',
    registerSignIn: 'Inicia Sesión',

    // Common
    loading: 'Cargando...',
    error: 'Error',
    retry: 'Reintentar',
    cancel: 'Cancelar',
    save: 'Guardar',
    delete: 'Eliminar',
    confirm: 'Confirmar',
    back: 'Atrás',
    next: 'Siguiente',
  },
} as const;

// === i18n Class ===
class I18n {
  private currentLanguage: Language = 'en';
  private listeners: Array<(lang: Language) => void> = [];

  constructor() {
    this.loadLanguage();
  }

  private async loadLanguage() {
    if (!AsyncStorage) return;
    try {
      const saved = await AsyncStorage.getItem(LANGUAGE_KEY);
      if (saved && (saved === 'en' || saved === 'es')) {
        this.currentLanguage = saved;
      }
    } catch (error) {
      console.error('Failed to load language:', error);
    }
  }

  async setLanguage(lang: Language) {
    this.currentLanguage = lang;
    if (AsyncStorage) {
      try {
        await AsyncStorage.setItem(LANGUAGE_KEY, lang);
      } catch (error) {
        console.error('Failed to save language:', error);
      }
    }
    this.notifyListeners();
  }

  getLanguage(): Language {
    return this.currentLanguage;
  }

  t(key: keyof typeof translations.en, params?: Record<string, string | number>): string {
    let text = translations[this.currentLanguage][key] || translations.en[key];
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, String(v));
      });
    }
    return text;
  }

  onLanguageChange(listener: (lang: Language) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  private notifyListeners() {
    this.listeners.forEach((listener) => listener(this.currentLanguage));
  }
}

export const i18n = new I18n();
