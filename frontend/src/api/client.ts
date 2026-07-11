const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export type ApiError = {
  error: {
    code: string;
    message: string;
    request_id: string;
  };
};

let accessToken: string | null = null;
let refreshPromise: Promise<string | null> | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function getAccessToken() {
  return accessToken;
}

export function resetClientForTests() {
  accessToken = null;
  refreshPromise = null;
}

export async function refreshAccessToken(): Promise<string | null> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    accessToken = null;
    return null;
  }
  const data = await response.json();
  accessToken = data.access_token;
  return accessToken;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const stationId = localStorage.getItem("active_station_id");
  if (stationId) {
    headers.set("X-Station-Id", stationId);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });

  if (response.status === 401 && retry && !path.includes("/auth/login")) {
    if (!refreshPromise) {
      refreshPromise = refreshAccessToken().finally(() => {
        refreshPromise = null;
      });
    }
    const newToken = await refreshPromise;
    if (newToken) {
      return apiFetch<T>(path, init, false);
    }
  }

  if (!response.ok) {
    let payload: ApiError | undefined;
    try {
      payload = await response.json();
    } catch {
      // ignore
    }
    throw new Error(payload?.error?.message ?? "Falha na requisição.");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export { API_BASE_URL };
