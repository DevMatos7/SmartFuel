import { apiFetch } from "./client";

export type RankingMode = "RAW" | "DELIVERED" | "FINANCIAL_EQUIVALENT";
export type RankingScope = "BEST_PER_DISTRIBUTOR" | "ALL_OFFERS";

export interface FinancialParameter {
  id: string;
  annual_effective_rate: string;
  day_count_basis: number;
  methodology_version: string;
  valid_from: string;
  valid_until: string | null;
  notes: string | null;
  active: boolean;
}

export interface ComparisonScenarioInput {
  station_id: string;
  product_id: string;
  requested_volume_liters: string;
  comparison_datetime: string;
  required_delivery_at?: string | null;
  ranking_mode?: RankingMode;
  ranking_scope?: RankingScope;
}

export interface EligibilityReason {
  code: string;
  severity: string;
  message: string;
  metadata: Record<string, unknown>;
}

export interface ComparisonCosts {
  raw_price_per_liter: string;
  discount_per_liter: string;
  rebate_per_liter: string;
  freight_per_liter: string;
  other_cost_per_liter: string;
  delivered_cost_per_liter: string;
  delivered_total: string;
  financial_days?: number | null;
  annual_effective_rate?: string | null;
  daily_rate?: string | null;
  financial_equivalent_cost_per_liter?: string | null;
  financial_equivalent_total?: string | null;
}

export interface ComparisonResult {
  quote_id: string;
  quote_item_id: string;
  quote_number?: number | null;
  distributor: { id: string; name: string };
  eligibility_status: string;
  eligibility_reasons: EligibilityReason[];
  costs: ComparisonCosts;
  rank_position?: number | null;
  difference_per_liter?: string | null;
  difference_total?: string | null;
  is_best_for_distributor: boolean;
  is_best_overall: boolean;
  payment_term_name?: string | null;
  delivery_expected_at?: string | null;
  effective_valid_until?: string | null;
  calculation_snapshot: Record<string, unknown>;
}

export interface ComparisonRunListItem {
  id: string;
  station_id: string;
  product_id: string;
  requested_volume_liters: string;
  comparison_datetime: string;
  ranking_mode: RankingMode;
  ranking_scope: RankingScope;
  best_cost_per_liter?: string | null;
  eligible_count: number;
  distributor_count: number;
  created_at: string;
  created_by: string;
}

export interface ComparisonRun {
  id: string;
  status: string;
  methodology_version: string;
  scenario: {
    station_id: string;
    product_id: string;
    requested_volume_liters: string;
    comparison_datetime: string;
    required_delivery_at?: string | null;
    ranking_mode: RankingMode;
    ranking_scope: RankingScope;
  };
  summary: {
    eligible_count: number;
    warning_count: number;
    ineligible_count: number;
    distributor_count: number;
    best_cost_per_liter?: string | null;
    highest_cost_per_liter?: string | null;
    average_cost_per_liter?: string | null;
    spread_absolute?: string | null;
    spread_percent?: string | null;
  };
  results: ComparisonResult[];
  calculation_hash?: string | null;
  created_at: string;
  created_by: string;
}

export async function listFinancialParameters(params?: {
  active?: boolean;
  page?: number;
  page_size?: number;
}) {
  const response = await apiFetch<{ items: FinancialParameter[]; total: number }>(
    `/api/v1/financial-parameters${buildQuery(params)}`,
  );
  return response;
}

function buildQuery(params?: Record<string, string | number | boolean | undefined>) {
  if (!params) return "";
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

export async function createFinancialParameter(payload: {
  annual_effective_rate: string;
  day_count_basis?: number;
  valid_from: string;
  valid_until?: string | null;
  notes?: string | null;
}) {
  return apiFetch<FinancialParameter>("/api/v1/financial-parameters", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function runQuoteComparison(payload: ComparisonScenarioInput) {
  return apiFetch<ComparisonRun>("/api/v1/quote-comparisons", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getQuoteComparison(runId: string) {
  return apiFetch<ComparisonRun>(`/api/v1/quote-comparisons/${runId}`);
}

export async function listQuoteComparisons(params?: Record<string, string | number | undefined>) {
  return apiFetch<{ items: ComparisonRunListItem[]; total: number }>(
    `/api/v1/quote-comparisons${buildQuery(params)}`,
  );
}

export async function getComparisonMethodology() {
  return apiFetch<Record<string, unknown>>("/api/v1/quote-comparisons/methodology");
}

export async function reprocessQuoteComparison(
  runId: string,
  payload: Partial<ComparisonScenarioInput>,
) {
  return apiFetch<ComparisonRun>(`/api/v1/quote-comparisons/${runId}/reprocess`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function comparisonExportUrl(runId: string, format: "pdf" | "csv") {
  return `/api/v1/quote-comparisons/${runId}/export/${format}`;
}
