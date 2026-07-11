import { apiFetch } from "./client";

export type ExecutiveCard = {
  metric_code: string;
  label: string;
  value: string | null;
  previous_value?: string | null;
  unit: string | null;
  quality_status: string;
  freshness_status: string;
  coverage_percentage: string | null;
  updated_at: string | null;
  deep_link: string;
  source_modules: string[];
  empty_reason?: string | null;
};

export type ExecutiveSummary = {
  cards: ExecutiveCard[];
  empty?: boolean;
  empty_reason?: string;
  disclaimer?: string;
  by_station?: Array<Record<string, unknown>>;
  synthetic?: boolean;
};

export type AlertRow = {
  id: string;
  alert_code: string;
  severity: string;
  priority: string;
  status: string;
  title: string;
  summary: string;
  station_id: string | null;
  occurrence_count: number;
  last_detected_at: string;
  deep_link: string | null;
  dismissible: boolean;
};

export type Readiness = {
  status: string;
  reason: string | null;
  gates: Array<{ gate: string; ok: boolean; status: string; reason?: string | null }>;
  production_with_sa_blocked: boolean;
  scheduler_blocked: boolean;
};

export function fetchExecutiveSummary() {
  return apiFetch<ExecutiveSummary>("/executive/summary");
}

export function runExecutiveSynthetic(stationIds?: string[]) {
  return apiFetch<ExecutiveSummary>("/executive/homologation/synthetic", {
    method: "POST",
    body: JSON.stringify({ station_ids: stationIds ?? null }),
  });
}

export function fetchExecutiveByStation() {
  return apiFetch<Array<Record<string, unknown>>>("/executive/by-station");
}

export function fetchAlertsSummary() {
  return apiFetch<Record<string, number>>("/alerts/summary");
}

export function fetchAlerts(params?: { status?: string; severity?: string }) {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.severity) q.set("severity", params.severity);
  const suffix = q.toString() ? `?${q}` : "";
  return apiFetch<AlertRow[]>(`/alerts${suffix}`);
}

export function fetchAlert(id: string) {
  return apiFetch<Record<string, unknown>>(`/alerts/${id}`);
}

export function acknowledgeAlert(id: string, comment?: string) {
  return apiFetch(`/alerts/${id}/acknowledge`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });
}

export function resolveAlert(id: string, note?: string) {
  return apiFetch(`/alerts/${id}/resolve`, {
    method: "POST",
    body: JSON.stringify({ resolution_code: "FIXED", note }),
  });
}

export function fetchOperationsHealth() {
  return apiFetch<Record<string, unknown>>("/operations/health");
}

export function fetchOperationsJobs() {
  return apiFetch<Array<Record<string, unknown>>>("/operations/jobs");
}

export function fetchOperationsSlo() {
  return apiFetch<Array<Record<string, unknown>>>("/operations/slo");
}

export function fetchOperationsReadiness() {
  return apiFetch<Readiness>("/operations/readiness");
}

export function fetchIncidents() {
  return apiFetch<Array<Record<string, unknown>>>("/operations/incidents");
}

export function fetchAlertRules() {
  return apiFetch<Array<Record<string, unknown>>>("/alert-rules");
}

export function fetchFeatureFlags() {
  return apiFetch<Array<{ flag_code: string; enabled: boolean }>>("/operations/feature-flags");
}
