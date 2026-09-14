import { useEffect } from 'react';
import { useModelsStore } from '../stores/modelsStore';

export function useModels() {
  const {
    models,
    selectedModel,
    isLoading,
    error,
    searchQuery,
    selectedProvider,
    selectedCategory,
    fetchModels,
    fetchModel,
    setSearchQuery,
    setSelectedProvider,
    setSelectedCategory,
    clearError,
  } = useModelsStore();

  useEffect(() => {
    fetchModels();
  }, []);

  return {
    models,
    selectedModel,
    isLoading,
    error,
    searchQuery,
    selectedProvider,
    selectedCategory,
    fetchModels,
    fetchModel,
    setSearchQuery,
    setSelectedProvider,
    setSelectedCategory,
    clearError,
  };
}
