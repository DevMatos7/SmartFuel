import { apiFetch } from "./client";

export type MarketSummary = {
  disclaimer: string;
  runs_count: number;
  completed_count: number;
  insufficient_sample_count: number;
  strongest_association: {
    run_id: string | null;
    coefficient: string | null;
    selected_lag: number | null;
    label: string;
  } | null;
  note?: string;
};

export type MarketRun = {
  id: string;
  status: string;
  analysis_type: string;
  external_series_code: string | null;
  internal_series_type: string;
  sample_size: number;
  aligned_pair_count: number;
  selected_lag: number | null;
  transformation: string;
  frequency: string;
  snapshot_hash: string | null;
  interpretive_disclaimer: string;
  started_at: string;
  finished_at: string | null;
  output_snapshot: Record<string, unknown> | null;
  warning_count: number;
};

export function fetchMarketCorrelationSummary() {
  return apiFetch<MarketSummary>("/analytics/market-correlation/summary");
}

export function fetchMarketRuns() {
  return apiFetch<MarketRun[]>("/market-analysis/runs");
}

export function fetchMarketRun(id: string) {
  return apiFetch<MarketRun>(`/market-analysis/runs/${id}`);
}

export function createSyntheticMarketRun(body: Record<string, unknown>) {
  return apiFetch<MarketRun>("/market-analysis/runs", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function reprocessMarketRun(id: string, reason: string) {
  return apiFetch<MarketRun>(`/market-analysis/runs/${id}/reprocess`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export function fetchMarketParameters() {
  return apiFetch<Record<string, unknown>>("/market-analysis/parameters");
}
