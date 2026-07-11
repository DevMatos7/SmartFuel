import { apiFetch } from "./client";

export type ExternalIndexCard = {
  series_id: string;
  series_code: string;
  series_name: string;
  value: string | null;
  unit: string;
  currency: string | null;
  observation_datetime: string | null;
  published_at: string | null;
  fetched_at: string | null;
  freshness: string;
  change_pct: string | null;
  frequency: string;
  note?: string;
};

export type ExternalIndicesSummary = {
  cards: ExternalIndexCard[];
  stale_series_count: number;
  open_quality_issues: number;
  disclaimer: string;
};

export type ExternalSeries = {
  id: string;
  source_id: string;
  code: string;
  name: string;
  frequency: string;
  source_unit: string;
  canonical_unit: string;
  currency: string | null;
  active: boolean;
};

export type ExternalSource = {
  id: string;
  code: string;
  name: string;
  source_type: string;
  status: string;
  connector_status: string;
  scheduler_enabled: boolean;
  requires_credentials: boolean;
};

export type ExternalObservation = {
  id: string;
  observation_datetime: string;
  canonical_value: string;
  canonical_unit: string;
  currency: string | null;
  published_at: string | null;
  fetched_at: string;
  revision_number: number;
  revision_status: string;
};

export type QualityIssue = {
  id: string;
  issue_code: string;
  severity: string;
  details: Record<string, unknown>;
  resolution_status: string;
  created_at: string;
};

export type IngestionRun = {
  id: string;
  trigger_type: string;
  status: string;
  records_read: number;
  records_inserted: number;
  records_revised: number;
  records_unchanged: number;
  records_rejected: number;
  started_at: string;
  finished_at: string | null;
};

export function fetchExternalIndicesSummary() {
  return apiFetch<ExternalIndicesSummary>("/analytics/external-indices/summary");
}

export function fetchExternalSeries() {
  return apiFetch<ExternalSeries[]>("/external-data/series");
}

export function fetchExternalSources() {
  return apiFetch<ExternalSource[]>("/external-data/sources");
}

export function bootstrapExternalCatalog() {
  return apiFetch<{ sources_created: number; series_created: number }>(
    "/external-data/bootstrap-catalog",
    { method: "POST" },
  );
}

export function fetchSeriesObservations(seriesId: string) {
  return apiFetch<ExternalObservation[]>(`/external-data/series/${seriesId}/observations`);
}

export function createManualObservation(
  seriesId: string,
  body: { observation_datetime: string; value: string; published_at?: string },
) {
  return apiFetch<Record<string, unknown>>(`/external-data/series/${seriesId}/observations`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchQualityIssues() {
  return apiFetch<QualityIssue[]>("/external-data/quality-issues");
}

export function fetchIngestionRuns() {
  return apiFetch<IngestionRun[]>("/external-data/runs");
}

export async function previewExternalImport(form: FormData) {
  return apiFetch<{
    import_file_id: string;
    run_id: string;
    preview: Array<Record<string, unknown>>;
    error_count: number;
    note: string;
  }>("/external-data/import/preview", { method: "POST", body: form });
}

export function confirmExternalImport(importFileId: string) {
  return apiFetch<Record<string, unknown>>("/external-data/import/confirm", {
    method: "POST",
    body: JSON.stringify({ import_file_id: importFileId }),
  });
}
