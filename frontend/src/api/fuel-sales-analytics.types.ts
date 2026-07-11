export type FuelSalesSummary = {
  net_volume_liters: string;
  net_sales_amount: string;
  realized_price_per_liter: string | null;
  cost_coverage_percent: string | null;
  item_count: number;
  gross_margin_amount?: string | null;
  gross_margin_per_liter?: string | null;
  gross_margin_percent?: string | null;
};

export type FuelSalesMargins = {
  total_cost_amount: string | null;
  gross_margin_amount: string | null;
  gross_margin_per_liter: string | null;
  gross_margin_percent: string | null;
  cost_coverage_percent: string | null;
};

export type FuelSalesTrendPoint = {
  business_date: string;
  net_volume_liters: string;
  net_sales_amount: string;
  realized_price_per_liter: string | null;
};

export type FuelSalesByProductRow = {
  product_id: string;
  product_name: string;
  net_volume_liters: string;
  net_sales_amount: string;
  realized_price_per_liter: string | null;
  gross_margin_per_liter?: string | null;
};

export type FuelSalesFreshness = {
  status: string;
  security_status?: string | null;
  last_completed_run_at?: string | null;
};

export type FuelSalesUnmappedRow = {
  erp_product_id: string;
  erp_product_code: string | null;
  erp_description: string;
  item_count: number;
  volume_liters: string;
  net_amount: string;
};

export type FuelSalesPriceVarianceRow = {
  product_id: string;
  product_name: string;
  payment_method_group: string | null;
  net_volume_liters: string;
  realized_price_per_liter: string | null;
  registered_price_per_liter: string | null;
  variance_per_liter: string | null;
  variance_percent: string | null;
};

export type FuelSalesRetailPriceRow = {
  station_id: string;
  station_name: string;
  product_id: string | null;
  product_name: string;
  payment_method_group: string | null;
  payment_method_name: string | null;
  price_per_liter: string;
  observed_at: string;
};

export type ReconcileMappingsResponse = {
  runs: Array<{
    id: string;
    status: string;
    erp_product_id: string | null;
    affected_facts: number;
    affected_dates: number;
    error_message: string | null;
  }>;
};
