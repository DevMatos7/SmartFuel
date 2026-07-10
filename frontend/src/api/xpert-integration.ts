import { apiFetch } from "./client";

export type XpertSummary = {
  status: string;
  security_status?: string | null;
  source_id?: string;
  sources_count: number;
  datasets_enabled: number;
  pending_products: number;
  pending_suppliers: number;
  error_runs: number;
  last_success_at: string | null;
  odbc_available: boolean;
  worker_healthy: boolean;
  worker_last_heartbeat_at: string | null;
};

export type XpertSource = {
  id: string;
  code: string;
  name: string;
  host: string;
  port: number;
  database_name: string;
  driver_name: string;
  encrypt_connection: boolean;
  trust_server_certificate: boolean;
  secret_ref: string;
  source_timezone: string;
  enabled: boolean;
  connection_status: string;
  security_status?: string;
  last_tested_at: string | null;
  last_test_result: Record<string, unknown> | null;
};

export type XpertSourceInput = {
  code: string;
  name: string;
  host: string;
  port?: number;
  database_name: string;
  driver_name?: string;
  encrypt_connection?: boolean;
  trust_server_certificate?: boolean;
  secret_ref: string;
  source_timezone?: string;
  enabled?: boolean;
};

export type XpertDataset = {
  id: string;
  erp_source_id: string;
  code: string;
  name: string;
  contract_status: string;
  query_hash: string | null;
  sync_mode: string;
  checkpoint_type?: string;
  overlap_seconds: number;
  batch_size: number;
  schedule_enabled: boolean;
  schedule_interval_minutes: number | null;
  next_scheduled_at: string | null;
  contract_result: Record<string, unknown> | null;
  enabled: boolean;
};

export type XpertDatasetUpdate = {
  sync_mode?: string;
  overlap_seconds?: number;
  batch_size?: number;
  schedule_enabled?: boolean;
  schedule_interval_minutes?: number;
  enabled?: boolean;
};

export type XpertSyncRun = {
  id: string;
  erp_source_id: string;
  erp_dataset_id: string;
  station_id: string | null;
  status: string;
  sync_mode: string;
  trigger_type: string;
  rows_read: number;
  rows_staged?: number;
  rows_valid?: number;
  rows_applied: number;
  rows_inserted?: number;
  rows_updated?: number;
  rows_unchanged?: number;
  rows_error: number;
  rows_quarantined: number;
  rows_marked_inactive?: number;
  checkpoint_before: string | null;
  checkpoint_after: string | null;
  source_upper_bound?: string | null;
  window_start?: string | null;
  window_end?: string | null;
  worker_id?: string | null;
  error_code: string | null;
  error_message: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string;
};

export type XpertCheckpoint = {
  id: string;
  erp_source_id: string;
  erp_dataset_id: string;
  station_id: string | null;
  checkpoint_type: string;
  watermark_value: string | null;
  source_upper_bound: string | null;
  last_success_at: string | null;
};

export type XpertStagingRecord = {
  id: string;
  source_key: string;
  processing_status: string;
  record_hash: string | null;
  raw_payload: Record<string, unknown> | null;
  normalized_payload: Record<string, unknown> | null;
  applied_entity_type: string | null;
  applied_entity_id: string | null;
};

export type XpertSyncError = {
  id: string;
  phase: string;
  error_code: string;
  message: string;
  source_key: string | null;
  field_name?: string | null;
  created_at: string;
};

export const fetchXpertSummary = () => apiFetch<XpertSummary>("/api/v1/integrations/xpert");
export const fetchXpertSources = () => apiFetch<XpertSource[]>("/api/v1/integrations/xpert/sources");
export const fetchXpertSource = (id: string) => apiFetch<XpertSource>(`/api/v1/integrations/xpert/sources/${id}`);
export const createXpertSource = (payload: XpertSourceInput) =>
  apiFetch<XpertSource>("/api/v1/integrations/xpert/sources", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const updateXpertSource = (id: string, payload: Partial<XpertSourceInput>) =>
  apiFetch<XpertSource>(`/api/v1/integrations/xpert/sources/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const fetchXpertDatasets = (sourceId?: string) => {
  const query = sourceId ? `?source_id=${sourceId}` : "";
  return apiFetch<XpertDataset[]>(`/api/v1/integrations/xpert/datasets${query}`);
};
export const updateXpertDataset = (id: string, payload: XpertDatasetUpdate) =>
  apiFetch<XpertDataset>(`/api/v1/integrations/xpert/datasets/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
export const fetchXpertRuns = (params?: Record<string, string>) => {
  const query = new URLSearchParams(params).toString();
  return apiFetch<{ items: XpertSyncRun[]; total: number; page: number; page_size: number }>(
    `/api/v1/integrations/xpert/sync-runs${query ? `?${query}` : ""}`,
  );
};
export const fetchXpertRun = (id: string) =>
  apiFetch<XpertSyncRun>(`/api/v1/integrations/xpert/sync-runs/${id}`);
export const fetchXpertCheckpoints = (params?: Record<string, string>) => {
  const query = new URLSearchParams(params).toString();
  return apiFetch<XpertCheckpoint[]>(`/api/v1/integrations/xpert/checkpoints${query ? `?${query}` : ""}`);
};
export const resetXpertCheckpoint = (id: string, payload: { mode: "CLEAR" | "SET"; new_value?: string; reason: string }) =>
  apiFetch<XpertCheckpoint>(`/api/v1/integrations/xpert/checkpoints/${id}/reset`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const fetchXpertRunStaging = (runId: string) =>
  apiFetch<XpertStagingRecord[]>(`/api/v1/integrations/xpert/sync-runs/${runId}/staging`);
export const fetchXpertRunErrors = (runId: string) =>
  apiFetch<XpertSyncError[]>(`/api/v1/integrations/xpert/sync-runs/${runId}/errors`);
export const testXpertConnection = (sourceId: string) =>
  apiFetch<Record<string, unknown>>(`/api/v1/integrations/xpert/sources/${sourceId}/test-connection`, {
    method: "POST",
  });
export const validateXpertContract = (datasetId: string, stationId?: string) =>
  apiFetch<Record<string, unknown>>(
    `/api/v1/integrations/xpert/datasets/${datasetId}/validate-contract${stationId ? `?station_id=${stationId}` : ""}`,
    { method: "POST" },
  );
export const fetchXpertSupplierDocumentDiagnostics = (runId: string) =>
  apiFetch<{
    run_id: string;
    total_staged: number;
    applied: number;
    quarantined_invalid_document: number;
    by_reason: Record<string, number>;
  }>(`/api/v1/integrations/xpert/sync-runs/${runId}/supplier-document-diagnostics`);

export const createXpertSyncRuns = (payload: {
  source_id: string;
  dataset_codes: string[];
  station_ids: string[];
  sync_mode: string;
  unsafe_homologation_acknowledged?: boolean;
  history_start_date?: string;
  history_end_date?: string;
}) =>
  apiFetch<{ runs: XpertSyncRun[] }>("/api/v1/integrations/xpert/sync-runs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
export const cancelXpertRun = (runId: string) =>
  apiFetch<XpertSyncRun>(`/api/v1/integrations/xpert/sync-runs/${runId}/cancel`, { method: "POST" });
export const retryXpertRun = (runId: string) =>
  apiFetch<{ runs: XpertSyncRun[] }>(`/api/v1/integrations/xpert/sync-runs/${runId}/retry`, { method: "POST" });
