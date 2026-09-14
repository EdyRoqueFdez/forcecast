import { apiClient } from './client';
import { AuthResponse, LoginRequest, RegisterRequest, User } from './types';

// === Auth API ===

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.postWithoutAuth<AuthResponse>('/auth/login', data);
  await apiClient.setTokens(response.access_token, response.refresh_token);
  return response;
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await apiClient.postWithoutAuth<AuthResponse>('/auth/register', data);
  await apiClient.setTokens(response.access_token, response.refresh_token);
  return response;
}

export async function logout(): Promise<void> {
  try {
    await apiClient.post('/auth/logout');
  } finally {
    await apiClient.clearTokens();
  }
}

export async function getCurrentUser(): Promise<User> {
  return apiClient.get<User>('/auth/me');
}

export async function updateProfile(data: Partial<User>): Promise<User> {
  return apiClient.patch<User>('/auth/me', data);
}

// === OAuth ===

export function getOAuthUrl(provider: 'github' | 'google'): string {
  return `https://forcecast-mvp.fly.dev/auth/${provider}`;
}

export async function handleOAuthCallback(
  provider: 'github' | 'google',
  code: string
): Promise<AuthResponse> {
  const response = await apiClient.postWithoutAuth<AuthResponse>(
    `/auth/${provider}/callback`,
    { code }
  );
  await apiClient.setTokens(response.access_token, response.refresh_token);
  return response;
}

// === Token Check ===

export async function isAuthenticated(): Promise<boolean> {
  const token = await apiClient.getAccessToken();
  return token !== null;
}
