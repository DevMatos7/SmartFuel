import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import {
  getComparisonMethodology,
  runQuoteComparison,
  type ComparisonResult,
  type ComparisonRun,
  type RankingMode,
  type RankingScope,
} from "../api/quote-comparisons";
import { fetchProducts } from "../api/master-data";

function formatMoney(value?: string | null, digits = 4) {
  if (!value) return "—";
  return `R$ ${Number(value).toFixed(digits)}`;
}

export function QuoteComparisonPage() {
  const { hasPermission } = useAuth();
  const [selectedStationId, setSelectedStationId] = useState(() => localStorage.getItem("active_station_id") ?? "");
  const [products, setProducts] = useState<Array<{ id: string; name: string }>>([]);
  const [productId, setProductId] = useState("");
  const [volume, setVolume] = useState("30000");
  const [comparisonAt, setComparisonAt] = useState(() => new Date().toISOString().slice(0, 16));
  const [requiredDeliveryAt, setRequiredDeliveryAt] = useState("");
  const [rankingMode, setRankingMode] = useState<RankingMode>("FINANCIAL_EQUIVALENT");
  const [rankingScope, setRankingScope] = useState<RankingScope>("BEST_PER_DISTRIBUTOR");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ComparisonRun | null>(null);
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const [methodology, setMethodology] = useState<Record<string, unknown> | null>(null);
  const [selectedItems, setSelectedItems] = useState<string[]>([]);

  useEffect(() => {
    setSelectedStationId(localStorage.getItem("active_station_id") ?? "");
    void fetchProducts({ page: 1, page_size: 100 }).then((data) => {
      setProducts(data.items.map((p) => ({ id: p.id, name: p.name })));
      if (data.items[0]) setProductId(data.items[0].id);
    });
  }, []);

  const ranked = useMemo(
    () => (result?.results ?? []).filter((r) => r.rank_position != null).sort((a, b) => (a.rank_position ?? 0) - (b.rank_position ?? 0)),
    [result],
  );
  const ineligible = useMemo(
    () => (result?.results ?? []).filter((r) => r.eligibility_status === "INELIGIBLE"),
    [result],
  );

  async function handleCompare() {
    if (!selectedStationId || !productId) {
      setError("Selecione posto e produto.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const comparison = await runQuoteComparison({
        station_id: selectedStationId,
        product_id: productId,
        requested_volume_liters: `${Number(volume).toFixed(3)}`,
        comparison_datetime: new Date(comparisonAt).toISOString(),
        required_delivery_at: requiredDeliveryAt ? new Date(requiredDeliveryAt).toISOString() : null,
        ranking_mode: rankingMode,
        ranking_scope: rankingScope,
      });
      setResult(comparison);
      setSelectedItems([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao comparar propostas.");
    } finally {
      setLoading(false);
    }
  }

  async function openMethodology() {
    setMethodologyOpen(true);
    if (!methodology) {
      setMethodology(await getComparisonMethodology());
    }
  }

  function toggleSelection(itemId: string) {
    setSelectedItems((current) => {
      if (current.includes(itemId)) return current.filter((id) => id !== itemId);
      if (current.length >= 4) return current;
      return [...current, itemId];
    });
  }

  if (!hasPermission("quote_comparisons.run")) {
    return <p className="text-sm text-slate-600">Você não possui permissão para executar comparações.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Comparar cotações</h1>
          <p className="text-sm text-slate-600">Ranking com custo entregue e equivalente à vista.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" className="rounded border px-3 py-2 text-sm" onClick={() => void openMethodology()}>
            Metodologia
          </button>
          <Link to="/quote-comparisons/history" className="rounded border px-3 py-2 text-sm">
            Histórico
          </Link>
        </div>
      </div>

      <section className="rounded-lg border bg-white p-4">
        <div className="grid gap-4 md:grid-cols-2">
          <label className="text-sm">
            Produto
            <select className="mt-1 w-full rounded border px-3 py-2" value={productId} onChange={(e) => setProductId(e.target.value)}>
              {products.map((product) => (
                <option key={product.id} value={product.id}>
                  {product.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-sm">
            Volume solicitado (L)
            <input className="mt-1 w-full rounded border px-3 py-2" value={volume} onChange={(e) => setVolume(e.target.value)} />
          </label>
          <label className="text-sm">
            Data da comparação
            <input
              type="datetime-local"
              className="mt-1 w-full rounded border px-3 py-2"
              value={comparisonAt}
              onChange={(e) => setComparisonAt(e.target.value)}
            />
          </label>
          <label className="text-sm">
            Entrega necessária
            <input
              type="datetime-local"
              className="mt-1 w-full rounded border px-3 py-2"
              value={requiredDeliveryAt}
              onChange={(e) => setRequiredDeliveryAt(e.target.value)}
            />
          </label>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {(["RAW", "DELIVERED", "FINANCIAL_EQUIVALENT"] as RankingMode[]).map((mode) => (
            <button
              key={mode}
              type="button"
              className={`rounded px-3 py-1 text-sm ${rankingMode === mode ? "bg-slate-900 text-white" : "border"}`}
              onClick={() => setRankingMode(mode)}
            >
              {mode === "RAW" ? "Preço bruto" : mode === "DELIVERED" ? "Custo entregue" : "Equivalente à vista"}
            </button>
          ))}
        </div>
        <div className="mt-2 flex flex-wrap gap-2">
          {(["BEST_PER_DISTRIBUTOR", "ALL_OFFERS"] as RankingScope[]).map((scope) => (
            <button
              key={scope}
              type="button"
              className={`rounded px-3 py-1 text-sm ${rankingScope === scope ? "bg-slate-900 text-white" : "border"}`}
              onClick={() => setRankingScope(scope)}
            >
              {scope === "BEST_PER_DISTRIBUTOR" ? "Melhor por distribuidora" : "Todas as ofertas"}
            </button>
          ))}
        </div>

        <button
          type="button"
          className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          disabled={loading}
          onClick={() => void handleCompare()}
        >
          {loading ? "Comparando..." : "Comparar propostas"}
        </button>
        {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      </section>

      {result && (
        <>
          <section className="grid gap-4 md:grid-cols-3 xl:grid-cols-6">
            <div className="rounded-lg border bg-white p-4">
              <p className="text-xs text-slate-500">Melhor custo</p>
              <p className="text-lg font-semibold">{formatMoney(result.summary.best_cost_per_liter)}/L</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-xs text-slate-500">Maior custo</p>
              <p className="text-lg font-semibold">{formatMoney(result.summary.highest_cost_per_liter)}/L</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-xs text-slate-500">Média</p>
              <p className="text-lg font-semibold">{formatMoney(result.summary.average_cost_per_liter)}/L</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-xs text-slate-500">Spread</p>
              <p className="text-lg font-semibold">
                {formatMoney(result.summary.spread_absolute)}/L
                {result.summary.spread_percent ? ` (${Number(result.summary.spread_percent).toFixed(2)}%)` : ""}
              </p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-xs text-slate-500">Elegíveis</p>
              <p className="text-lg font-semibold">{result.summary.eligible_count}</p>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <p className="text-xs text-slate-500">Distribuidoras</p>
              <p className="text-lg font-semibold">{result.summary.distributor_count}</p>
            </div>
          </section>

          <section className="overflow-x-auto rounded-lg border bg-white">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left">
                <tr>
                  <th className="px-3 py-2">Sel.</th>
                  <th className="px-3 py-2">Pos.</th>
                  <th className="px-3 py-2">Distribuidora</th>
                  <th className="px-3 py-2">Preço</th>
                  <th className="px-3 py-2">Entregue</th>
                  <th className="px-3 py-2">Equivalente</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {ranked.map((row) => (
                  <tr key={row.quote_item_id} className="border-t">
                    <td className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={selectedItems.includes(row.quote_item_id)}
                        onChange={() => toggleSelection(row.quote_item_id)}
                        aria-label={`Selecionar ${row.distributor.name}`}
                      />
                    </td>
                    <td className="px-3 py-2">{row.rank_position}</td>
                    <td className="px-3 py-2">{row.distributor.name}</td>
                    <td className="px-3 py-2">{formatMoney(row.costs.raw_price_per_liter)}</td>
                    <td className="px-3 py-2">{formatMoney(row.costs.delivered_cost_per_liter)}</td>
                    <td className="px-3 py-2">{formatMoney(row.costs.financial_equivalent_cost_per_liter)}</td>
                    <td className="px-3 py-2">{row.eligibility_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {selectedItems.length > 0 && (
            <section className="rounded-lg border bg-white p-4">
              <h2 className="font-medium">Comparação lado a lado</h2>
              <div className="mt-3 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead>
                    <tr>
                      <th className="px-2 py-1 text-left">Critério</th>
                      {selectedItems.map((id) => {
                        const row = result.results.find((r) => r.quote_item_id === id);
                        return (
                          <th key={id} className="px-2 py-1 text-left">
                            {row?.distributor.name}
                          </th>
                        );
                      })}
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        ["Preço bruto", (r: ComparisonResult) => formatMoney(r.costs.raw_price_per_liter)],
                        ["Frete/L", (r: ComparisonResult) => formatMoney(r.costs.freight_per_liter)],
                        ["Entregue", (r: ComparisonResult) => formatMoney(r.costs.delivered_cost_per_liter)],
                        ["Equivalente", (r: ComparisonResult) => formatMoney(r.costs.financial_equivalent_cost_per_liter)],
                        ["Elegibilidade", (r: ComparisonResult) => r.eligibility_status],
                      ] as const
                    ).map(([label, getter]) => (
                      <tr key={label} className="border-t">
                        <td className="px-2 py-1">{label}</td>
                        {selectedItems.map((id) => {
                          const row = result.results.find((r) => r.quote_item_id === id);
                          return <td key={id} className="px-2 py-1">{row ? getter(row) : "—"}</td>;
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {ineligible.length > 0 && (
            <section className="rounded-lg border bg-white p-4">
              <h2 className="font-medium">Propostas fora do ranking</h2>
              <ul className="mt-3 space-y-3">
                {ineligible.map((row) => (
                  <li key={row.quote_item_id} className="rounded border p-3">
                    <p className="font-medium">{row.distributor.name}</p>
                    <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
                      {row.eligibility_reasons.map((reason) => (
                        <li key={reason.code}>{reason.message}</li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <div className="flex gap-2">
            <Link to={`/quote-comparisons/${result.id}`} className="rounded border px-3 py-2 text-sm">
              Ver detalhes
            </Link>
            {hasPermission("quote_comparisons.export") && (
              <>
                <a href={`/api/v1/quote-comparisons/${result.id}/export/pdf`} className="rounded border px-3 py-2 text-sm">
                  Exportar PDF
                </a>
                <a href={`/api/v1/quote-comparisons/${result.id}/export/csv`} className="rounded border px-3 py-2 text-sm">
                  Exportar CSV
                </a>
              </>
            )}
          </div>
        </>
      )}

      {methodologyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-h-[80vh] w-full max-w-2xl overflow-auto rounded-lg bg-white p-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Como os custos são calculados</h2>
              <button type="button" className="text-sm" onClick={() => setMethodologyOpen(false)}>
                Fechar
              </button>
            </div>
            <pre className="mt-4 whitespace-pre-wrap text-xs text-slate-700">
              {JSON.stringify(methodology, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
