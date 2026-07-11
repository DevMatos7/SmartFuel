import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  createSyntheticMarketRun,
  fetchMarketCorrelationSummary,
  fetchMarketRuns,
} from "../api/market-correlation";
import { useAuth } from "../auth/AuthProvider";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";

function buildLagScenario() {
  const start = new Date("2026-01-01T12:00:00Z");
  const external = [];
  const internal = [];
  for (let i = 0; i < 30; i += 1) {
    const d = new Date(start);
    d.setUTCDate(start.getUTCDate() + i);
    const iso = d.toISOString();
    const extVal = (100 + i * 0.5).toFixed(4);
    external.push({
      observation_datetime: iso,
      available_at: iso,
      value: extVal,
    });
    // alvo segue o índice com lag 3
    const src = Math.max(0, i - 3);
    const srcDate = new Date(start);
    srcDate.setUTCDate(start.getUTCDate() + src);
    const intVal = (50 + src * 0.5 + 0.01 * i).toFixed(4);
    internal.push({
      observation_datetime: iso,
      available_at: iso,
      value: intVal,
    });
  }
  return {
    analysis_type: "FULL",
    internal_series_type: "SYNTHETIC_INTERNAL",
    period_start: external[0].observation_datetime,
    period_end: external[external.length - 1].observation_datetime,
    frequency: "DAILY",
    transformation: "ABSOLUTE_CHANGE",
    alignment_policy: "EXACT_DATE",
    lag_min: 0,
    lag_max: 7,
    synthetic_external: external,
    synthetic_internal: internal,
  };
}

export function MarketCorrelationDashboardPage() {
  const { hasPermission } = useAuth();
  const canRun = hasPermission("market_analysis.run");
  const qc = useQueryClient();
  const summaryQ = useQuery({
    queryKey: ["market-correlation-summary"],
    queryFn: fetchMarketCorrelationSummary,
  });
  const runsQ = useQuery({ queryKey: ["market-runs"], queryFn: fetchMarketRuns });
  const synthM = useMutation({
    mutationFn: () => createSyntheticMarketRun(buildLagScenario()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["market-correlation-summary"] });
      qc.invalidateQueries({ queryKey: ["market-runs"] });
    },
  });

  const s = summaryQ.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Correlação e defasagem</h1>
          <p className="text-sm text-slate-600">
            Associação observada · defasagem estimada · repasse observado — sem causalidade
          </p>
        </div>
        {canRun ? (
          <button
            type="button"
            className="rounded bg-slate-800 px-3 py-2 text-sm text-white"
            disabled={synthM.isPending}
            onClick={() => synthM.mutate()}
          >
            Rodar cenário sintético (lag ~3)
          </button>
        ) : null}
      </div>

      <XpertUnsafeSourceBanner securityStatus="UNSAFE" />
      <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-950">
        {s?.disclaimer ??
          "Correlação não é causalidade. Homologação real depende de séries externas homologadas (Sprint 9)."}
      </p>
      {s?.note ? <p className="text-sm text-slate-600">{s.note}</p> : null}

      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="underline" to="/analytics/external-indices">
          Índices externos
        </Link>
        <Link className="underline" to="/analytics/market-correlation/quality">
          Qualidade estatística
        </Link>
        <Link className="underline" to="/analytics/market-correlation/parameters">
          Parâmetros
        </Link>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Execuções" value={s?.runs_count?.toString()} loading={summaryQ.isLoading} />
        <Card label="Concluídas" value={s?.completed_count?.toString()} loading={summaryQ.isLoading} />
        <Card
          label="Amostra insuficiente"
          value={s?.insufficient_sample_count?.toString()}
          loading={summaryQ.isLoading}
        />
        <Card
          label="Maior |associação|"
          value={s?.strongest_association?.coefficient ?? "—"}
          loading={summaryQ.isLoading}
        />
        <Card
          label="Defasagem estimada"
          value={
            s?.strongest_association?.selected_lag != null
              ? String(s.strongest_association.selected_lag)
              : "—"
          }
          loading={summaryQ.isLoading}
        />
      </section>

      <section>
        <h2 className="mb-2 font-medium">Execuções recentes</h2>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-slate-500">
              <th className="py-2">Início</th>
              <th>Status</th>
              <th>Referência</th>
              <th>Alvo</th>
              <th>Pares</th>
              <th>Lag</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(runsQ.data ?? []).map((r) => (
              <tr key={r.id} className="border-b border-slate-100">
                <td className="py-2">{r.started_at}</td>
                <td>{r.status}</td>
                <td>{r.external_series_code ?? "—"}</td>
                <td>{r.internal_series_type}</td>
                <td>{r.aligned_pair_count}</td>
                <td>{r.selected_lag ?? "—"}</td>
                <td>
                  <Link className="underline" to={`/analytics/market-correlation/runs/${r.id}`}>
                    Detalhe
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!runsQ.isLoading && (runsQ.data?.length ?? 0) === 0 ? (
          <p className="mt-2 text-sm text-slate-600">Nenhuma análise. Execute o cenário sintético.</p>
        ) : null}
      </section>
    </div>
  );
}

function Card({
  label,
  value,
  loading,
}: {
  label: string;
  value?: string | null;
  loading?: boolean;
}) {
  return (
    <div className="rounded border border-slate-200 p-4">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{loading ? "…" : (value ?? "—")}</div>
    </div>
  );
}
