const API_BASE = '/api';

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

function getCredentials(): { username: string; password: string } {
  const stored = localStorage.getItem('wfm_credentials');
  if (stored) {
    try {
      return JSON.parse(stored);
    } catch {
      localStorage.removeItem('wfm_credentials');
    }
  }
  return { username: '', password: '' };
}

function authHeader(): Record<string, string> {
  const { username, password } = getCredentials();
  if (!username || !password) return {};
  const encoded = btoa(`${username}:${password}`);
  return { Authorization: `Basic ${encoded}` };
}

function headers(extra?: Record<string, string>): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    ...authHeader(),
    ...extra,
  };
}

export async function apiGet<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        url.searchParams.set(k, v);
      }
    });
  }
  const res = await fetch(url.toString(), { headers: headers() });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
  return res.json();
}

export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: headers(),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export async function apiPut<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: headers(),
    body: body ? JSON.stringify(body) : undefined,
  });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
  return res.json();
}

export async function apiDelete(path: string): Promise<void> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: headers(),
  });
  if (res.status === 401) {
    throw new ApiError(401, 'Authentication required');
  }
  if (!res.ok) {
    const errBody = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, errBody.detail || res.statusText);
  }
}

export function setCredentials(username: string, password: string): void {
  localStorage.setItem('wfm_credentials', JSON.stringify({ username, password }));
}

export function clearCredentials(): void {
  localStorage.removeItem('wfm_credentials');
}

export function hasCredentials(): boolean {
  const { username, password } = getCredentials();
  return !!username && !!password;
}
