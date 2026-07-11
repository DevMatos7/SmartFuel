import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchBenchmarkCoverage,
  fetchBenchmarkDataQuality,
  fetchBenchmarkOpportunities,
  fetchBenchmarkSummary,
} from "../api/purchase-benchmarks";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

function defaultRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return { from: from.toISOString().slice(0, 10), to: to.toISOString().slice(0, 10) };
}

export function PurchaseBenchmarkDashboardPage() {
  const { hasPermission } = useAuth();
  const canOpp = hasPermission("purchase_benchmarks.view_opportunity");
  const [range] = useState(defaultRange);

  const summaryQ = useQuery({
    queryKey: ["pb-summary", range],
    queryFn: () => fetchBenchmarkSummary(range.from, range.to),
  });
  const coverageQ = useQuery({
    queryKey: ["pb-coverage", range],
    queryFn: () => fetchBenchmarkCoverage(range.from, range.to),
  });
  const qualityQ = useQuery({
    queryKey: ["pb-quality", range],
    queryFn: () => fetchBenchmarkDataQuality(range.from, range.to),
  });
  const oppQ = useQuery({
    queryKey: ["pb-opp", range],
    queryFn: () => fetchBenchmarkOpportunities(range.from, range.to),
    enabled: canOpp,
  });

  const s = summaryQ.data;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Compra real × cotação</h1>
        <p className="text-sm text-slate-600">
          Comparação histórica sem viés retrospectivo · {range.from} a {range.to}
        </p>
      </div>
      <XpertUnsafeSourceBanner securityStatus="UNSAFE" />
      <p className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded p-3">
        Dados de compra sincronizados de fonte XPERT insegura — usuário sa. O benchmark calcula no
        PostgreSQL e não grava no ERP.
      </p>

      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="underline" to="/analytics/purchase-benchmarks/opportunities">
          Oportunidades
        </Link>
        <Link className="underline" to="/analytics/purchase-benchmarks/quality">
          Qualidade
        </Link>
        <Link className="underline" to="/analytics/fuel-purchases/invoices">
          Notas de compra
        </Link>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Volume comprado" value={s?.purchased_volume_liters} loading={summaryQ.isLoading} />
        <Card label="Volume com benchmark" value={s?.benchmarked_volume_liters} loading={summaryQ.isLoading} />
        <Card
          label="Cobertura (volume)"
          value={s?.coverage_volume_ratio ? `${(Number(s.coverage_volume_ratio) * 100).toFixed(1)}%` : "—"}
          loading={summaryQ.isLoading}
        />
        <Card label="Melhor opção / empate" value={s?.best_or_tied_count?.toString()} loading={summaryQ.isLoading} />
        <Card label="Custo real" value={s?.actual_total_cost} loading={summaryQ.isLoading} />
        <Card label="Custo benchmark" value={s?.benchmark_total_cost ?? "—"} loading={summaryQ.isLoading} />
        <Card label="Diferença total" value={s?.cost_variance_amount ?? "—"} loading={summaryQ.isLoading} />
        {canOpp && (
          <Card label="Oportunidade estimada" value={s?.opportunity_amount ?? "—"} loading={summaryQ.isLoading} />
        )}
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <div>
          <h2 className="mb-2 font-medium">Cobertura por status</h2>
          {coverageQ.isLoading ? (
            <p className="text-sm text-slate-500">Carregando…</p>
          ) : (
            <ul className="space-y-1 text-sm">
              {Object.entries(coverageQ.data?.by_status ?? {}).map(([status, row]) => (
                <li key={status} className="flex justify-between border-b py-1">
                  <span>{status}</span>
                  <span>{(row as { count?: number }).count ?? 0}</span>
                </li>
              ))}
              {!coverageQ.data?.total_groups && <li className="text-slate-500">Sem benchmarks no período.</li>}
            </ul>
          )}
        </div>
        <div>
          <h2 className="mb-2 font-medium">Qualidade</h2>
          {qualityQ.isLoading ? (
            <p className="text-sm text-slate-500">Carregando…</p>
          ) : (
            <ul className="space-y-1 text-sm">
              <li>Sem produto mapeado: {qualityQ.data?.unmapped_product_count ?? 0}</li>
              <li>Sem custo: {qualityQ.data?.missing_cost_count ?? 0}</li>
              <li>Sem cotação: {qualityQ.data?.no_quotes_count ?? 0}</li>
              <li>Sem elegível: {qualityQ.data?.no_eligible_count ?? 0}</li>
              <li>Referência baixa: {qualityQ.data?.low_confidence_count ?? 0}</li>
            </ul>
          )}
        </div>
      </section>

      {canOpp && (
        <section>
          <h2 className="mb-2 font-medium">Maiores oportunidades</h2>
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
              {(oppQ.data ?? []).slice(0, 10).map((row) => (
                <tr key={row.benchmark_item_id} className="border-b">
                  <td className="py-2 pr-4 font-mono text-xs">
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
              {!oppQ.data?.length && (
                <tr>
                  <td colSpan={5} className="py-4 text-slate-500">
                    Nenhuma oportunidade no período.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      )}
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
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-medium">{loading ? "…" : (value ?? "—")}</p>
    </div>
  );
}
