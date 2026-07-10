import { API_BASE_URL, apiFetch, getAccessToken } from "./client";

async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const stationId = localStorage.getItem("active_station_id");
  if (stationId) headers.set("X-Station-Id", stationId);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
  });

  if (!response.ok) {
    let message = "Falha na requisição.";
    try {
      const payload = await response.json();
      message = payload?.error?.message ?? message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export type QuoteListItem = {
  id: string;
  quote_number: number;
  station_id: string;
  distributor_id: string;
  quoted_at: string;
  valid_until: string;
  source_channel: string;
  status: string;
  effective_status: string;
  version: number;
  item_count: number;
};

export type QuoteList = {
  items: QuoteListItem[];
  total: number;
  page: number;
  page_size: number;
  summary: Record<string, number>;
};

export type QuoteItem = {
  id: string;
  product_id: string;
  distribution_base_id: string | null;
  sequence: number;
  quoted_price_per_liter: string;
  payment_term_id: string;
  payment_type_snapshot: string;
  payment_term_days_snapshot: number;
  payment_term_name_snapshot: string;
  freight_type: string;
  freight_calculation_type: string;
  freight_value_total: string | null;
  freight_value_per_liter: string | null;
  discount_per_liter: string;
  rebate_per_liter: string;
  other_cost_per_liter: string;
  other_cost_description: string | null;
  minimum_volume_liters: string;
  available_volume_liters: string | null;
  delivery_expected_at: string | null;
  valid_until: string | null;
  notes: string | null;
  item_effective_status?: string;
  effective_valid_until?: string;
};

export type QuoteEvidence = {
  id: string;
  category: string;
  original_file_name: string;
  content_type: string;
  file_extension: string;
  size_bytes: number;
  sha256: string;
  is_supplemental: boolean;
  active: boolean;
  uploaded_by: string;
  uploaded_at: string;
};

export type Quote = {
  id: string;
  organization_id: string;
  station_id: string;
  distributor_id: string;
  distribution_base_id: string | null;
  quote_number: number;
  quoted_at: string;
  valid_until: string;
  source_channel: string;
  entry_method: string;
  seller_name: string | null;
  seller_contact: string | null;
  external_reference: string | null;
  source_description: string | null;
  notes: string | null;
  status: string;
  effective_status: string;
  version: number;
  replaces_quote_id: string | null;
  duplicated_from_quote_id: string | null;
  activated_at: string | null;
  items: QuoteItem[];
  evidences: QuoteEvidence[];
  warnings: string[];
};

export type QuoteHistoryEntry = {
  id: string;
  action: string;
  version: number;
  reason: string | null;
  changed_fields: Record<string, unknown> | null;
  metadata: Record<string, unknown> | null;
  user_id: string | null;
  created_at: string;
};

type QueryParams = Record<string, string | number | boolean | undefined>;

function buildQuery(params: QueryParams = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function fetchQuotes(params: QueryParams = {}) {
  return apiFetch<QuoteList>(`/api/v1/quotes${buildQuery(params)}`);
}

export async function fetchQuote(quoteId: string) {
  return apiFetch<Quote>(`/api/v1/quotes/${quoteId}`);
}

export async function createQuote(payload: Record<string, unknown>) {
  return apiFetch<Quote>("/api/v1/quotes", { method: "POST", body: JSON.stringify(payload) });
}

export async function updateQuote(quoteId: string, payload: Record<string, unknown>) {
  return apiFetch<Quote>(`/api/v1/quotes/${quoteId}`, { method: "PATCH", body: JSON.stringify(payload) });
}

export async function addQuoteItem(quoteId: string, payload: Record<string, unknown>) {
  return apiFetch<QuoteItem>(`/api/v1/quotes/${quoteId}/items`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function activateQuote(quoteId: string, expectedVersion: number) {
  return apiFetch<Quote>(`/api/v1/quotes/${quoteId}/activate`, {
    method: "POST",
    body: JSON.stringify({ expected_version: expectedVersion }),
  });
}

export async function cancelQuote(quoteId: string, expectedVersion: number, reason: string) {
  return apiFetch<Quote>(`/api/v1/quotes/${quoteId}/cancel`, {
    method: "POST",
    body: JSON.stringify({ expected_version: expectedVersion, reason }),
  });
}

export async function reviseQuote(quoteId: string, reason: string) {
  return apiFetch<Quote>(`/api/v1/quotes/${quoteId}/revise`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function duplicateQuote(quoteId: string, payload: Record<string, unknown>) {
  return apiFetch<Quote>(`/api/v1/quotes/${quoteId}/duplicate`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function fetchQuoteHistory(quoteId: string, page = 1) {
  return apiFetch<{ items: QuoteHistoryEntry[]; total: number }>(
    `/api/v1/quotes/${quoteId}/history${buildQuery({ page })}`,
  );
}

export async function uploadQuoteEvidence(
  quoteId: string,
  file: File,
  category: string,
  expectedVersion: number,
  isSupplemental = false,
) {
  const form = new FormData();
  form.append("file", file);
  form.append("category", category);
  form.append("expected_version", String(expectedVersion));
  form.append("is_supplemental", String(isSupplemental));
  return apiUpload<Quote>(`/api/v1/quotes/${quoteId}/evidences`, form);
}

export async function fetchItemPrefill(params: {
  station_id: string;
  distributor_id: string;
  product_id: string;
  distribution_base_id?: string;
}) {
  return apiFetch<{
    minimum_volume_liters: string;
    distribution_base_id: string | null;
    supplier_allowed: boolean;
    rule_source: string;
    alert_supplier_not_allowed: boolean;
  }>(`/api/v1/quotes/item-prefill${buildQuery(params)}`);
}
