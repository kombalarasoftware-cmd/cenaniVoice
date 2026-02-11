/**
 * Centralized API client for VoiceAI Platform.
 * Uses NEXT_PUBLIC_API_URL environment variable with fallback to localhost.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const API_V1 = `${API_BASE_URL}/api/v1`;

/**
 * Get the auth token from localStorage
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

/**
 * Build headers with optional auth token
 */
function buildHeaders(options?: { contentType?: string; includeAuth?: boolean }): HeadersInit {
  const headers: Record<string, string> = {};
  
  const contentType = options?.contentType;
  if (contentType !== 'multipart') {
    headers['Content-Type'] = contentType || 'application/json';
  }

  const includeAuth = options?.includeAuth ?? true;
  if (includeAuth) {
    const token = getAuthToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
  }

  return headers;
}

/**
 * Generic API fetch wrapper with error handling
 */
export async function apiFetch<T = unknown>(
  path: string,
  options?: RequestInit & { includeAuth?: boolean }
): Promise<T> {
  const { includeAuth, ...fetchOptions } = options || {};
  const url = path.startsWith('http') ? path : `${API_V1}${path}`;

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      ...buildHeaders({ includeAuth }),
      ...(fetchOptions.headers as Record<string, string> || {}),
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `API Error: ${response.status}`);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

/**
 * Convenience methods
 */
export const api = {
  get: <T = unknown>(path: string, options?: { includeAuth?: boolean }) =>
    apiFetch<T>(path, { method: 'GET', ...options }),

  post: <T = unknown>(path: string, body?: unknown, options?: { includeAuth?: boolean }) =>
    apiFetch<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  put: <T = unknown>(path: string, body?: unknown, options?: { includeAuth?: boolean }) =>
    apiFetch<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  patch: <T = unknown>(path: string, body?: unknown, options?: { includeAuth?: boolean }) =>
    apiFetch<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
      ...options,
    }),

  delete: <T = unknown>(path: string, options?: { includeAuth?: boolean }) =>
    apiFetch<T>(path, { method: 'DELETE', ...options }),

  /**
   * Upload file (multipart/form-data)
   */
  upload: <T = unknown>(path: string, formData: FormData, options?: { includeAuth?: boolean }) => {
    const url = path.startsWith('http') ? path : `${API_V1}${path}`;
    const headers: Record<string, string> = {};
    const token = getAuthToken();
    if (token && (options?.includeAuth ?? true)) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    return fetch(url, {
      method: 'POST',
      body: formData,
      headers,
    }).then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `Upload Error: ${res.status}`);
      }
      return res.json() as Promise<T>;
    });
  },

  /**
   * Create EventSource for SSE streams
   */
  eventSourceUrl: (path: string): string => {
    return path.startsWith('http') ? path : `${API_V1}${path}`;
  },
};

export default api;
