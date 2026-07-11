import { useQuery } from "@tanstack/react-query";
import { fetchFuelSalesPriceVariance, fetchFuelSalesFreshness, fetchFuelSalesRetailPrices } from "../api/fuel-sales-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useMemo, useState } from "react";

function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return { date_from: from.toISOString().slice(0, 10), date_to: to.toISOString().slice(0, 10) };
}

export function FuelPricesPage() {
  const [range] = useState(defaultDateRange);
  const pricesQuery = useQuery({
    queryKey: ["fuel-sales-retail-prices"],
    queryFn: () => fetchFuelSalesRetailPrices(),
  });
  const varianceQuery = useQuery({
    queryKey: ["fuel-sales-price-variance", range],
    queryFn: () => fetchFuelSalesPriceVariance(range),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-sales-freshness"],
    queryFn: fetchFuelSalesFreshness,
  });

  const prices = pricesQuery.data ?? [];
  const variance = varianceQuery.data ?? [];
  const topVariance = useMemo(() => variance.slice(0, 20), [variance]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Preços de combustíveis</h1>
      <p className="text-sm text-amber-800">
        Mapeamento VALOR1–4 → FORMAPGTO é <strong>provisório</strong> (`LEGACY_REFERENCE`). Indicadores por forma de
        pagamento não estão homologados até confirmação do DBA.
      </p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Preços cadastrados atuais</h2>
        {pricesQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : prices.length === 0 ? (
          <p className="text-sm text-slate-500">Sem snapshots. Execute a sincronização FUEL_RETAIL_PRICES.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Posto</th>
                  <th className="py-2 pr-4">Produto</th>
                  <th className="py-2 pr-4">Forma pagamento</th>
                  <th className="py-2 pr-4">Preço/L</th>
                  <th className="py-2 pr-4">Observado em</th>
                </tr>
              </thead>
              <tbody>
                {prices.map((row, index) => (
                  <tr key={`${row.station_id}-${row.product_id}-${row.payment_method_group}-${index}`} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.station_name}</td>
                    <td className="py-2 pr-4">{row.product_name}</td>
                    <td className="py-2 pr-4">{row.payment_method_name ?? row.payment_method_group ?? "—"}</td>
                    <td className="py-2 pr-4">{row.price_per_liter}</td>
                    <td className="py-2 pr-4">{row.observed_at.slice(0, 16).replace("T", " ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Variação preço realizado vs cadastrado (30 dias)</h2>
        {varianceQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : topVariance.length === 0 ? (
          <p className="text-sm text-slate-500">Sem dados comparáveis no período.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Produto</th>
                  <th className="py-2 pr-4">Forma</th>
                  <th className="py-2 pr-4">Realizado</th>
                  <th className="py-2 pr-4">Cadastrado</th>
                  <th className="py-2 pr-4">Δ/L</th>
                  <th className="py-2 pr-4">Δ%</th>
                </tr>
              </thead>
              <tbody>
                {topVariance.map((row) => (
                  <tr key={`${row.product_id}-${row.payment_method_group}`} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.product_name}</td>
                    <td className="py-2 pr-4">{row.payment_method_group ?? "—"}</td>
                    <td className="py-2 pr-4">{row.realized_price_per_liter ?? "—"}</td>
                    <td className="py-2 pr-4">{row.registered_price_per_liter ?? "—"}</td>
                    <td className="py-2 pr-4">{row.variance_per_liter ?? "—"}</td>
                    <td className="py-2 pr-4">{row.variance_percent ? `${row.variance_percent}%` : "—"}</td>
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
