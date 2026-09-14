import { apiClient } from './client';
import { MetaResponse, Category } from './types';

// === Meta API ===

export async function getMeta(): Promise<MetaResponse> {
  const response = await apiClient.get<MetaResponse & { categories?: Array<Category | string> }>('/api/v1/meta');
  return {
    ...response,
    categories: (response.categories ?? []).map((category) => typeof category === 'string'
      ? { id: category, slug: category, name: category }
      : category),
  };
}

export async function getCategories(): Promise<Category[]> {
  const meta = await getMeta();
  return meta.categories;
}
