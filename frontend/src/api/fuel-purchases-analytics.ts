import { apiFetch } from "./client";
import type {
  AccountsPayableAgingBucket,
  AccountsPayableSummary,
  AccountsPayableTitleRow,
  FuelPurchaseInvoiceDetail,
  FuelPurchaseInvoiceItem,
  FuelPurchaseInvoiceListRow,
  FuelPurchaseInvoiceTitle,
  FuelPurchaseInvoiceXml,
  FuelPurchasesByDistributorRow,
  FuelPurchasesByProductRow,
  FuelPurchasesCosts,
  FuelPurchasesDataQuality,
  FuelPurchasesFreshness,
  FuelPurchasesSummary,
  FuelPurchasesTrendPoint,
  NfeDocumentDetail,
  NfeDocumentRow,
  PaginatedResponse,
} from "./fuel-purchases-analytics.types";

export type DateRange = { date_from: string; date_to: string };

function params(range: DateRange) {
  return { date_from: range.date_from, date_to: range.date_to };
}

function toQuery(search: Record<string, string | number | undefined>) {
  const entries = Object.entries(search).filter(([, v]) => v !== undefined && v !== "");
  return new URLSearchParams(entries.map(([k, v]) => [k, String(v)]));
}

export async function fetchFuelPurchasesSummary(range: DateRange) {
  return apiFetch<FuelPurchasesSummary>(
    `/api/v1/analytics/fuel-purchases/summary?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelPurchasesTrend(range: DateRange) {
  return apiFetch<FuelPurchasesTrendPoint[]>(
    `/api/v1/analytics/fuel-purchases/trend?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelPurchasesByProduct(range: DateRange) {
  return apiFetch<FuelPurchasesByProductRow[]>(
    `/api/v1/analytics/fuel-purchases/by-product?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelPurchasesByDistributor(range: DateRange) {
  return apiFetch<FuelPurchasesByDistributorRow[]>(
    `/api/v1/analytics/fuel-purchases/by-distributor?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelPurchasesCosts(range: DateRange) {
  return apiFetch<FuelPurchasesCosts>(
    `/api/v1/analytics/fuel-purchases/costs?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelPurchasesDataQuality(range: DateRange) {
  return apiFetch<FuelPurchasesDataQuality>(
    `/api/v1/analytics/fuel-purchases/data-quality?${new URLSearchParams(params(range))}`,
  );
}

export async function fetchFuelPurchasesFreshness() {
  return apiFetch<FuelPurchasesFreshness>("/api/v1/analytics/fuel-purchases/freshness");
}

export async function fetchFuelPurchaseInvoices(search: {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  distributor_id?: string;
  q?: string;
}) {
  return apiFetch<PaginatedResponse<FuelPurchaseInvoiceListRow>>(
    `/api/v1/fuel-purchase-invoices?${toQuery(search)}`,
  );
}

export async function fetchFuelPurchaseInvoice(id: string) {
  return apiFetch<FuelPurchaseInvoiceDetail>(`/api/v1/fuel-purchase-invoices/${id}`);
}

export async function fetchFuelPurchaseInvoiceItems(id: string) {
  return apiFetch<FuelPurchaseInvoiceItem[]>(`/api/v1/fuel-purchase-invoices/${id}/items`);
}

export async function fetchFuelPurchaseInvoiceTitles(id: string) {
  return apiFetch<FuelPurchaseInvoiceTitle[]>(`/api/v1/fuel-purchase-invoices/${id}/titles`);
}

export async function fetchFuelPurchaseInvoiceXml(id: string) {
  return apiFetch<FuelPurchaseInvoiceXml>(`/api/v1/fuel-purchase-invoices/${id}/xml`);
}

export async function fetchAccountsPayableSummary(range?: DateRange) {
  const query = range ? new URLSearchParams(params(range)) : "";
  return apiFetch<AccountsPayableSummary>(
    `/api/v1/accounts-payable/summary${query ? `?${query}` : ""}`,
  );
}

export async function fetchAccountsPayableAging(range?: DateRange) {
  const query = range ? new URLSearchParams(params(range)) : "";
  return apiFetch<AccountsPayableAgingBucket[]>(
    `/api/v1/accounts-payable/aging${query ? `?${query}` : ""}`,
  );
}

export async function fetchAccountsPayableTitles(search: {
  page?: number;
  page_size?: number;
  date_from?: string;
  date_to?: string;
  status?: string;
}) {
  return apiFetch<PaginatedResponse<AccountsPayableTitleRow>>(
    `/api/v1/accounts-payable/titles?${toQuery(search)}`,
  );
}

export async function fetchNfeDocuments(search: { page?: number; page_size?: number; q?: string }) {
  return apiFetch<PaginatedResponse<NfeDocumentRow>>(`/api/v1/nfe-documents?${toQuery(search)}`);
}

export async function fetchNfeDocument(id: string) {
  return apiFetch<NfeDocumentDetail>(`/api/v1/nfe-documents/${id}`);
}

export type {
  AccountsPayableAgingBucket,
  AccountsPayableSummary,
  AccountsPayableTitleRow,
  FuelPurchaseInvoiceDetail,
  FuelPurchaseInvoiceItem,
  FuelPurchaseInvoiceListRow,
  FuelPurchaseInvoiceTitle,
  FuelPurchaseInvoiceXml,
  FuelPurchasesByDistributorRow,
  FuelPurchasesByProductRow,
  FuelPurchasesCosts,
  FuelPurchasesDataQuality,
  FuelPurchasesFreshness,
  FuelPurchasesSummary,
  FuelPurchasesTrendPoint,
  NfeDocumentDetail,
  NfeDocumentRow,
} from "./fuel-purchases-analytics.types";
