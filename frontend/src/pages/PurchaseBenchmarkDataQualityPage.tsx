import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchBenchmarkDataQuality } from "../api/purchase-benchmarks";

export function PurchaseBenchmarkDataQualityPage() {
  const q = useQuery({
    queryKey: ["pb-quality-page"],
    queryFn: () => fetchBenchmarkDataQuality(),
  });
  const d = q.data;

  return (
    <div className="space-y-4">
      <div>
        <Link to="/analytics/purchase-benchmarks" className="text-sm underline text-slate-500">
          Voltar
        </Link>
        <h1 className="mt-2 text-xl font-semibold">Qualidade — compra × cotação</h1>
      </div>
      {q.isLoading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : (
        <ul className="space-y-2 text-sm">
          <li>Sem produto mapeado: {d?.unmapped_product_count ?? 0}</li>
          <li>Fornecedor não mapeado (aviso): {d?.unmapped_supplier_warning_count ?? 0}</li>
          <li>Sem custo entregue: {d?.missing_cost_count ?? 0}</li>
          <li>Sem volume: {d?.missing_volume_count ?? 0}</li>
          <li>Sem referência temporal: {d?.reference_unavailable_count ?? 0}</li>
          <li>Sem cotação: {d?.no_quotes_count ?? 0}</li>
          <li>Sem elegível: {d?.no_eligible_count ?? 0}</li>
          <li>Não comparável: {d?.not_comparable_count ?? 0}</li>
          <li>Referência baixa confiança: {d?.low_confidence_count ?? 0}</li>
        </ul>
      )}
    </div>
  );
}
