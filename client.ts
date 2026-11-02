/**
 * Thin typed HTTP client — the RN equivalent of SupabaseAuthRepository /
 * SupabaseProfileRepository: this is the ONLY module that knows the API's
 * base URL and attaches the auth header. Screens/hooks never call fetch()
 * directly (same "no direct backend calls from the presentation layer"
 * rule as the Flutter phase, ADR-0005).
 *
 * Handles access-token expiry transparently: unlike the Supabase SDK
 * (which refreshed tokens for us), this backend requires an explicit
 * POST /auth/token/refresh/ call. A 401 triggers exactly one refresh
 * attempt + one retry of the original request — never an infinite loop
 * (`isRetry` guards that), and a failed refresh clears tokens and
 * surfaces the 401 as-is so the caller's normal error handling (and, at
 * the AuthContext level, eventually a forced sign-out) takes over.
 */
import { secureStorage } from '../auth/secureStorage';

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api';

export class ApiError extends Error {
  constructor(
    public code: string,
    message: string,
    public status: number,
    public fields: Record<string, string> = {},
  ) {
    super(message);
  }
}

// Fired when the session can no longer be refreshed, so AuthContext can flip
// to `unauthenticated` immediately (closes the 0.1 "residual gap").
type Listener = () => void;
const sessionExpiredListeners = new Set<Listener>();
export function onSessionExpired(listener: Listener): () => void {
  sessionExpiredListeners.add(listener);
  return () => sessionExpiredListeners.delete(listener);
}

let refreshPromise: Promise<boolean> | null = null;

async function refreshAccessToken(): Promise<boolean> {
  // De-duplicated: if several requests 401 at once, only one refresh call
  // is made; the rest await the same in-flight promise.
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const { refresh } = await secureStorage.getTokens();
      if (!refresh) return false;
      try {
        const response = await fetch(`${BASE_URL}/auth/token/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh }),
        });
        if (!response.ok) return false;
        const data = await response.json();
        // SIMPLE_JWT's ROTATE_REFRESH_TOKENS returns a new refresh token
        // too — persist both, not just the access token.
        await secureStorage.setTokens(data.access, data.refresh ?? refresh);
        return true;
      } catch {
        return false;
      }
    })().finally(() => {
      refreshPromise = null;
    });
  }
  return refreshPromise;
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown; auth?: boolean; isRetry?: boolean } = {},
): Promise<T> {
  const isForm = typeof FormData !== 'undefined' && options.body instanceof FormData;
  // For multipart the runtime must set the Content-Type itself (it adds the boundary).
  const headers: Record<string, string> = isForm ? {} : { 'Content-Type': 'application/json' };

  if (options.auth !== false) {
    const { access } = await secureStorage.getTokens();
    if (access) headers.Authorization = `Bearer ${access}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body: options.body === undefined ? undefined : isForm ? (options.body as FormData) : JSON.stringify(options.body),
  });

  if (response.status === 401 && options.auth !== false && !options.isRetry) {
    const refreshed = await refreshAccessToken();
    if (refreshed) {
      return request<T>(path, { ...options, isRetry: true });
    }
    await secureStorage.clearTokens();
    sessionExpiredListeners.forEach((l) => l());
    // Falls through to the normal error path below.
  }

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    // Backend always responds {"error": {"code", "message"}} — see
    // backend/core/exceptions.py. Never surface raw response text.
    const err = data?.error ?? { code: 'unknown', message: 'Something went wrong.' };
    throw new ApiError(err.code, err.message, response.status, err.fields ?? {});
  }

  return data as T;
}

export const apiClient = { request };
