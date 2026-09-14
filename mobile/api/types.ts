// API Types for Forcecast Mobile App

// === Auth Types ===
export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  name: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatar?: string;
  role: 'user' | 'admin';
  created_at: string;
}

// === Model Types ===
export interface Model {
  slug: string;
  name: string;
  provider: string;
  avatar?: string;
  context_size: number;
  price_per_million: number;
  elo_rating: number;
  tier: 'elite' | 'strong' | 'average' | 'emerging';
  categories: string[];
  modalities: string[];
  description?: string;
  created_at: string;
}

export interface ApiModel {
  slug: string;
  display_name?: string;
  name?: string;
  provider?: { slug?: string; name?: string } | string;
  icon?: string;
  avatar?: string;
  context_window?: number;
  context_size?: number;
  input_price_per_mtok?: number | string | null;
  price_per_million?: number | string | null;
  elo_rating?: number;
  tier?: Model['tier'];
  categories?: string[];
  modality?: string[];
  modalities?: string[];
  description?: string;
  created_at?: string;
}

export interface ModelListResponse {
  models: Model[];
  total: number;
  page: number;
  per_page: number;
}

// === Voting Types ===
export interface VoteRequest {
  target_type?: 'model' | 'orchestrator';
  target_id?: string;
  category_id?: string;
  idempotency_key?: string;
  model_slug?: string;
  category_slug?: string;
  vote_type?: 'upvote' | 'downvote';
  comment?: string;
}

export interface VoteResponse {
  id: string;
  user_id?: string;
  event_id?: string;
  model_slug?: string;
  vote_type?: string;
  action?: string;
  target_type?: string;
  target_id?: string;
  category_id?: string;
  weight?: number | string;
  comment?: string | null;
  created_at?: string;
}

export interface Ranking {
  rank: number;
  model: Model;
  elo_rating: number;
  elo_delta_7d: number;
  votes_count: number;
}

export interface RankingsResponse {
  rankings: Ranking[];
  category: string;
  total: number;
}

export interface UserVotesResponse {
  votes: VoteResponse[];
  total: number;
  has_more: boolean;
  next_cursor: string | null;
}

// === Meta Types ===
export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
}

export interface MetaResponse {
  categories: Category[];
  providers: string[];
  modalities: string[];
}

// === API Error ===
export interface ApiError {
  detail: string;
  status_code: number;
}
