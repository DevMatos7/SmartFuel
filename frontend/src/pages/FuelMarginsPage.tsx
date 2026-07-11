import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  fetchFuelSalesMargins,
  fetchFuelSalesFreshness,
  fetchFuelSalesSummary,
  type DateRange,
} from "../api/fuel-sales-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

function defaultDateRange(): DateRange {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return {
    date_from: from.toISOString().slice(0, 10),
    date_to: to.toISOString().slice(0, 10),
  };
}

export function FuelMarginsPage() {
  const { hasPermission } = useAuth();
  const canView = hasPermission("fuel_sales_analytics.view_margin");
  const [range] = useState(defaultDateRange);

  const summaryQuery = useQuery({
    queryKey: ["fuel-sales-margins-summary", range],
    queryFn: () => fetchFuelSalesSummary(range),
    enabled: canView,
  });
  const marginsQuery = useQuery({
    queryKey: ["fuel-sales-margins", range],
    queryFn: () => fetchFuelSalesMargins(range),
    enabled: canView,
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-sales-freshness"],
    queryFn: fetchFuelSalesFreshness,
  });

  if (!canView) {
    return <p className="text-sm text-slate-600">Você não possui permissão para visualizar margens.</p>;
  }

  const margins = marginsQuery.data;
  const summary = summaryQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Margens de combustíveis</h1>
        <p className="text-sm text-slate-600">
          Margem bruta calculada com custo registrado no ERP. Ausência de custo não é tratada como zero.
        </p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Custo total" value={margins?.total_cost_amount ?? "Indisponível"} loading={marginsQuery.isLoading} />
        <Card label="Margem bruta" value={margins?.gross_margin_amount ?? "Indisponível"} loading={marginsQuery.isLoading} />
        <Card label="Margem / L" value={margins?.gross_margin_per_liter ?? "Indisponível"} loading={marginsQuery.isLoading} />
        <Card label="Margem %" value={margins?.gross_margin_percent ? `${margins.gross_margin_percent}%` : "Indisponível"} loading={marginsQuery.isLoading} />
        <Card label="Cobertura de custo" value={margins?.cost_coverage_percent ? `${margins.cost_coverage_percent}%` : "—"} loading={marginsQuery.isLoading} />
        <Card label="Volume (L)" value={summary?.net_volume_liters ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Faturamento" value={summary?.net_sales_amount ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Itens" value={summary?.item_count?.toString() ?? "—"} loading={summaryQuery.isLoading} />
      </div>
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
