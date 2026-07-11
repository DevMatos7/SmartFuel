import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchFuelPurchasesByDistributor,
  fetchFuelPurchasesByProduct,
  fetchFuelPurchasesFreshness,
  fetchFuelPurchasesSummary,
  fetchFuelPurchasesTrend,
  type FuelPurchasesByDistributorRow,
  type FuelPurchasesByProductRow,
  type FuelPurchasesTrendPoint,
} from "../api/fuel-purchases-analytics";
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

export function FuelPurchasesDashboardPage() {
  const { hasPermission } = useAuth();
  const canViewCost = hasPermission("fuel_purchases.view_cost");
  const canViewInvoices = hasPermission("purchase_invoices.read");
  const [range] = useState(defaultDateRange);

  const summaryQuery = useQuery({
    queryKey: ["fuel-purchases-summary", range],
    queryFn: () => fetchFuelPurchasesSummary(range),
  });
  const trendQuery = useQuery({
    queryKey: ["fuel-purchases-trend", range],
    queryFn: () => fetchFuelPurchasesTrend(range),
  });
  const byProductQuery = useQuery({
    queryKey: ["fuel-purchases-by-product", range],
    queryFn: () => fetchFuelPurchasesByProduct(range),
  });
  const byDistributorQuery = useQuery({
    queryKey: ["fuel-purchases-by-distributor", range],
    queryFn: () => fetchFuelPurchasesByDistributor(range),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-purchases-freshness"],
    queryFn: fetchFuelPurchasesFreshness,
  });

  const summary = summaryQuery.data;
  const trend = trendQuery.data ?? [];
  const products = byProductQuery.data ?? [];
  const distributors = byDistributorQuery.data ?? [];
  const maxVolume = useMemo(
    () => Math.max(...trend.map((p: FuelPurchasesTrendPoint) => Number(p.purchased_volume_liters)), 1),
    [trend],
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Compras de combustíveis</h1>
          <p className="text-sm text-slate-600">Volume adquirido, custo entregue e compromissos financeiros.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {canViewInvoices && (
            <Link
              to="/analytics/fuel-purchases/invoices"
              className="rounded border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
            >
              Notas fiscais
            </Link>
          )}
          {canViewCost && (
            <Link
              to="/analytics/fuel-purchases/costs"
              className="rounded border border-slate-300 px-3 py-2 text-sm hover:bg-slate-50"
            >
              Custos
            </Link>
          )}
        </div>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />
      {freshnessQuery.data && (
        <p className="text-xs text-slate-500">Freshness: {freshnessQuery.data.status}</p>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Volume comprado (L)" value={summary?.purchased_volume_liters ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Valor total das compras" value={summary?.gross_purchase_amount ?? "—"} loading={summaryQuery.isLoading} />
        <Card
          label="Custo entregue / L"
          value={canViewCost ? (summary?.average_delivered_cost_per_liter ?? "Indisponível") : "Restrito"}
          loading={summaryQuery.isLoading}
        />
        <Card label="Frete total" value={summary?.total_freight_amount ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Descontos" value={summary?.total_discount_amount ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Notas fiscais" value={summary?.invoice_count?.toString() ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Prazo médio (dias)" value={summary?.weighted_term_days ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Saldo a pagar" value={summary?.open_payable_amount ?? "—"} loading={summaryQuery.isLoading} />
        {canViewCost && (
          <Card
            label="Custo entregue total"
            value={summary?.commercial_delivered_cost ?? "Indisponível"}
            loading={summaryQuery.isLoading}
          />
        )}
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Evolução diária de volume</h2>
        {trendQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : trend.length === 0 ? (
          <p className="text-sm text-slate-500">Sem dados no período. Execute a sincronização FUEL_PURCHASE_INVOICES.</p>
        ) : (
          <div className="flex h-40 items-end gap-1">
            {trend.map((point: FuelPurchasesTrendPoint) => (
              <div key={point.business_date} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className="w-full rounded bg-emerald-500"
                  style={{
                    height: `${(Number(point.purchased_volume_liters) / maxVolume) * 100}%`,
                    minHeight: "4px",
                  }}
                  title={`${point.business_date}: ${point.purchased_volume_liters} L`}
                />
                <span className="text-[10px] text-slate-500">{point.business_date.slice(5)}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Por produto</h2>
        {byProductQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : products.length === 0 ? (
          <p className="text-sm text-slate-500">Sem compras elegíveis no período.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Produto</th>
                  <th className="py-2 pr-4">Volume</th>
                  <th className="py-2 pr-4">Valor</th>
                  {canViewCost && <th className="py-2 pr-4">Custo/L</th>}
                </tr>
              </thead>
              <tbody>
                {products.map((row: FuelPurchasesByProductRow) => (
                  <tr key={row.product_id ?? row.product_name} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.product_name}</td>
                    <td className="py-2 pr-4">{row.purchased_volume_liters}</td>
                    <td className="py-2 pr-4">{row.gross_purchase_amount}</td>
                    {canViewCost && (
                      <td className="py-2 pr-4">{row.average_delivered_cost_per_liter ?? "—"}</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Por distribuidora</h2>
        {byDistributorQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : distributors.length === 0 ? (
          <p className="text-sm text-slate-500">Sem compras por distribuidora no período.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Distribuidora</th>
                  <th className="py-2 pr-4">Notas</th>
                  <th className="py-2 pr-4">Volume</th>
                  <th className="py-2 pr-4">Valor</th>
                  {canViewCost && <th className="py-2 pr-4">Custo/L</th>}
                </tr>
              </thead>
              <tbody>
                {distributors.map((row: FuelPurchasesByDistributorRow) => (
                  <tr key={row.distributor_id ?? row.distributor_name} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.distributor_name}</td>
                    <td className="py-2 pr-4">{row.invoice_count}</td>
                    <td className="py-2 pr-4">{row.purchased_volume_liters}</td>
                    <td className="py-2 pr-4">{row.gross_purchase_amount}</td>
                    {canViewCost && (
                      <td className="py-2 pr-4">{row.average_delivered_cost_per_liter ?? "—"}</td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
