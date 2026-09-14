import { create } from 'zustand';
import * as modelsApi from '../api/models';
import { Model } from '../api/types';

interface ModelsState {
  models: Model[];
  selectedModel: Model | null;
  isLoading: boolean;
  error: string | null;
  searchQuery: string;
  selectedProvider: string | null;
  selectedCategory: string | null;
  fetchModels: () => Promise<void>;
  fetchModel: (slug: string) => Promise<void>;
  setSearchQuery: (query: string) => void;
  setSelectedProvider: (provider: string | null) => void;
  setSelectedCategory: (category: string | null) => void;
  clearError: () => void;
}

export const useModelsStore = create<ModelsState>((set) => ({
  models: [],
  selectedModel: null,
  isLoading: false,
  error: null,
  searchQuery: '',
  selectedProvider: null,
  selectedCategory: null,

  fetchModels: async () => {
    set({ isLoading: true, error: null });
    try {
      const response = await modelsApi.getModels({
        search: undefined,
        provider: undefined,
        category: undefined,
      });
      set({ models: response.models, isLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch models';
      set({ error: message, isLoading: false });
    }
  },

  fetchModel: async (slug: string) => {
    set({ isLoading: true, error: null });
    try {
      const model = await modelsApi.getModel(slug);
      set({ selectedModel: model, isLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch model';
      set({ error: message, isLoading: false });
    }
  },

  setSearchQuery: (query) => set({ searchQuery: query }),
  setSelectedProvider: (provider) => set({ selectedProvider: provider }),
  setSelectedCategory: (category) => set({ selectedCategory: category }),
  clearError: () => set({ error: null }),
}));
