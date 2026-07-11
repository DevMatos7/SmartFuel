import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchBenchmarkOpportunities } from "../api/purchase-benchmarks";
import { useAuth } from "../auth/AuthProvider";

export function PurchaseBenchmarkOpportunitiesPage() {
  const { hasPermission } = useAuth();
  const can = hasPermission("purchase_benchmarks.view_opportunity");
  const q = useQuery({
    queryKey: ["pb-opp-page"],
    queryFn: () => fetchBenchmarkOpportunities(),
    enabled: can,
  });

  if (!can) {
    return <p className="text-sm text-rose-600">Sem permissão para ver oportunidades.</p>;
  }

  return (
    <div className="space-y-4">
      <div>
        <Link to="/analytics/purchase-benchmarks" className="text-sm underline text-slate-500">
          Voltar
        </Link>
        <h1 className="mt-2 text-xl font-semibold">Oportunidades de compra</h1>
        <p className="text-sm text-slate-600">Diferença frente à melhor cotação historicamente elegível.</p>
      </div>
      {q.isLoading ? (
        <p className="text-sm text-slate-500">Carregando…</p>
      ) : (
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b text-left text-slate-500">
              <th className="py-2 pr-4">Nota</th>
              <th className="py-2 pr-4">Volume</th>
              <th className="py-2 pr-4">Diferença/L</th>
              <th className="py-2 pr-4">Oportunidade</th>
              <th className="py-2 pr-4">Resultado</th>
            </tr>
          </thead>
          <tbody>
            {(q.data ?? []).map((row) => (
              <tr key={row.benchmark_item_id} className="border-b">
                <td className="py-2 pr-4">
                  <Link className="underline" to={`/analytics/fuel-purchases/invoices/${row.purchase_invoice_id}`}>
                    {row.purchase_invoice_id.slice(0, 8)}…
                  </Link>
                </td>
                <td className="py-2 pr-4">{row.volume_liters}</td>
                <td className="py-2 pr-4">{row.cost_variance_per_liter ?? "—"}</td>
                <td className="py-2 pr-4">{row.opportunity_amount ?? "—"}</td>
                <td className="py-2 pr-4">{row.decision_result}</td>
              </tr>
            ))}
            {!q.data?.length && (
              <tr>
                <td colSpan={5} className="py-4 text-slate-500">
                  Sem oportunidades.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      )}
    </div>
  );
}
