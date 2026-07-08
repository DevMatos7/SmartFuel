import { apiFetch, setAccessToken } from "./client";

export type LoginResponse = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: {
    id: string;
    name: string;
    email: string;
    must_change_password: boolean;
  };
};

export type MeResponse = {
  id: string;
  name: string;
  email: string;
  organization: { id: string; name: string };
  roles: string[];
  permissions: string[];
  stations: Array<{ id: string; trade_name: string; station_type: string; active: boolean }>;
  has_all_stations_access: boolean;
  must_change_password: boolean;
  last_login_at: string | null;
};

export async function login(email: string, password: string) {
  const data = await apiFetch<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setAccessToken(data.access_token);
  return data;
}

export async function logout() {
  await apiFetch("/api/v1/auth/logout", { method: "POST" });
  setAccessToken(null);
}

export async function fetchMe() {
  return apiFetch<MeResponse>("/api/v1/auth/me");
}

export async function changePassword(payload: {
  current_password: string;
  new_password: string;
  new_password_confirmation: string;
}) {
  const data = await apiFetch<LoginResponse>("/api/v1/auth/change-password", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setAccessToken(data.access_token);
  return data;
}
