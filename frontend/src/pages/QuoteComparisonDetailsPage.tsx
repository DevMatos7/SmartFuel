import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getQuoteComparison, reprocessQuoteComparison } from "../api/quote-comparisons";
import { useAuth } from "../auth/AuthProvider";

export function QuoteComparisonDetailsPage() {
  const { runId } = useParams();
  const { hasPermission } = useAuth();
  const [data, setData] = useState<Awaited<ReturnType<typeof getQuoteComparison>> | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    void getQuoteComparison(runId)
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar comparação."));
  }, [runId]);

  async function handleReprocess() {
    if (!runId || !hasPermission("quote_comparisons.reprocess")) return;
    const next = await reprocessQuoteComparison(runId, {});
    setData(next);
  }

  if (error) return <p className="text-sm text-red-600">{error}</p>;
  if (!data) return <p className="text-sm text-slate-600">Carregando...</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Detalhes da comparação</h1>
          <p className="text-sm text-slate-600">{data.methodology_version}</p>
        </div>
        <div className="flex gap-2">
          <Link to="/quote-comparisons/history" className="rounded border px-3 py-2 text-sm">
            Histórico
          </Link>
          {hasPermission("quote_comparisons.reprocess") && (
            <button type="button" className="rounded border px-3 py-2 text-sm" onClick={() => void handleReprocess()}>
              Reprocessar
            </button>
          )}
        </div>
      </div>

      <section className="rounded-lg border bg-white p-4 text-sm">
        <p>Volume: {data.scenario.requested_volume_liters} L</p>
        <p>Comparação: {new Date(data.scenario.comparison_datetime).toLocaleString()}</p>
        <p>Modo: {data.scenario.ranking_mode} | Escopo: {data.scenario.ranking_scope}</p>
        {data.calculation_hash && <p className="mt-2 font-mono text-xs">Hash: {data.calculation_hash}</p>}
      </section>

      <section className="rounded-lg border bg-white p-4">
        <h2 className="font-medium">Memória de cálculo</h2>
        <div className="mt-3 space-y-4">
          {data.results.map((result) => (
            <details key={result.quote_item_id} className="rounded border p-3">
              <summary className="cursor-pointer font-medium">
                {result.distributor.name} — {result.eligibility_status}
              </summary>
              <pre className="mt-2 overflow-auto text-xs">{JSON.stringify(result.calculation_snapshot, null, 2)}</pre>
            </details>
          ))}
        </div>
      </section>
    </div>
  );
}
