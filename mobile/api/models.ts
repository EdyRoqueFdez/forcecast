import { apiClient } from './client';
import { ApiModel, Model, ModelListResponse } from './types';

function normalizeModel(model: ApiModel): Model {
  const provider = typeof model.provider === 'string' ? model.provider : model.provider?.name || model.provider?.slug || 'Unknown';
  const contextSize = model.context_size ?? model.context_window ?? 0;
  const price = Number(model.price_per_million ?? model.input_price_per_mtok ?? 0);
  const elo = model.elo_rating ?? 1500;
  const tier = model.tier ?? (elo >= 1800 ? 'elite' : elo >= 1600 ? 'strong' : elo >= 1400 ? 'average' : 'emerging');

  return {
    slug: model.slug,
    name: model.name ?? model.display_name ?? model.slug,
    provider,
    avatar: model.avatar ?? model.icon,
    context_size: contextSize,
    price_per_million: Number.isFinite(price) ? price : 0,
    elo_rating: elo,
    tier,
    categories: model.categories ?? [],
    modalities: model.modalities ?? model.modality ?? [],
    description: model.description,
    created_at: model.created_at ?? new Date(0).toISOString(),
  };
}

// === Models API ===

export async function getModels(params?: {
  category?: string;
  provider?: string;
  search?: string;
  page?: number;
  per_page?: number;
}): Promise<ModelListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set('category', params.category);
  if (params?.provider) searchParams.set('provider', params.provider);
  if (params?.search) searchParams.set('search', params.search);
  if (params?.page) searchParams.set('page', params.page.toString());
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString());

  const query = searchParams.toString();
  const response = await apiClient.get<{ data?: ApiModel[]; models?: ApiModel[]; total?: number }>(`/api/v1/models${query ? `?${query}` : ''}`);
  const data = response.data ?? response.models ?? [];
  return {
    models: data.map(normalizeModel),
    total: response.total ?? data.length,
    page: params?.page ?? 1,
    per_page: params?.per_page ?? data.length,
  };
}

export async function getModel(slug: string): Promise<Model> {
  const response = await apiClient.get<ApiModel>(`/api/v1/models/${slug}`);
  return normalizeModel(response);
}

export async function compareModels(slugs: string[]): Promise<Model[]> {
  const searchParams = new URLSearchParams();
  slugs.forEach((slug) => searchParams.append('slugs', slug));
  return apiClient.get<Model[]>(`/api/v1/models/compare?${searchParams.toString()}`);
}
