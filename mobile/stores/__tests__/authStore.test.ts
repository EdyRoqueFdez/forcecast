import { useAuthStore } from '../authStore';

// Mock the auth API
jest.mock('../../api/auth', () => ({
  login: jest.fn(),
  register: jest.fn(),
  logout: jest.fn(),
  getCurrentUser: jest.fn(),
  isAuthenticated: jest.fn(),
}));

describe('Auth Store', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      isAuthenticated: false,
      user: null,
      isLoading: false,
      error: null,
    });
  });

  describe('login', () => {
    it('should set loading state', async () => {
      const { login } = useAuthStore.getState();
      
      // Start login (will fail due to mocked API)
      const loginPromise = login('test@test.com', 'password');
      
      // Check loading state
      expect(useAuthStore.getState().isLoading).toBe(true);
      
      // Wait for completion
      await loginPromise.catch(() => {});
    });

    it('should set error on failure', async () => {
      const { login } = useAuthStore.getState();
      
      await login('test@test.com', 'wrong-password').catch(() => {});
      
      expect(useAuthStore.getState().error).toBeTruthy();
    });
  });

  describe('logout', () => {
    it('should clear state', async () => {
      // Set initial state
      useAuthStore.setState({
        isAuthenticated: true,
        user: { id: '1', email: 'test@test.com', name: 'Test' },
      });

      const { logout } = useAuthStore.getState();
      await logout();

      expect(useAuthStore.getState().isAuthenticated).toBe(false);
      expect(useAuthStore.getState().user).toBeNull();
    });
  });

  describe('clearError', () => {
    it('should clear error state', () => {
      useAuthStore.setState({ error: 'Some error' });
      
      const { clearError } = useAuthStore.getState();
      clearError();
      
      expect(useAuthStore.getState().error).toBeNull();
    });
  });
});
