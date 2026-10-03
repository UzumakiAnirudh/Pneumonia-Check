import type { ApiClient } from './client';
import { ApiError, type ApiErrorDetail } from './types';

async function parseError(res: Response): Promise<ApiError> {
  let detail: ApiErrorDetail = {
    code: `http_${res.status}`,
    message: res.statusText || 'Request failed',
  };
  try {
    const body = await res.json();
    if (body?.detail && typeof body.detail === 'object' && !Array.isArray(body.detail)) {
      detail = { ...detail, ...body.detail };
    } else if (typeof body?.detail === 'string') {
      detail = { ...detail, message: body.detail };
    } else if (Array.isArray(body?.detail)) {
      detail = {
        code: 'invalid_request',
        message: body.detail.map((d: { msg: string }) => d.msg).join('; '),
      };
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, detail);
}

type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

/** Notified when an authenticated request comes back 401 (session expired / logged out elsewhere). */
export function onUnauthorized(fn: UnauthorizedListener): () => void {
  unauthorizedListeners.add(fn);
  return () => unauthorizedListeners.delete(fn);
}

export function createHttpClient(baseUrl: string): ApiClient {
  const url = (path: string) => `${baseUrl}${path}`;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let res: Response;
    try {
      // credentials: send the httpOnly session cookie (also when the API is on another origin).
      res = await fetch(url(path), { credentials: 'include', ...init });
    } catch {
      throw new ApiError(0, {
        code: 'network',
        message: 'Cannot reach the analysis server. Check that the backend is running.',
      });
    }
    if (!res.ok) {
      const err = await parseError(res);
      if (res.status === 401 && !path.startsWith('/api/auth/'))
        unauthorizedListeners.forEach((fn) => fn());
      throw err;
    }
    if (res.status === 204) return undefined as T;
    // A static host without the API (e.g. Vercel with no /api rewrite) answers with index.html.
    if (!(res.headers.get('content-type') ?? '').includes('application/json')) {
      throw new ApiError(0, {
        code: 'network',
        message: 'The analysis server is not connected. Deploy the backend and point /api at it.',
      });
    }
    return (await res.json()) as T;
  }

  const json = (body: unknown): RequestInit => ({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  return {
    me: () => request('/api/auth/me'),
    login: (email, password) => request('/api/auth/login', json({ email, password })),
    register: (params) => request('/api/auth/register', json(params)),
    logout: () => request('/api/auth/logout', { method: 'POST' }),
    health: () => request('/api/health'),
    validate(file) {
      const body = new FormData();
      body.append('file', file);
      return request('/api/validate', { method: 'POST', body });
    },
    predict({ file, model, threshold, saveHistory, sourceName }) {
      const body = new FormData();
      body.append('file', file);
      body.append('model', model);
      body.append('threshold', String(threshold));
      body.append('save_history', String(saveHistory));
      if (sourceName) body.append('source_name', sourceName);
      return request('/api/predict', { method: 'POST', body });
    },
    metrics: () => request('/api/metrics'),
    samples: () => request('/api/samples'),
    async sampleFile(sample) {
      const res = await fetch(url(sample.url), { credentials: 'include' });
      if (!res.ok) throw await parseError(res);
      const blob = await res.blob();
      const name = sample.url.split('/').pop() ?? `${sample.id}.png`;
      return new File([blob], name, { type: blob.type || 'image/jpeg' });
    },
    history: () => request('/api/history'),
    historyItem: (id) => request(`/api/history/${encodeURIComponent(id)}`),
    deleteHistoryItem: (id) =>
      request(`/api/history/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    clearHistory: () => request('/api/history', { method: 'DELETE' }),
  };
}
