import { Platform } from 'react-native';

// Safe Haptics import for web SSR
let Haptics: any = null;
if (Platform.OS !== 'web') {
  Haptics = require('expo-haptics');
}

// === Error Handler ===

interface AppError {
  code: string;
  message: string;
  details?: unknown;
}

class ErrorHandler {
  private listeners: Array<(error: AppError) => void> = [];

  onError(listener: (error: AppError) => void) {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter((l) => l !== listener);
    };
  }

  handle(error: unknown): AppError {
    const appError = this.normalizeError(error);
    this.notifyListeners(appError);
    this.triggerHaptic();
    return appError;
  }

  private normalizeError(error: unknown): AppError {
    if (error instanceof Error) {
      return {
        code: 'UNKNOWN_ERROR',
        message: error.message,
        details: error,
      };
    }

    if (typeof error === 'object' && error !== null && 'detail' in error) {
      const apiError = error as { detail: string; status_code?: number };
      return {
        code: `API_ERROR_${apiError.status_code || 500}`,
        message: apiError.detail,
        details: error,
      };
    }

    return {
      code: 'UNKNOWN_ERROR',
      message: 'An unexpected error occurred',
      details: error,
    };
  }

  private notifyListeners(error: AppError) {
    this.listeners.forEach((listener) => listener(error));
  }

  private triggerHaptic() {
    if (Haptics) {
      Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error).catch(() => {});
    }
  }
}

export const errorHandler = new ErrorHandler();

// === Network Error Recovery ===

export async function withRetry<T>(
  fn: () => Promise<T>,
  maxRetries = 3,
  delay = 1000
): Promise<T> {
  let lastError: unknown;

  for (let i = 0; i < maxRetries; i++) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      if (i < maxRetries - 1) {
        await new Promise((resolve) => setTimeout(resolve, delay * (i + 1)));
      }
    }
  }

  throw lastError;
}
