import { create } from 'zustand';
import { api } from '@/api/client';
import { onUnauthorized } from '@/api/httpClient';
import { queryClient } from '@/api/queryClient';
import { ApiError, type AuthUser, type RegisterParams } from '@/api/types';
import { useAnalysis } from '@/store/analysisStore';

type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

interface AuthState {
  user: AuthUser | null;
  status: AuthStatus;
  bootstrap: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  register: (params: RegisterParams) => Promise<void>;
  logout: () => Promise<void>;
}

/** Wipe everything tied to the previous account (cached history, the open analysis). */
function resetAccountData() {
  queryClient.removeQueries({ queryKey: ['history'] });
  useAnalysis.getState().reset();
}

export const useAuth = create<AuthState>()((set) => ({
  user: null,
  status: 'loading',

  async bootstrap() {
    try {
      set({ user: await api.me(), status: 'authenticated' });
    } catch (err) {
      // 401 = not logged in. Network errors also leave the user anonymous (the API status shows offline).
      if (!(err instanceof ApiError)) console.warn(err);
      set({ user: null, status: 'anonymous' });
    }
  },

  async login(email, password) {
    const user = await api.login(email, password);
    resetAccountData();
    set({ user, status: 'authenticated' });
  },

  async register(params) {
    const user = await api.register(params);
    resetAccountData();
    set({ user, status: 'authenticated' });
  },

  async logout() {
    try {
      await api.logout();
    } finally {
      resetAccountData();
      set({ user: null, status: 'anonymous' });
    }
  },
}));

// A protected request returned 401: the session expired or was revoked.
onUnauthorized(() => {
  if (useAuth.getState().status === 'authenticated') {
    resetAccountData();
    useAuth.setState({ user: null, status: 'anonymous' });
  }
});

/** Only allow same-site relative paths as post-login redirects (prevents open redirects). */
export function safeNext(next: string | null | undefined, fallback = '/analyze'): string {
  return next && next.startsWith('/') && !next.startsWith('//') ? next : fallback;
}
