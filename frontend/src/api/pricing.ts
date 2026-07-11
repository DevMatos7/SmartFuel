import { apiFetch } from "./client";

export type PricingSummary = {
  monitored_products: number;
  below_floor: number;
  average_margin_per_liter: string | null;
  increase_recommendations: number;
  decrease_recommendations: number;
  pending_approval: number;
  approved_not_implemented: number;
  divergent_implementations: number;
  disclaimer: string;
  xpert_write_enabled: boolean;
};

export type PricingItem = {
  id: string;
  recommendation_run_id: string;
  station_id: string;
  canonical_product_id: string;
  price_type: string;
  current_price: string | null;
  cost_per_liter: string | null;
  cost_confidence: string;
  current_margin_per_liter: string | null;
  commercial_floor_price: string | null;
  target_price: string | null;
  recommended_price: string | null;
  recommendation_status: string;
  quality_status: string;
  guardrail_applied: boolean;
  reasons: string[] | null;
  warnings: string[] | null;
  snapshot_hash: string;
  result_snapshot?: Record<string, unknown> | null;
};

export type PricingDecision = {
  id: string;
  recommendation_item_id: string;
  status: string;
  recommended_price: string;
  approved_price: string | null;
  decision_reason: string | null;
  created_at: string;
};

export type PricingPolicy = {
  id: string;
  name: string;
  status: string;
  cost_basis_type: string;
  price_type: string;
  minimum_margin_per_liter: string | null;
  target_margin_per_liter: string | null;
  rounding_policy: string;
  default_scenario: string;
  required_approvals: number;
  allow_self_approval: boolean;
  valid_from: string;
  active: boolean;
};

export type PricingRun = {
  id: string;
  status: string;
  trigger_type: string;
  item_count: number;
  recommendation_count: number;
  warning_count: number;
  snapshot_hash: string | null;
  interpretive_disclaimer: string;
  started_at: string;
  finished_at: string | null;
};

export function fetchPricingSummary() {
  return apiFetch<PricingSummary>("/analytics/pricing/summary");
}

export function fetchPricingRecommendations() {
  return apiFetch<PricingItem[]>("/pricing/recommendations");
}

export function fetchPricingRecommendation(id: string) {
  return apiFetch<PricingItem>(`/pricing/recommendations/${id}`);
}

export function fetchPricingScenarios(id: string) {
  return apiFetch<
    Array<{
      scenario_type: string;
      rounded_price: string;
      calculated_price: string;
      margin_per_liter: string;
      details: Record<string, unknown> | null;
    }>
  >(`/pricing/recommendations/${id}/scenarios`);
}

export function fetchPricingDecisions(status?: string) {
  const q = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<PricingDecision[]>(`/pricing/decisions${q}`);
}

export function fetchPricingPolicies() {
  return apiFetch<PricingPolicy[]>("/pricing/policies");
}

export function fetchPricingRuns() {
  return apiFetch<PricingRun[]>("/pricing/recommendations/runs");
}

export function fetchPricingDataQuality() {
  return apiFetch<{ by_quality_status: Record<string, number>; total: number }>(
    "/analytics/pricing/data-quality",
  );
}

export function fetchBelowFloor() {
  return apiFetch<
    Array<{ id: string; station_id: string; current_price: string; commercial_floor_price: string; gap: string | null }>
  >("/analytics/pricing/below-floor");
}

export function createPricingDecision(itemId: string, body: { required_approvals?: number; decision_reason?: string }) {
  return apiFetch<PricingDecision>(`/pricing/recommendations/${itemId}/decision`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function submitPricingDecision(id: string) {
  return apiFetch<PricingDecision>(`/pricing/decisions/${id}/submit`, { method: "POST", body: "{}" });
}

export function approvePricingDecision(id: string, comment?: string, allowSelfApproval = false) {
  return apiFetch<PricingDecision>(`/pricing/decisions/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ comment, allow_self_approval: allowSelfApproval }),
  });
}

export function rejectPricingDecision(id: string, comment?: string) {
  return apiFetch<PricingDecision>(`/pricing/decisions/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  });
}

export function confirmImplementation(id: string, implementedPrice: string, note?: string) {
  return apiFetch<{ id: string; status: string; xpert_write: boolean }>(
    `/pricing/decisions/${id}/confirm-implementation`,
    {
      method: "POST",
      body: JSON.stringify({ implemented_price: implementedPrice, note }),
    },
  );
}

export function addPricingEvidence(id: string, description: string) {
  return apiFetch<{ id: string }>(`/pricing/decisions/${id}/evidence`, {
    method: "POST",
    body: JSON.stringify({ evidence_type: "NOTE", description }),
  });
}

export function runSyntheticPricingHomologation(stationId: string, productId: string) {
  return apiFetch<{ scenarios: Array<{ label: string; run_id: string }>; xpert_write: boolean }>(
    "/pricing/homologation/synthetic",
    {
      method: "POST",
      body: JSON.stringify({ station_id: stationId, canonical_product_id: productId }),
    },
  );
}

export function exportPricingCsvUrl() {
  return "/api/v1/analytics/pricing/export/csv";
}
