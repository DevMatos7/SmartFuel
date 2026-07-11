import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { fetchFuelPurchasesDataQuality, fetchFuelPurchasesFreshness } from "../api/fuel-purchases-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";

function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return { date_from: from.toISOString().slice(0, 10), date_to: to.toISOString().slice(0, 10) };
}

export function PurchaseDataQualityPage() {
  const [range] = useState(defaultDateRange);

  const qualityQuery = useQuery({
    queryKey: ["fuel-purchases-quality", range],
    queryFn: () => fetchFuelPurchasesDataQuality(range),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-purchases-freshness"],
    queryFn: fetchFuelPurchasesFreshness,
  });

  const q = qualityQuery.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Qualidade dos dados — compras</h1>
        <p className="text-sm text-slate-600">
          Itens sem mapeamento, custo ausente, XML pendente e divergências ERP × XML.
        </p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Itens sem produto mapeado" value={q?.unmapped_item_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Volume sem mapeamento (L)" value={q?.unmapped_volume_liters ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Fornecedores sem mapeamento" value={q?.unmapped_supplier_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Itens sem custo" value={q?.missing_cost_item_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Notas sem XML" value={q?.missing_xml_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Divergências ERP × XML" value={q?.xml_mismatch_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Chaves de acesso inválidas" value={q?.invalid_access_key_count ?? "—"} loading={qualityQuery.isLoading} />
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
