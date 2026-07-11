export type FuelPurchasesSummary = {
  purchased_volume_liters: string;
  gross_purchase_amount: string;
  commercial_delivered_cost: string;
  average_delivered_cost_per_liter: string | null;
  total_freight_amount: string;
  total_discount_amount: string;
  invoice_count: number;
  weighted_term_days: string | null;
  open_payable_amount: string | null;
  erp_recorded_cost?: string | null;
};

export type FuelPurchasesTrendPoint = {
  business_date: string;
  purchased_volume_liters: string;
  gross_purchase_amount: string;
  commercial_delivered_cost: string;
  average_delivered_cost_per_liter: string | null;
  freight_amount: string;
};

export type FuelPurchasesByProductRow = {
  product_id: string | null;
  product_name: string;
  purchased_volume_liters: string;
  gross_purchase_amount: string;
  commercial_delivered_cost: string;
  average_delivered_cost_per_liter: string | null;
};

export type FuelPurchasesByDistributorRow = {
  distributor_id: string | null;
  distributor_name: string;
  purchased_volume_liters: string;
  gross_purchase_amount: string;
  commercial_delivered_cost: string;
  average_delivered_cost_per_liter: string | null;
  invoice_count: number;
};

export type FuelPurchasesCosts = {
  purchased_volume_liters: string;
  gross_purchase_amount: string;
  discount_amount: string;
  freight_amount: string;
  insurance_amount: string;
  other_expenses_amount: string;
  commercial_delivered_cost: string;
  erp_recorded_cost: string | null;
  average_delivered_cost_per_liter: string | null;
  invoice_count: number;
  item_count: number;
};

export type FuelPurchasesDataQuality = {
  unmapped_item_count: number;
  unmapped_volume_liters: string;
  unmapped_supplier_count: number;
  missing_cost_item_count: number;
  missing_xml_count: number;
  xml_mismatch_count: number;
  invalid_access_key_count: number;
  quarantined_item_count: number;
};

export type FuelPurchasesFreshness = {
  status: string;
  security_status?: string | null;
  last_completed_run_at?: string | null;
};

export type FuelPurchaseInvoiceListRow = {
  id: string;
  station_id: string;
  station_name: string;
  source_document_number: string;
  source_series: string | null;
  access_key: string | null;
  entry_date: string;
  issue_date: string;
  distributor_name: string | null;
  purchased_volume_liters: string;
  total_amount: string;
  delivered_cost_per_liter: string | null;
  has_xml: boolean; // arquivo em nfe_xml_documents / MinIO
  xml_imported_in_erp: boolean; // flag IMPORTOU_XML do ERP
  xml_reconciliation_status: string | null;
  metric_eligibility_status: string;
  is_cancelled: boolean;
};

export type PaginatedResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type FuelPurchaseInvoiceDetail = {
  id: string;
  station_id: string;
  station_name: string;
  source_invoice_id: string;
  source_document_number: string;
  source_series: string | null;
  access_key: string | null;
  xml_imported_in_erp: boolean;
  has_xml_file: boolean;
  distributor_id: string | null;
  distributor_name: string | null;
  source_supplier_id: string;
  issue_date: string;
  entry_date: string;
  operation_type: string;
  source_status: string;
  is_cancelled: boolean;
  gross_amount: string;
  discount_amount: string;
  freight_amount: string;
  insurance_amount: string;
  other_expenses_amount: string;
  tax_amount: string;
  total_amount: string;
  purchased_volume_liters: string;
  commercial_delivered_cost: string;
  average_delivered_cost_per_liter: string | null;
  allocation_method: string | null;
  metric_eligibility_status: string;
  metric_exclusion_reasons: string[] | null;
  payment_condition_id: string | null;
};

export type FuelPurchaseInvoiceItem = {
  id: string;
  source_description: string | null;
  product_name: string | null;
  source_product_id: string;
  volume_liters: string | null;
  source_quantity: string;
  source_unit: string | null;
  unit_price: string;
  gross_item_amount: string;
  discount_amount: string;
  allocated_freight_amount: string;
  allocated_insurance_amount: string;
  allocated_other_expenses: string;
  commercial_delivered_cost: string;
  delivered_cost_per_liter: string | null;
  erp_recorded_cost: string | null;
  accounting_cost: string | null;
  icms_amount: string | null;
  icms_st_amount: string | null;
  fcp_amount: string | null;
  pis_amount: string | null;
  cofins_amount: string | null;
  cfop: string | null;
  ncm: string | null;
  metric_eligibility_status: string;
  metric_exclusion_reasons: string[] | null;
};

export type FuelPurchaseInvoiceXml = {
  id: string | null;
  access_key: string | null;
  parse_status: string | null;
  reconciliation_status: string | null;
  reconciliation_details: Record<string, unknown> | null;
  xml_size_bytes: number | null;
  imported_at: string | null;
};

export type FuelPurchaseInvoiceTitle = {
  id: string;
  installment_number: number | null;
  document_number: string | null;
  due_date: string;
  payment_date: string | null;
  original_amount: string;
  paid_amount: string | null;
  open_amount: string;
  normalized_status: string;
  source_status: string;
};

export type AccountsPayableSummary = {
  open_amount: string;
  overdue_amount: string;
  due_in_7_days_amount: string;
  due_in_30_days_amount: string;
  weighted_term_days: string | null;
  partially_paid_count: number;
  open_title_count: number;
};

export type AccountsPayableAgingBucket = {
  bucket: string;
  title_count: number;
  open_amount: string;
};

export type AccountsPayableTitleRow = {
  id: string;
  station_id: string;
  station_name: string;
  distributor_name: string | null;
  document_number: string | null;
  installment_number: number | null;
  due_date: string;
  payment_date: string | null;
  original_amount: string;
  paid_amount: string | null;
  open_amount: string;
  normalized_status: string;
  purchase_invoice_id: string | null;
};

export type NfeDocumentRow = {
  id: string;
  station_id: string;
  station_name: string;
  access_key: string;
  document_number: string;
  series: string;
  issuer_cnpj: string;
  issue_datetime: string;
  total_amount: string;
  parse_status: string;
  reconciliation_status: string;
  purchase_invoice_id: string | null;
  xml_size_bytes: number;
};

export type NfeDocumentDetail = NfeDocumentRow & {
  recipient_cnpj: string;
  parse_errors: unknown;
  reconciliation_details: Record<string, unknown> | null;
  imported_at: string;
};
