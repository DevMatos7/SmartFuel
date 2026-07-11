import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchMarketRuns } from "../api/market-correlation";

export function MarketAnalysisQualityPage() {
  const q = useQuery({ queryKey: ["market-runs"], queryFn: fetchMarketRuns });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Qualidade estatística</h1>
        <p className="text-sm text-slate-600">
          Amostra insuficiente e série constante não exibem coeficiente isolado como conclusão.
        </p>
      </div>
      <Link className="text-sm underline" to="/analytics/market-correlation">
        Voltar
      </Link>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Run</th>
            <th>Status</th>
            <th>Amostra</th>
            <th>Warnings</th>
            <th>Qualidade</th>
          </tr>
        </thead>
        <tbody>
          {(q.data ?? []).map((r) => (
            <tr key={r.id} className="border-b border-slate-100">
              <td className="py-2">
                <Link className="underline" to={`/analytics/market-correlation/runs/${r.id}`}>
                  {r.id.slice(0, 8)}
                </Link>
              </td>
              <td>{r.status}</td>
              <td>{r.sample_size}</td>
              <td>{r.warning_count}</td>
              <td>{String((r.output_snapshot as { quality_status?: string } | null)?.quality_status ?? "—")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
