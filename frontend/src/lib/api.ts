/**
 * Centralized API client for VoiceAI Platform.
 * Uses NEXT_PUBLIC_API_URL environment variable.
 * Default: empty string (relative URLs) — works with nginx proxy in production.
 * For local dev, set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '';
export const API_V1 = `${API_BASE_URL}/api/v1`;

/**
 * Get the auth token from localStorage
 */
function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('access_token');
}

/**
 * Get the refresh token from localStorage
 */
function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('refresh_token');
}

// Prevent multiple simultaneous refresh requests
let refreshPromise: Promise<boolean> | null = null;

/**
 * Attempt to refresh the access token using the stored refresh token.
 * Returns true if refresh succeeded, false otherwise.
 */
async function tryRefreshToken(): Promise<boolean> {
  // If already refreshing, wait for the existing request
  if (refreshPromise) return refreshPromise;

  const refreshToken = getRefreshToken();
  if (!refreshToken) return false;

  refreshPromise = (async () => {
    try {
      const response = await fetch(`${API_V1}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });

      if (!response.ok) {
        // Refresh token expired or revoked — force logout
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        document.cookie = 'access_token=; path=/; max-age=0';
        document.cookie = 'refresh_token=; path=/; max-age=0';
        return false;
      }

      const data = await response.json();
      localStorage.setItem('access_token', data.access_token);
      document.cookie = `access_token=${data.access_token}; path=/; max-age=${30 * 60}; SameSite=Lax; Secure`;
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
        document.cookie = `refresh_token=${data.refresh_token}; path=/; max-age=${7 * 24 * 60 * 60}; SameSite=Lax; Secure`;
      }
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();

  return refreshPromise;
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
 * Generic API fetch wrapper with error handling and automatic token refresh
 */
export async function apiFetch<T = unknown>(
  path: string,
  options?: RequestInit & { includeAuth?: boolean; _isRetry?: boolean }
): Promise<T> {
  const { includeAuth, _isRetry, ...fetchOptions } = options || {};
  const url = path.startsWith('http') ? path : `${API_V1}${path}`;

  const response = await fetch(url, {
    ...fetchOptions,
    headers: {
      ...buildHeaders({ includeAuth }),
      ...(fetchOptions.headers as Record<string, string> || {}),
    },
  });

  // On 401, try refreshing the token once (skip for auth endpoints)
  if (
    response.status === 401 &&
    !_isRetry &&
    !path.includes('/auth/login') &&
    !path.includes('/auth/refresh')
  ) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      return apiFetch<T>(path, { ...options, _isRetry: true });
    }
    // Refresh failed — redirect to login
    if (typeof window !== 'undefined') {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      document.cookie = 'access_token=; path=/; max-age=0';
      document.cookie = 'refresh_token=; path=/; max-age=0';
      window.location.href = '/login';
    }
  }

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
   * Upload file with progress tracking via XMLHttpRequest.
   * onProgress receives a value 0-100.
   */
  uploadWithProgress: <T = unknown>(
    path: string,
    formData: FormData,
    onProgress: (percent: number) => void,
    options?: { includeAuth?: boolean },
  ): Promise<T> => {
    const url = path.startsWith('http') ? path : `${API_V1}${path}`;
    return new Promise<T>((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', url);

      const token = getAuthToken();
      if (token && (options?.includeAuth ?? true)) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const pct = Math.round((e.loaded / e.total) * 100);
          onProgress(pct);
        }
      });

      xhr.addEventListener('load', () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            resolve(JSON.parse(xhr.responseText) as T);
          } catch {
            reject(new Error('Invalid JSON response'));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || `Upload Error: ${xhr.status}`));
          } catch {
            reject(new Error(`Upload Error: ${xhr.status}`));
          }
        }
      });

      xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
      xhr.addEventListener('abort', () => reject(new Error('Upload aborted')));

      xhr.send(formData);
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
