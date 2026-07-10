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
