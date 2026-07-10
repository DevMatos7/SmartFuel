import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listQuoteComparisons, type ComparisonRunListItem } from "../api/quote-comparisons";
import { useAuth } from "../auth/AuthProvider";

export function QuoteComparisonHistoryPage() {
  const { hasPermission } = useAuth();
  const [items, setItems] = useState<ComparisonRunListItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void listQuoteComparisons({ page: 1, page_size: 50 })
      .then((data) => setItems(data.items))
      .catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar histórico."));
  }, []);

  if (!hasPermission("quote_comparisons.read")) {
    return <p className="text-sm text-slate-600">Sem permissão para consultar histórico.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Histórico de comparações</h1>
        <Link to="/quote-comparisons" className="rounded border px-3 py-2 text-sm">
          Nova comparação
        </Link>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="overflow-x-auto rounded-lg border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-3 py-2">Data</th>
              <th className="px-3 py-2">Modo</th>
              <th className="px-3 py-2">Melhor custo</th>
              <th className="px-3 py-2">Elegíveis</th>
              <th className="px-3 py-2">Ações</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t">
                <td className="px-3 py-2">{new Date(item.created_at).toLocaleString()}</td>
                <td className="px-3 py-2">{item.ranking_mode}</td>
                <td className="px-3 py-2">{item.best_cost_per_liter ? `R$ ${Number(item.best_cost_per_liter).toFixed(4)}` : "—"}</td>
                <td className="px-3 py-2">{item.eligible_count}</td>
                <td className="px-3 py-2">
                  <Link to={`/quote-comparisons/${item.id}`} className="text-slate-900 underline">
                    Abrir
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
