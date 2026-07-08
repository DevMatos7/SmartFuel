import { apiFetch } from "./client";

export type Station = {
  id: string;
  organization_id: string;
  station_type: string;
  erp_branch_id: string | null;
  corporate_name: string;
  trade_name: string;
  cnpj: string;
  anp_code: string | null;
  brand_type: string;
  brand_name: string | null;
  timezone: string;
  active: boolean;
};

export type StationList = {
  items: Station[];
  total: number;
  page: number;
  page_size: number;
};

export async function fetchStations(params: Record<string, string | number | boolean | undefined> = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  return apiFetch<StationList>(`/api/v1/stations?${query.toString()}`);
}

export async function createStation(payload: Record<string, unknown>) {
  return apiFetch<Station>("/api/v1/stations", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateStation(id: string, payload: Record<string, unknown>) {
  return apiFetch<Station>(`/api/v1/stations/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateStation(id: string, reason: string) {
  return apiFetch<Station>(`/api/v1/stations/${id}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reactivateStation(id: string) {
  return apiFetch<Station>(`/api/v1/stations/${id}/reactivate`, { method: "POST" });
}
