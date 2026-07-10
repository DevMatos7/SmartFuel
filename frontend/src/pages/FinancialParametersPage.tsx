import { useEffect, useState } from "react";
import { createFinancialParameter, listFinancialParameters } from "../api/quote-comparisons";
import { useAuth } from "../auth/AuthProvider";

export function FinancialParametersPage() {
  const { hasPermission } = useAuth();
  const [items, setItems] = useState<Awaited<ReturnType<typeof listFinancialParameters>>["items"]>([]);
  const [annualRatePercent, setAnnualRatePercent] = useState("15");
  const [validFrom, setValidFrom] = useState(() => new Date().toISOString().slice(0, 16));
  const [error, setError] = useState<string | null>(null);

  async function load() {
    const data = await listFinancialParameters({ page: 1, page_size: 50 });
    setItems(data.items);
  }

  useEffect(() => {
    void load().catch((err) => setError(err instanceof Error ? err.message : "Falha ao carregar parâmetros."));
  }, []);

  async function handleCreate() {
    setError(null);
    try {
      await createFinancialParameter({
        annual_effective_rate: (Number(annualRatePercent) / 100).toFixed(8),
        day_count_basis: 365,
        valid_from: new Date(validFrom).toISOString(),
      });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao criar parâmetro.");
    }
  }

  if (!hasPermission("financial_parameters.read")) {
    return <p className="text-sm text-slate-600">Sem permissão para visualizar parâmetros financeiros.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Parâmetros financeiros</h1>
        <p className="text-sm text-slate-600">Taxa anual efetiva de capital por vigência.</p>
      </div>

      {hasPermission("financial_parameters.write") && (
        <section className="rounded-lg border bg-white p-4">
          <h2 className="font-medium">Nova taxa</h2>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            <label className="text-sm">
              Taxa anual (%)
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={annualRatePercent}
                onChange={(e) => setAnnualRatePercent(e.target.value)}
              />
            </label>
            <label className="text-sm">
              Início da vigência
              <input
                type="datetime-local"
                className="mt-1 w-full rounded border px-3 py-2"
                value={validFrom}
                onChange={(e) => setValidFrom(e.target.value)}
              />
            </label>
          </div>
          <button type="button" className="mt-3 rounded bg-slate-900 px-4 py-2 text-sm text-white" onClick={() => void handleCreate()}>
            Salvar taxa
          </button>
          <p className="mt-2 text-xs text-slate-500">
            Alterações na taxa não modificam comparações já concluídas.
          </p>
        </section>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <section className="overflow-x-auto rounded-lg border bg-white">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-left">
            <tr>
              <th className="px-3 py-2">Taxa anual</th>
              <th className="px-3 py-2">Base</th>
              <th className="px-3 py-2">Vigência</th>
              <th className="px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t">
                <td className="px-3 py-2">{(Number(item.annual_effective_rate) * 100).toFixed(4)}%</td>
                <td className="px-3 py-2">{item.day_count_basis} dias</td>
                <td className="px-3 py-2">
                  {new Date(item.valid_from).toLocaleString()}
                  {item.valid_until ? ` — ${new Date(item.valid_until).toLocaleString()}` : " — aberta"}
                </td>
                <td className="px-3 py-2">{item.active ? "Ativa" : "Inativa"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
