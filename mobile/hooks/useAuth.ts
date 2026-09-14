import { useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';

export function useAuth() {
  const { isAuthenticated, user, isLoading, error, login, register, logout, checkAuth, clearError } =
    useAuthStore();

  useEffect(() => {
    checkAuth();
  }, []);

  return {
    isAuthenticated,
    user,
    isLoading,
    error,
    login,
    register,
    logout,
    checkAuth,
    clearError,
  };
}
