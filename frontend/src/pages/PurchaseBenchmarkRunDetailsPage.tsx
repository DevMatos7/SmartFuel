import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchBenchmarkRun, reprocessBenchmarkRun } from "../api/purchase-benchmarks";
import { useAuth } from "../auth/AuthProvider";

export function PurchaseBenchmarkRunDetailsPage() {
  const { id = "" } = useParams();
  const { hasPermission } = useAuth();
  const canReprocess = hasPermission("purchase_benchmarks.reprocess");
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["pb-run", id],
    queryFn: () => fetchBenchmarkRun(id),
    enabled: Boolean(id),
  });
  const reprocess = useMutation({
    mutationFn: () => reprocessBenchmarkRun(id, "Reprocessamento manual via UI"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pb-run"] }),
  });

  if (q.isLoading) return <p className="text-sm text-slate-500">Carregando…</p>;
  if (q.isError || !q.data) return <p className="text-sm text-rose-600">Run não encontrada.</p>;
  const run = q.data;

  return (
    <div className="space-y-6">
      <div>
        <Link to="/analytics/purchase-benchmarks" className="text-sm underline text-slate-500">
          Voltar
        </Link>
        <h1 className="mt-2 text-xl font-semibold">Benchmark {run.id.slice(0, 8)}…</h1>
        <p className="text-sm text-slate-600">
          {run.status} · {run.comparison_mode} · confiança {run.reference_confidence}
        </p>
      </div>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3 text-sm">
        <Info label="Referência" value={run.reference_datetime ?? "—"} />
        <Info label="Origem da data" value={run.reference_source} />
        <Info label="Custo real" value={run.actual_total_cost} />
        <Info label="Custo benchmark" value={run.benchmark_total_cost ?? "—"} />
        <Info label="Diferença" value={run.cost_variance_amount ?? "—"} />
        <Info label="Oportunidade" value={run.opportunity_amount ?? "—"} />
        <Info label="Vantagem" value={run.actual_advantage_amount ?? "—"} />
        <Info label="Hash" value={run.snapshot_hash?.slice(0, 16) ?? "—"} />
      </section>

      {canReprocess && (
        <button
          type="button"
          className="rounded border px-3 py-2 text-sm"
          disabled={reprocess.isPending}
          onClick={() => reprocess.mutate()}
        >
          Reprocessar
        </button>
      )}

      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-left text-slate-500">
            <th className="py-2 pr-4">Grupo</th>
            <th className="py-2 pr-4">Volume</th>
            <th className="py-2 pr-4">Real/L</th>
            <th className="py-2 pr-4">Melhor/L</th>
            <th className="py-2 pr-4">Dif/L</th>
            <th className="py-2 pr-4">Resultado</th>
            <th className="py-2 pr-4">Status</th>
            <th className="py-2 pr-4">Rank dist.</th>
          </tr>
        </thead>
        <tbody>
          {run.items.map((item) => (
            <tr key={item.id} className="border-b">
              <td className="py-2 pr-4 font-mono text-xs">{item.group_key}</td>
              <td className="py-2 pr-4">{item.volume_liters}</td>
              <td className="py-2 pr-4">{item.actual_delivered_cost_per_liter ?? "—"}</td>
              <td className="py-2 pr-4">{item.benchmark_cost_per_liter ?? "—"}</td>
              <td className="py-2 pr-4">{item.cost_variance_per_liter ?? "—"}</td>
              <td className="py-2 pr-4">{item.decision_result}</td>
              <td className="py-2 pr-4">{item.benchmark_status}</td>
              <td className="py-2 pr-4">{item.actual_distributor_rank ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <p className="text-sm">
        Nota:{" "}
        <Link className="underline" to={`/analytics/fuel-purchases/invoices/${run.purchase_invoice_id}`}>
          abrir compra
        </Link>
      </p>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="mt-1 break-all">{value}</p>
    </div>
  );
}
