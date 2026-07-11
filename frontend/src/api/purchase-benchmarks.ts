import { apiFetch } from "./client";

export type BenchmarkSummary = {
  purchase_group_count: number;
  benchmarked_group_count: number;
  purchased_volume_liters: string;
  benchmarked_volume_liters: string;
  coverage_volume_ratio: string | null;
  actual_total_cost: string;
  benchmark_total_cost: string | null;
  cost_variance_amount: string | null;
  opportunity_amount: string | null;
  best_or_tied_count: number;
};

export type BenchmarkCoverage = {
  total_groups: number;
  total_volume_liters: string;
  total_value: string;
  by_status: Record<string, unknown>;
};

export type BenchmarkDataQuality = {
  unmapped_product_count: number;
  unmapped_supplier_warning_count: number;
  missing_cost_count: number;
  missing_volume_count: number;
  reference_unavailable_count: number;
  no_quotes_count: number;
  no_eligible_count: number;
  not_comparable_count: number;
  low_confidence_count: number;
};

export type BenchmarkOpportunity = {
  benchmark_item_id: string;
  purchase_invoice_id: string;
  station_id: string;
  canonical_product_id: string | null;
  volume_liters: string;
  opportunity_amount: string | null;
  cost_variance_per_liter: string | null;
  decision_result: string;
};

export type BenchmarkRunDetail = {
  id: string;
  purchase_invoice_id: string;
  station_id: string;
  status: string;
  comparison_mode: string;
  reference_datetime: string | null;
  reference_source: string;
  reference_confidence: string;
  item_count: number;
  benchmarked_item_count: number;
  actual_total_cost: string;
  benchmark_total_cost: string | null;
  cost_variance_amount: string | null;
  opportunity_amount: string | null;
  actual_advantage_amount: string | null;
  snapshot_hash: string | null;
  items: Array<{
    id: string;
    group_key: string;
    volume_liters: string;
    actual_delivered_cost_per_liter: string | null;
    benchmark_cost_per_liter: string | null;
    cost_variance_per_liter: string | null;
    decision_result: string;
    benchmark_status: string;
    opportunity_amount: string | null;
    actual_distributor_rank: number | null;
  }>;
};

function rangeQs(dateFrom?: string, dateTo?: string) {
  const sp = new URLSearchParams();
  if (dateFrom) sp.set("date_from", dateFrom);
  if (dateTo) sp.set("date_to", dateTo);
  const s = sp.toString();
  return s ? `?${s}` : "";
}

export function fetchBenchmarkSummary(dateFrom?: string, dateTo?: string) {
  return apiFetch<BenchmarkSummary>(`/api/v1/analytics/purchase-benchmarks/summary${rangeQs(dateFrom, dateTo)}`);
}

export function fetchBenchmarkCoverage(dateFrom?: string, dateTo?: string) {
  return apiFetch<BenchmarkCoverage>(`/api/v1/analytics/purchase-benchmarks/coverage${rangeQs(dateFrom, dateTo)}`);
}

export function fetchBenchmarkDataQuality(dateFrom?: string, dateTo?: string) {
  return apiFetch<BenchmarkDataQuality>(
    `/api/v1/analytics/purchase-benchmarks/data-quality${rangeQs(dateFrom, dateTo)}`,
  );
}

export function fetchBenchmarkOpportunities(dateFrom?: string, dateTo?: string) {
  return apiFetch<BenchmarkOpportunity[]>(
    `/api/v1/analytics/purchase-benchmarks/opportunities${rangeQs(dateFrom, dateTo)}`,
  );
}

export function fetchBenchmarkRun(id: string) {
  return apiFetch<BenchmarkRunDetail>(`/api/v1/purchase-benchmarks/runs/${id}`);
}

export function runInvoiceBenchmark(invoiceId: string) {
  return apiFetch<BenchmarkRunDetail>(`/api/v1/fuel-purchase-invoices/${invoiceId}/benchmark`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ purchase_invoice_id: invoiceId }),
  });
}

export function fetchLatestInvoiceBenchmark(invoiceId: string) {
  return apiFetch<BenchmarkRunDetail>(`/api/v1/fuel-purchase-invoices/${invoiceId}/latest-benchmark`);
}

export function reprocessBenchmarkRun(runId: string, reason: string) {
  return apiFetch<BenchmarkRunDetail>(`/api/v1/purchase-benchmarks/runs/${runId}/reprocess`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
}
