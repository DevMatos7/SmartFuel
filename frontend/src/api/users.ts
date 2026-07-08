import { apiFetch } from "./client";

export type UserItem = {
  id: string;
  organization_id: string;
  name: string;
  email: string;
  active: boolean;
  must_change_password: boolean;
  has_all_stations_access: boolean;
  last_login_at: string | null;
  role_codes: string[];
  station_ids: string[];
};

export type UserList = {
  items: UserItem[];
  total: number;
  page: number;
  page_size: number;
};

export async function fetchUsers(params: Record<string, string | number | boolean | undefined> = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return apiFetch<UserList>(`/api/v1/users?${query.toString()}`);
}

export async function createUser(payload: Record<string, unknown>) {
  return apiFetch<UserItem>("/api/v1/users", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateUser(id: string, payload: Record<string, unknown>) {
  return apiFetch<UserItem>(`/api/v1/users/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function resetUserPassword(id: string, payload: Record<string, unknown>) {
  return apiFetch<{ temporary_password: string }>(`/api/v1/users/${id}/reset-password`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function deactivateUser(id: string, reason: string) {
  return apiFetch<UserItem>(`/api/v1/users/${id}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reactivateUser(id: string) {
  return apiFetch<UserItem>(`/api/v1/users/${id}/reactivate`, { method: "POST" });
}

export async function updateUserRoles(id: string, role_codes: string[]) {
  return apiFetch<UserItem>(`/api/v1/users/${id}/roles`, {
    method: "PUT",
    body: JSON.stringify({ role_codes }),
  });
}

export async function updateUserStations(
  id: string,
  payload: { station_ids: string[]; has_all_stations_access: boolean },
) {
  return apiFetch<UserItem>(`/api/v1/users/${id}/stations`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
