import { API_BASE_URL, apiFetch, getAccessToken } from "./client";

type QueryParams = Record<string, string | number | boolean | undefined>;

function buildQuery(params: QueryParams = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== "") query.set(key, String(value));
  });
  const qs = query.toString();
  return qs ? `?${qs}` : "";
}

async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const headers = new Headers();
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const stationId = localStorage.getItem("active_station_id");
  if (stationId) headers.set("X-Station-Id", stationId);

  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers,
    body: formData,
    credentials: "include",
  });

  if (!response.ok) {
    let message = "Falha na requisição.";
    try {
      const payload = await response.json();
      message = payload?.error?.message ?? message;
    } catch {
      // ignore
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

// --- Products ---

export type Product = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  fuel_family: string;
  commercial_variant: string;
  unit: string;
  regulatory_code: string | null;
  purchasable: boolean;
  sellable: boolean;
  display_order: number;
  active: boolean;
  code_locked: boolean;
  created_at: string;
  updated_at: string;
};

export type ProductList = {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
};

export type ProductCreatePayload = {
  code: string;
  name: string;
  fuel_family: string;
  commercial_variant: string;
  unit?: string;
  regulatory_code?: string | null;
  purchasable?: boolean;
  sellable?: boolean;
  display_order?: number;
  active?: boolean;
};

export type ProductUpdatePayload = Partial<ProductCreatePayload>;

export async function fetchProducts(params: QueryParams = {}) {
  return apiFetch<ProductList>(`/api/v1/products${buildQuery(params)}`);
}

export async function fetchProduct(id: string) {
  return apiFetch<Product>(`/api/v1/products/${id}`);
}

export async function createProduct(payload: ProductCreatePayload) {
  return apiFetch<Product>("/api/v1/products", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateProduct(id: string, payload: ProductUpdatePayload) {
  return apiFetch<Product>(`/api/v1/products/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateProduct(id: string, reason: string) {
  return apiFetch<Product>(`/api/v1/products/${id}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reactivateProduct(id: string) {
  return apiFetch<Product>(`/api/v1/products/${id}/reactivate`, { method: "POST" });
}

// --- ERP Products ---

export type ErpProduct = {
  id: string;
  organization_id: string;
  station_id: string;
  erp_product_id: string;
  erp_product_code: string | null;
  erp_description: string;
  erp_unit: string | null;
  erp_group_id: string | null;
  erp_group_name: string | null;
  erp_subgroup_id: string | null;
  erp_subgroup_name: string | null;
  canonical_product_id: string | null;
  mapping_status: string;
  mapping_source: string;
  ignore_reason: string | null;
  mapped_by: string | null;
  mapped_at: string | null;
  last_synced_at: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type ErpProductList = {
  items: ErpProduct[];
  total: number;
  page: number;
  page_size: number;
};

export type ProductMappingHistory = {
  id: string;
  erp_product_id: string;
  previous_product_id: string | null;
  new_product_id: string | null;
  previous_status: string | null;
  new_status: string;
  reason: string | null;
  changed_by: string;
  created_at: string;
};

export type ErpProductBulkMapResult = {
  mapped: ErpProduct[];
  failures: { erp_product_id: string; code: string; message: string }[];
};

export async function fetchErpProducts(params: QueryParams = {}) {
  return apiFetch<ErpProductList>(`/api/v1/erp-products${buildQuery(params)}`);
}

export async function fetchErpProduct(id: string) {
  return apiFetch<ErpProduct>(`/api/v1/erp-products/${id}`);
}

export async function mapErpProduct(id: string, payload: { canonical_product_id: string; reason?: string }) {
  return apiFetch<ErpProduct>(`/api/v1/erp-products/${id}/map`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function bulkMapErpProducts(payload: {
  erp_product_ids: string[];
  canonical_product_id: string;
  reason?: string;
}) {
  return apiFetch<ErpProductBulkMapResult>("/api/v1/erp-products/bulk-map", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ignoreErpProduct(id: string, reason: string) {
  return apiFetch<ErpProduct>(`/api/v1/erp-products/${id}/ignore`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reopenErpProduct(id: string, reason?: string) {
  return apiFetch<ErpProduct>(`/api/v1/erp-products/${id}/reopen`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

export async function fetchErpProductHistory(id: string) {
  return apiFetch<{ items: ProductMappingHistory[] }>(`/api/v1/erp-products/${id}/history`);
}

// --- Distributors ---

export type Distributor = {
  id: string;
  organization_id: string;
  internal_code: string;
  corporate_name: string;
  trade_name: string;
  cnpj: string | null;
  normalized_name: string;
  registration_status: string;
  notes: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type DistributorList = {
  items: Distributor[];
  total: number;
  page: number;
  page_size: number;
};

export type DistributorCreatePayload = {
  internal_code: string;
  corporate_name: string;
  trade_name: string;
  cnpj?: string | null;
  notes?: string | null;
  active?: boolean;
  confirm_duplicate?: boolean;
};

export type DistributorUpdatePayload = Partial<DistributorCreatePayload>;

export async function fetchDistributors(params: QueryParams = {}) {
  return apiFetch<DistributorList>(`/api/v1/distributors${buildQuery(params)}`);
}

export async function fetchDistributor(id: string) {
  return apiFetch<Distributor>(`/api/v1/distributors/${id}`);
}

export async function createDistributor(payload: DistributorCreatePayload) {
  return apiFetch<Distributor>("/api/v1/distributors", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDistributor(id: string, payload: DistributorUpdatePayload) {
  return apiFetch<Distributor>(`/api/v1/distributors/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateDistributor(id: string, reason: string) {
  return apiFetch<Distributor>(`/api/v1/distributors/${id}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reactivateDistributor(id: string) {
  return apiFetch<Distributor>(`/api/v1/distributors/${id}/reactivate`, { method: "POST" });
}

export async function fetchDistributorBases(distributorId: string, params: QueryParams = {}) {
  return apiFetch<DistributionBaseList>(`/api/v1/distributors/${distributorId}/bases${buildQuery(params)}`);
}

// --- Distribution Bases ---

export type DistributionBase = {
  id: string;
  organization_id: string;
  distributor_id: string;
  external_code: string | null;
  name: string;
  normalized_name: string;
  city: string;
  state: string;
  notes: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type DistributionBaseList = {
  items: DistributionBase[];
  total: number;
  page: number;
  page_size: number;
};

export type DistributionBaseCreatePayload = {
  distributor_id: string;
  name: string;
  city: string;
  state: string;
  external_code?: string | null;
  notes?: string | null;
  active?: boolean;
};

export type DistributionBaseUpdatePayload = Partial<DistributionBaseCreatePayload>;

export async function fetchDistributionBases(params: QueryParams = {}) {
  return apiFetch<DistributionBaseList>(`/api/v1/distribution-bases${buildQuery(params)}`);
}

export async function createDistributionBase(payload: DistributionBaseCreatePayload) {
  return apiFetch<DistributionBase>("/api/v1/distribution-bases", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateDistributionBase(id: string, payload: DistributionBaseUpdatePayload) {
  return apiFetch<DistributionBase>(`/api/v1/distribution-bases/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateDistributionBase(id: string, reason: string) {
  return apiFetch<DistributionBase>(`/api/v1/distribution-bases/${id}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reactivateDistributionBase(id: string) {
  return apiFetch<DistributionBase>(`/api/v1/distribution-bases/${id}/reactivate`, { method: "POST" });
}

// --- ERP Suppliers ---

export type ErpSupplier = {
  id: string;
  organization_id: string;
  station_id: string;
  erp_entity_id: string;
  erp_entity_code: string | null;
  erp_name: string;
  erp_cnpj: string | null;
  distributor_id: string | null;
  mapping_status: string;
  ignore_reason: string | null;
  mapped_by: string | null;
  mapped_at: string | null;
  last_synced_at: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type ErpSupplierList = {
  items: ErpSupplier[];
  total: number;
  page: number;
  page_size: number;
};

export async function fetchErpSuppliers(params: QueryParams = {}) {
  return apiFetch<ErpSupplierList>(`/api/v1/erp-suppliers${buildQuery(params)}`);
}

export async function mapErpSupplier(id: string, payload: { distributor_id: string; reason?: string }) {
  return apiFetch<ErpSupplier>(`/api/v1/erp-suppliers/${id}/map`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function ignoreErpSupplier(id: string, reason: string) {
  return apiFetch<ErpSupplier>(`/api/v1/erp-suppliers/${id}/ignore`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reopenErpSupplier(id: string, reason?: string) {
  return apiFetch<ErpSupplier>(`/api/v1/erp-suppliers/${id}/reopen`, {
    method: "POST",
    body: JSON.stringify({ reason: reason ?? null }),
  });
}

// --- Payment Terms ---

export type PaymentTerm = {
  id: string;
  organization_id: string;
  code: string;
  name: string;
  normalized_name: string;
  payment_type: string;
  days: number;
  description: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

export type PaymentTermList = {
  items: PaymentTerm[];
  total: number;
  page: number;
  page_size: number;
};

export type PaymentTermCreatePayload = {
  code: string;
  name: string;
  payment_type: string;
  days: number;
  description?: string | null;
  active?: boolean;
};

export type PaymentTermUpdatePayload = Partial<PaymentTermCreatePayload>;

export async function fetchPaymentTerms(params: QueryParams = {}) {
  return apiFetch<PaymentTermList>(`/api/v1/payment-terms${buildQuery(params)}`);
}

export async function createPaymentTerm(payload: PaymentTermCreatePayload) {
  return apiFetch<PaymentTerm>("/api/v1/payment-terms", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updatePaymentTerm(id: string, payload: PaymentTermUpdatePayload) {
  return apiFetch<PaymentTerm>(`/api/v1/payment-terms/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivatePaymentTerm(id: string, reason: string) {
  return apiFetch<PaymentTerm>(`/api/v1/payment-terms/${id}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function reactivatePaymentTerm(id: string) {
  return apiFetch<PaymentTerm>(`/api/v1/payment-terms/${id}/reactivate`, { method: "POST" });
}

// --- Supplier Rules ---

export type SupplierRule = {
  id: string;
  organization_id: string;
  station_id: string;
  distributor_id: string;
  product_id: string | null;
  distribution_base_id: string | null;
  allowed: boolean;
  minimum_volume_liters: string;
  valid_from: string;
  valid_until: string | null;
  contract_reference: string | null;
  reason: string | null;
  notes: string | null;
  priority: number;
  active: boolean;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type SupplierRuleList = {
  items: SupplierRule[];
  total: number;
  page: number;
  page_size: number;
};

export type SupplierRuleCreatePayload = {
  station_id: string;
  distributor_id: string;
  product_id?: string | null;
  distribution_base_id?: string | null;
  allowed?: boolean;
  minimum_volume_liters: string | number;
  valid_from: string;
  valid_until?: string | null;
  contract_reference?: string | null;
  reason?: string | null;
  notes?: string | null;
  priority?: number;
  active?: boolean;
};

export type SupplierRuleUpdatePayload = Partial<SupplierRuleCreatePayload>;

export type EffectiveRule = {
  allowed: boolean;
  minimum_volume_liters: string;
  rule_source: string;
  rule_id: string | null;
  distribution_base_id?: string | null;
  valid_from: string | null;
  valid_until: string | null;
  reason: string | null;
};

export async function fetchSupplierRules(params: QueryParams = {}) {
  return apiFetch<SupplierRuleList>(`/api/v1/station-supplier-rules${buildQuery(params)}`);
}

export async function fetchEffectiveSupplierRule(params: {
  station_id: string;
  distributor_id: string;
  product_id: string;
  reference_date?: string;
}) {
  return apiFetch<EffectiveRule>(`/api/v1/station-supplier-rules/effective${buildQuery(params)}`);
}

export async function createSupplierRule(payload: SupplierRuleCreatePayload) {
  return apiFetch<SupplierRule>("/api/v1/station-supplier-rules", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function updateSupplierRule(id: string, payload: SupplierRuleUpdatePayload) {
  return apiFetch<SupplierRule>(`/api/v1/station-supplier-rules/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export async function deactivateSupplierRule(id: string, reason: string) {
  return apiFetch<SupplierRule>(`/api/v1/station-supplier-rules/${id}/deactivate`, {
    method: "POST",
    body: JSON.stringify({ reason }),
  });
}

export async function closeSupplierRuleValidity(id: string, payload: { valid_until: string; reason?: string }) {
  return apiFetch<SupplierRule>(`/api/v1/station-supplier-rules/${id}/close-validity`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// --- Master Data Imports ---

export type MasterDataImportRow = {
  id: string;
  import_job_id: string;
  row_number: number;
  external_identifier: string | null;
  action: string;
  status: string;
  raw_data: Record<string, unknown>;
  normalized_data: Record<string, unknown> | null;
  validation_errors: Record<string, unknown> | null;
  processed_at: string | null;
};

export type MasterDataImportJob = {
  id: string;
  organization_id: string;
  station_id: string | null;
  import_type: string;
  source_file_name: string;
  source_file_hash: string;
  status: string;
  records_total: number;
  records_valid: number;
  records_inserted: number;
  records_updated: number;
  records_unchanged: number;
  records_failed: number;
  error_summary: Record<string, unknown> | null;
  created_by: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type MasterDataImportJobDetail = MasterDataImportJob & {
  rows: MasterDataImportRow[];
};

export type MasterDataImportJobList = {
  items: MasterDataImportJob[];
  total: number;
  page: number;
  page_size: number;
};

export async function fetchImportJobs(params: QueryParams = {}) {
  return apiFetch<MasterDataImportJobList>(`/api/v1/master-data-imports${buildQuery(params)}`);
}

export async function fetchImportJob(id: string) {
  return apiFetch<MasterDataImportJobDetail>(`/api/v1/master-data-imports/${id}`);
}

export async function uploadErpProductsImport(stationId: string, file: File) {
  const formData = new FormData();
  formData.append("station_id", stationId);
  formData.append("file", file);
  return apiUpload<MasterDataImportJobDetail>("/api/v1/master-data-imports/erp-products", formData);
}

export async function uploadErpSuppliersImport(stationId: string, file: File) {
  const formData = new FormData();
  formData.append("station_id", stationId);
  formData.append("file", file);
  return apiUpload<MasterDataImportJobDetail>("/api/v1/master-data-imports/erp-suppliers", formData);
}

export async function confirmImportJob(id: string) {
  return apiFetch<MasterDataImportJob>(`/api/v1/master-data-imports/${id}/confirm`, { method: "POST" });
}

export async function cancelImportJob(id: string) {
  return apiFetch<MasterDataImportJob>(`/api/v1/master-data-imports/${id}/cancel`, { method: "POST" });
}

// --- Labels ---

export const MAPPING_STATUS_LABELS: Record<string, string> = {
  PENDING: "Pendente",
  MAPPED: "Mapeado",
  IGNORED: "Ignorado",
  CONFLICT: "Conflito",
};

export const PAYMENT_TYPE_LABELS: Record<string, string> = {
  CASH: "À vista",
  TERM: "Prazo",
  ANTICIPATED: "Antecipado",
};

export const RULE_SOURCE_LABELS: Record<string, string> = {
  PRODUCT_SPECIFIC: "Produto específico",
  DISTRIBUTOR_GENERAL: "Distribuidor geral",
  ORGANIZATION_DEFAULT: "Padrão da organização",
  NO_RULE: "Sem regra",
};

export const IMPORT_STATUS_LABELS: Record<string, string> = {
  UPLOADED: "Enviado",
  VALIDATING: "Validando",
  READY: "Pronto",
  PROCESSING: "Processando",
  SUCCESS: "Sucesso",
  PARTIAL: "Parcial",
  FAILED: "Falhou",
  CANCELLED: "Cancelado",
};
