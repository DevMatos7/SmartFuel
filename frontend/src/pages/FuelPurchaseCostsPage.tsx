import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchFuelPurchasesCosts,
  fetchFuelPurchasesFreshness,
  type DateRange,
} from "../api/fuel-purchases-analytics";
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

export function FuelPurchaseCostsPage() {
  const { hasPermission } = useAuth();
  const canView = hasPermission("fuel_purchases.view_cost");
  const [range] = useState(defaultDateRange);

  const costsQuery = useQuery({
    queryKey: ["fuel-purchases-costs", range],
    queryFn: () => fetchFuelPurchasesCosts(range),
    enabled: canView,
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-purchases-freshness"],
    queryFn: fetchFuelPurchasesFreshness,
  });

  if (!canView) {
    return <p className="text-sm text-slate-600">Você não possui permissão para visualizar custos de aquisição.</p>;
  }

  const costs = costsQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/analytics/fuel-purchases" className="text-sm text-slate-500 underline">
          Voltar ao dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Custos de aquisição</h1>
        <p className="text-sm text-slate-600">
          Custo comercial entregue com frete, despesas e tributos preservados separadamente.
        </p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Volume (L)" value={costs?.purchased_volume_liters ?? "—"} loading={costsQuery.isLoading} />
        <Card label="Valor bruto" value={costs?.gross_purchase_amount ?? "—"} loading={costsQuery.isLoading} />
        <Card label="Descontos" value={costs?.discount_amount ?? "—"} loading={costsQuery.isLoading} />
        <Card label="Frete" value={costs?.freight_amount ?? "—"} loading={costsQuery.isLoading} />
        <Card label="Seguro" value={costs?.insurance_amount ?? "—"} loading={costsQuery.isLoading} />
        <Card label="Outras despesas" value={costs?.other_expenses_amount ?? "—"} loading={costsQuery.isLoading} />
        <Card label="Custo entregue" value={costs?.commercial_delivered_cost ?? "Indisponível"} loading={costsQuery.isLoading} />
        <Card label="Custo/L" value={costs?.average_delivered_cost_per_liter ?? "Indisponível"} loading={costsQuery.isLoading} />
        <Card label="Custo ERP" value={costs?.erp_recorded_cost ?? "Indisponível"} loading={costsQuery.isLoading} />
        <Card label="Notas" value={costs?.invoice_count?.toString() ?? "—"} loading={costsQuery.isLoading} />
        <Card label="Itens" value={costs?.item_count?.toString() ?? "—"} loading={costsQuery.isLoading} />
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
