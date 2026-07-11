import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchMarketRun, reprocessMarketRun } from "../api/market-correlation";
import { useAuth } from "../auth/AuthProvider";

export function MarketAnalysisRunDetailsPage() {
  const { id = "" } = useParams();
  const { hasPermission } = useAuth();
  const canReprocess = hasPermission("market_analysis.reprocess");
  const qc = useQueryClient();
  const runQ = useQuery({
    queryKey: ["market-run", id],
    queryFn: () => fetchMarketRun(id),
    enabled: Boolean(id),
  });
  const reprocessM = useMutation({
    mutationFn: () => reprocessMarketRun(id, "Reprocessamento manual Sprint 10"),
    onSuccess: (run) => {
      qc.invalidateQueries({ queryKey: ["market-runs"] });
      window.location.href = `/analytics/market-correlation/runs/${run.id}`;
    },
  });

  const run = runQ.data;
  const out = (run?.output_snapshot ?? {}) as Record<string, unknown>;
  const pearson = (out.pearson ?? {}) as Record<string, unknown>;
  const spearman = (out.spearman ?? {}) as Record<string, unknown>;
  const passThrough = (out.pass_through ?? {}) as Record<string, unknown>;
  const lags = (out.lags ?? []) as Array<Record<string, unknown>>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Detalhe da análise</h1>
          <p className="text-sm text-slate-600">{run?.interpretive_disclaimer}</p>
        </div>
        {canReprocess ? (
          <button
            type="button"
            className="rounded border border-slate-300 px-3 py-2 text-sm"
            disabled={reprocessM.isPending}
            onClick={() => reprocessM.mutate()}
          >
            Reprocessar (nova run)
          </button>
        ) : null}
      </div>
      <Link className="text-sm underline" to="/analytics/market-correlation">
        Voltar
      </Link>

      {runQ.isLoading ? <p>Carregando…</p> : null}
      {run ? (
        <>
          <section className="grid gap-4 md:grid-cols-3">
            <Info label="Status" value={run.status} />
            <Info label="Transformação" value={run.transformation} />
            <Info label="Frequência" value={run.frequency} />
            <Info label="Amostra" value={String(run.sample_size)} />
            <Info label="Pares alinhados" value={String(run.aligned_pair_count)} />
            <Info
              label="Defasagem estimada"
              value={run.selected_lag != null ? String(run.selected_lag) : "—"}
            />
            <Info label="Hash snapshot" value={run.snapshot_hash ?? "—"} />
            <Info label="Pearson" value={String(pearson.coefficient ?? "—")} />
            <Info label="Spearman" value={String(spearman.coefficient ?? "—")} />
            <Info label="Repasse altas" value={String(passThrough.upward_average_ratio ?? "—")} />
            <Info label="Repasse quedas" value={String(passThrough.downward_average_ratio ?? "—")} />
            <Info label="Assimetria" value={String(passThrough.asymmetry ?? "—")} />
          </section>

          <section>
            <h2 className="mb-2 font-medium">Correlação por lag (associação observada)</h2>
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-slate-500">
                  <th className="py-2">Lag</th>
                  <th>Coeficiente</th>
                  <th>Pares</th>
                  <th>Qualidade</th>
                </tr>
              </thead>
              <tbody>
                {lags.map((l) => (
                  <tr key={String(l.lag)} className="border-b border-slate-100">
                    <td className="py-2">{String(l.lag)}</td>
                    <td>{String(l.coefficient ?? "—")}</td>
                    <td>{String(l.sample_size)}</td>
                    <td>{String(l.quality_status)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <section>
            <h2 className="mb-2 font-medium">Warnings</h2>
            <pre className="overflow-auto rounded bg-slate-50 p-3 text-xs">
              {JSON.stringify(out.warnings ?? [], null, 2)}
            </pre>
          </section>
        </>
      ) : null}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-slate-200 p-3">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="mt-1 break-all text-sm font-medium">{value}</div>
    </div>
  );
}
