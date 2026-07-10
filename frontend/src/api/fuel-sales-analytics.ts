import { apiFetch } from "./client";
import type {
  FuelSalesByProductRow,
  FuelSalesFreshness,
  FuelSalesSummary,
  FuelSalesTrendPoint,
} from "./fuel-sales-analytics.types";

type DateRange = { date_from: string; date_to: string };

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

export async function fetchFuelSalesFreshness() {
  return apiFetch<FuelSalesFreshness>("/api/v1/analytics/fuel-sales/freshness");
}

export async function fetchFuelSalesDataQuality(range: DateRange) {
  return apiFetch(`/api/v1/analytics/fuel-sales/data-quality?${new URLSearchParams(params(range))}`);
}

export type {
  FuelSalesByProductRow,
  FuelSalesFreshness,
  FuelSalesSummary,
  FuelSalesTrendPoint,
} from "./fuel-sales-analytics.types";
