import { apiFetch } from "./client";
import type {
  FuelSalesByProductRow,
  FuelSalesFreshness,
  FuelSalesMargins,
  FuelSalesPriceVarianceRow,
  FuelSalesRetailPriceRow,
  FuelSalesSummary,
  FuelSalesTrendPoint,
  FuelSalesUnmappedRow,
  ReconcileMappingsResponse,
} from "./fuel-sales-analytics.types";

export type DateRange = { date_from: string; date_to: string };

function params(range: DateRange) {
  return { date_from: range.date_from, date_to: range.date_to };
}

export async function fetchFuelSalesSummary(range: DateRange) {
  return apiFetch<FuelSalesSummary>(`/api/v1/analytics/fuel-sales/summary?${new URLSearchParams(params(range))}`);
}

export async function fetchFuelSalesTrend(range: DateRange) {
  return apiFetch<FuelSalesTrendPoint[]>(`/api/v1/analytics/fuel-sales/trend?${new URLSearchParams(params(range))}`);
}

export async function fetchFuelSalesByProduct(range: DateRange) {
  return apiFetch<FuelSalesByProductRow[]>(
    `/api/v1/analytics/fuel-sales/by-product?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelSalesMargins(range: DateRange) {
  return apiFetch<FuelSalesMargins>(`/api/v1/analytics/fuel-sales/margins?${new URLSearchParams(params(range))}`);
}

export async function fetchFuelSalesFreshness() {
  return apiFetch<FuelSalesFreshness>("/api/v1/analytics/fuel-sales/freshness");
}

export async function fetchFuelSalesDataQuality(range: DateRange) {
  return apiFetch(`/api/v1/analytics/fuel-sales/data-quality?${new URLSearchParams(params(range))}`);
}

export async function fetchFuelSalesUnmapped(range: DateRange) {
  return apiFetch<FuelSalesUnmappedRow[]>(
    `/api/v1/analytics/fuel-sales/unmapped?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelSalesPriceVariance(range: DateRange) {
  return apiFetch<FuelSalesPriceVarianceRow[]>(
    `/api/v1/analytics/fuel-sales/price-variance?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelSalesRetailPrices() {
  return apiFetch<FuelSalesRetailPriceRow[]>("/api/v1/analytics/fuel-sales/retail-prices");
}

export async function reconcileFuelSalesMappings() {
  return apiFetch<ReconcileMappingsResponse>("/api/v1/analytics/fuel-sales/reconcile-mappings", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export type {
  FuelSalesByProductRow,
  FuelSalesFreshness,
  FuelSalesMargins,
  FuelSalesPriceVarianceRow,
  FuelSalesRetailPriceRow,
  FuelSalesSummary,
  FuelSalesTrendPoint,
  FuelSalesUnmappedRow,
} from "./fuel-sales-analytics.types";
