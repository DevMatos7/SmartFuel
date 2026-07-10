import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { fetchFuelSalesByProduct, fetchFuelSalesFreshness, fetchFuelSalesSummary, fetchFuelSalesTrend, type FuelSalesByProductRow, type FuelSalesTrendPoint } from "../api/fuel-sales-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return {
    date_from: from.toISOString().slice(0, 10),
    date_to: to.toISOString().slice(0, 10),
  };
}

export function FuelSalesDashboardPage() {
  const { hasPermission } = useAuth();
  const canViewMargin = hasPermission("fuel_sales_analytics.view_margin");
  const [range] = useState(defaultDateRange);

  const summaryQuery = useQuery({
    queryKey: ["fuel-sales-summary", range],
    queryFn: () => fetchFuelSalesSummary(range),
  });
  const trendQuery = useQuery({
    queryKey: ["fuel-sales-trend", range],
    queryFn: () => fetchFuelSalesTrend(range),
  });
  const byProductQuery = useQuery({
    queryKey: ["fuel-sales-by-product", range],
    queryFn: () => fetchFuelSalesByProduct(range),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-sales-freshness"],
    queryFn: fetchFuelSalesFreshness,
  });

  const summary = summaryQuery.data;
  const trend = trendQuery.data ?? [];
  const products = byProductQuery.data ?? [];
  const maxVolume = useMemo(
    () => Math.max(...trend.map((p: FuelSalesTrendPoint) => Number(p.net_volume_liters)), 1),
    [trend],
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Vendas de combustíveis</h1>
        <p className="text-sm text-slate-600">Volume, faturamento e margem bruta baseada no custo do ERP.</p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />
      {freshnessQuery.data && (
        <p className="text-xs text-slate-500">Freshness: {freshnessQuery.data.status}</p>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Volume vendido (L)" value={summary?.net_volume_liters ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Faturamento líquido" value={summary?.net_sales_amount ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Preço médio realizado" value={summary?.realized_price_per_liter ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Cobertura de custo" value={summary?.cost_coverage_percent ? `${summary.cost_coverage_percent}%` : "—"} loading={summaryQuery.isLoading} />
        {canViewMargin && (
          <>
            <Card label="Margem bruta" value={summary?.gross_margin_amount ?? "Indisponível"} loading={summaryQuery.isLoading} />
            <Card label="Margem / L" value={summary?.gross_margin_per_liter ?? "Indisponível"} loading={summaryQuery.isLoading} />
            <Card label="Margem %" value={summary?.gross_margin_percent ? `${summary.gross_margin_percent}%` : "Indisponível"} loading={summaryQuery.isLoading} />
          </>
        )}
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Evolução diária de volume</h2>
        {trendQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : trend.length === 0 ? (
          <p className="text-sm text-slate-500">Sem dados no período. Execute a sincronização FUEL_SALES_ITEMS.</p>
        ) : (
          <div className="flex h-40 items-end gap-1">
            {trend.map((point: FuelSalesTrendPoint) => (
              <div key={point.business_date} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded bg-sky-500"
                  style={{ height: `${(Number(point.net_volume_liters) / maxVolume) * 100}%`, minHeight: "4px" }}
                  title={`${point.business_date}: ${point.net_volume_liters} L`}
                />
                <span className="text-[10px] text-slate-500">{point.business_date.slice(5)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Por produto</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2 pr-4">Produto</th>
                <th className="py-2 pr-4">Volume</th>
                <th className="py-2 pr-4">Receita</th>
                <th className="py-2 pr-4">Preço médio</th>
                {canViewMargin && <th className="py-2 pr-4">Margem/L</th>}
              </tr>
            </thead>
            <tbody>
              {products.map((row: FuelSalesByProductRow) => (
                <tr key={row.product_id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{row.product_name}</td>
                  <td className="py-2 pr-4">{row.net_volume_liters}</td>
                  <td className="py-2 pr-4">{row.net_sales_amount}</td>
                  <td className="py-2 pr-4">{row.realized_price_per_liter ?? "—"}</td>
                  {canViewMargin && <td className="py-2 pr-4">{row.gross_margin_per_liter ?? "—"}</td>}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Card({ label, value, loading }: { label: string; value: string; loading: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-900">{loading ? "..." : value}</p>
    </div>
  );
}
