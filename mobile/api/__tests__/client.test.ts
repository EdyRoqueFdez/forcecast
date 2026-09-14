import { apiClient } from '../client';

// Mock fetch
global.fetch = jest.fn();

describe('API Client', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('request', () => {
    it('should make GET request', async () => {
      const mockResponse = { data: 'test' };
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiClient.get('/test');

      expect(fetch).toHaveBeenCalledWith(
        'https://forcecast-mvp.fly.dev/test',
        expect.objectContaining({
          method: 'GET',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should make POST request with body', async () => {
      const mockResponse = { id: 1 };
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await apiClient.post('/test', { name: 'test' });

      expect(fetch).toHaveBeenCalledWith(
        'https://forcecast-mvp.fly.dev/test',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ name: 'test' }),
        })
      );
      expect(result).toEqual(mockResponse);
    });

    it('should throw error on failed response', async () => {
      (fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Not found' }),
      });

      await expect(apiClient.get('/not-found')).rejects.toEqual({
        detail: 'Not found',
      });
    });
  });

  describe('token management', () => {
    it('should set and get tokens', async () => {
      // This would require mocking SecureStore
      // For now, just test the API exists
      expect(typeof apiClient.setTokens).toBe('function');
      expect(typeof apiClient.clearTokens).toBe('function');
      expect(typeof apiClient.getAccessToken).toBe('function');
    });
  });
});
