import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchFuelSalesDataQuality, fetchFuelSalesFreshness } from "../api/fuel-sales-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";

function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return { date_from: from.toISOString().slice(0, 10), date_to: to.toISOString().slice(0, 10) };
}

export function FuelSalesDataQualityPage() {
  const [range] = useState(defaultDateRange);
  const qualityQuery = useQuery({
    queryKey: ["fuel-sales-quality", range],
    queryFn: () => fetchFuelSalesDataQuality(range),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-sales-freshness"],
    queryFn: fetchFuelSalesFreshness,
  });
  const q = qualityQuery.data as
    | {
        unmapped_item_count: number;
        unmapped_volume_liters: string;
        missing_cost_item_count: number;
        missing_cost_volume_liters: string;
        quarantined_item_count: number;
        pending_payment_methods: number;
      }
    | undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Qualidade dos dados — vendas</h1>
        <p className="text-sm text-slate-600">Itens sem mapeamento, sem custo e formas de pagamento pendentes.</p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MetricCard label="Vendas sem produto mapeado" value={q?.unmapped_item_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Volume sem mapeamento (L)" value={q?.unmapped_volume_liters ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Vendas sem custo" value={q?.missing_cost_item_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Volume sem custo (L)" value={q?.missing_cost_volume_liters ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Métodos de pagamento pendentes" value={q?.pending_payment_methods ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Linhas excluídas" value={q?.quarantined_item_count ?? "—"} loading={qualityQuery.isLoading} />
      </div>
    </div>
  );
}

function MetricCard({ label, value, loading }: { label: string; value: string | number; loading: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold">{loading ? "..." : value}</p>
    </div>
  );
}
