import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiFetch } from "../api/client";
import { fetchXpertSummary } from "../api/xpert-integration";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";

type Summary = {
  status: string;
  security_status?: string | null;
  sources_count: number;
  datasets_enabled: number;
  pending_products: number;
  pending_suppliers: number;
  error_runs: number;
  last_success_at: string | null;
  odbc_available: boolean;
  worker_healthy: boolean;
  worker_last_heartbeat_at: string | null;
};

type Source = {
  id: string;
  code: string;
  name: string;
  host: string;
  connection_status: string;
  enabled: boolean;
};

type Dataset = {
  id: string;
  code: string;
  name: string;
  contract_status: string;
  enabled: boolean;
  sync_mode: string;
};

type SyncRun = {
  id: string;
  status: string;
  sync_mode: string;
  rows_read: number;
  rows_applied: number;
  rows_error: number;
  created_at: string;
};

export function XpertIntegrationPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [runs, setRuns] = useState<SyncRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [summaryRes, sourcesRes, datasetsRes, runsRes] = await Promise.all([
          fetchXpertSummary(),
          apiFetch<Source[]>("/api/v1/integrations/xpert/sources"),
          apiFetch<Dataset[]>("/api/v1/integrations/xpert/datasets"),
          apiFetch<{ items: SyncRun[] }>("/api/v1/integrations/xpert/sync-runs?page_size=10"),
        ]);
        if (!cancelled) {
          setSummary(summaryRes);
          setSources(sourcesRes);
          setDatasets(datasetsRes);
          setRuns(runsRes.items);
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Falha ao carregar integração.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <p className="text-slate-600">Carregando integração XPERT…</p>;
  if (error) return <p className="text-red-600">{error}</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Integração XPERT</h1>
        <p className="text-sm text-slate-600">Conector somente leitura, staging e sincronização incremental.</p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={summary?.security_status} />

      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card title="Status" value={summary.status} />
          <Card title="ODBC Driver" value={summary.odbc_available ? "Disponível" : "Ausente"} />
          <Card title="Worker" value={summary.worker_healthy ? "Saudável" : "Indisponível"} />
          <Card title="Produtos pendentes" value={String(summary.pending_products)} />
        </div>
      )}

      <nav className="flex flex-wrap gap-3 text-sm">
        <Link className="text-blue-600 hover:underline" to="/integrations/xpert/source">
          Fonte
        </Link>
        <Link className="text-blue-600 hover:underline" to="/integrations/xpert/datasets">
          Datasets
        </Link>
        <Link className="text-blue-600 hover:underline" to="/integrations/xpert/runs">
          Execuções
        </Link>
        <Link className="text-blue-600 hover:underline" to="/integrations/xpert/sync">
          Sincronizar
        </Link>
        <Link className="text-blue-600 hover:underline" to="/integrations/xpert/checkpoints">
          Checkpoints
        </Link>
      </nav>

      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card title="Datasets ativos" value={String(summary.datasets_enabled)} />
          <Card title="Fornecedores pendentes" value={String(summary.pending_suppliers)} />
        </div>
      )}

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-lg font-medium">Fontes</h2>
        {sources.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhuma fonte cadastrada.</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {sources.map((s) => (
              <li key={s.id} className="flex items-center justify-between py-2 text-sm">
                <span>
                  {s.name} <span className="text-slate-400">({s.code})</span>
                </span>
                <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">{s.connection_status}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-lg font-medium">Datasets</h2>
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-slate-500">
              <th className="py-2">Código</th>
              <th>Contrato</th>
              <th>Modo</th>
              <th>Ativo</th>
            </tr>
          </thead>
          <tbody>
            {datasets.map((d) => (
              <tr key={d.id} className="border-b border-slate-50">
                <td className="py-2">{d.code}</td>
                <td>{d.contract_status}</td>
                <td>{d.sync_mode}</td>
                <td>{d.enabled ? "Sim" : "Não"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-lg font-medium">Últimas execuções</h2>
        {runs.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhuma execução registrada.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="py-2">Status</th>
                <th>Modo</th>
                <th>Lidos</th>
                <th>Aplicados</th>
                <th>Erros</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-b border-slate-50">
                  <td className="py-2">
                    <Link className="text-blue-600 hover:underline" to={`/integrations/xpert/runs/${r.id}`}>
                      {r.status}
                    </Link>
                  </td>
                  <td>{r.sync_mode}</td>
                  <td>{r.rows_read}</td>
                  <td>{r.rows_applied}</td>
                  <td>{r.rows_error}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <p className="text-xs text-slate-500">
        A integração nunca grava no SQL Server do XPERT. Credenciais permanecem fora do banco da aplicação.
      </p>
    </div>
  );
}

function Card({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}
