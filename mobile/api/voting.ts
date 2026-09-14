import { apiClient } from './client';
import { VoteRequest, VoteResponse, RankingsResponse, Ranking, UserVotesResponse, ApiModel } from './types';

// === Voting API ===

export async function createVote(data: VoteRequest): Promise<VoteResponse> {
  const payload = {
    ...data,
    target_type: data.target_type ?? 'model',
    model_slug: data.model_slug,
    category_slug: data.category_slug,
    idempotency_key: data.idempotency_key ?? `mobile-${Date.now()}`,
  };
  return apiClient.post<VoteResponse>('/api/v1/votes', payload);
}

export async function getRankings(category: string): Promise<RankingsResponse> {
  const response = await apiClient.get<{ data?: Array<Record<string, unknown>>; meta?: { total?: number } }>(`/api/v1/rankings/models?category=${encodeURIComponent(category)}&min_votes=1`);
  const rankings: Ranking[] = (response.data ?? []).map((item, index) => {
    const elo = Number(item.weighted_score ?? 1500);
    const model: ApiModel = {
      slug: String(item.slug ?? item.model_id),
      display_name: String(item.display_name ?? item.slug ?? item.model_id),
      provider: String(item.provider_id ?? 'Unknown'),
      categories: [category],
      elo_rating: elo,
    };
    return {
      rank: index + 1,
      model: {
        slug: model.slug!, name: model.display_name!, provider: String(model.provider),
        context_size: 0, price_per_million: 0, elo_rating: elo,
        tier: elo >= 1800 ? 'elite' : elo >= 1600 ? 'strong' : elo >= 1400 ? 'average' : 'emerging',
        categories: [category], modalities: [], created_at: new Date(0).toISOString(),
      },
      elo_rating: elo,
      elo_delta_7d: Number(item.tendency_pct ?? 0),
      votes_count: Number(item.raw_votes ?? item.sample_size ?? 0),
    };
  });
  return { rankings, category, total: response.meta?.total ?? rankings.length };
}

export async function getUserVotes(params?: {
  limit?: number;
  offset?: number;
}): Promise<VoteResponse[]> {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set('limit', params.limit.toString());
  if (params?.offset) searchParams.set('offset', params.offset.toString());

  const query = searchParams.toString();
  const response = await apiClient.get<UserVotesResponse>(`/api/v1/users/me/votes${query ? `?${query}` : ''}`);
  return response.votes.map((vote) => ({ ...vote, action: vote.action ?? 'cast' }));
}
