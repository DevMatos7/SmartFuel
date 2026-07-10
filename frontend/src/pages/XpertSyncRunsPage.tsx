import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchXpertDatasets, fetchXpertRuns, fetchXpertSources } from "../api/xpert-integration";
import { fetchStations } from "../api/stations";
import { useAuth } from "../auth/AuthProvider";

const ACTIVE_STATUSES = [
  "QUEUED",
  "CONNECTING",
  "EXTRACTING",
  "STAGING",
  "VALIDATING",
  "APPLYING",
  "CANCELLATION_REQUESTED",
];

const STATUS_OPTIONS = [
  "",
  "QUEUED",
  "CONNECTING",
  "EXTRACTING",
  "STAGING",
  "VALIDATING",
  "APPLYING",
  "COMPLETED",
  "PARTIAL",
  "FAILED",
  "CANCELLED",
  "CANCELLATION_REQUESTED",
  "SKIPPED_LOCKED",
];

export function XpertSyncRunsPage() {
  const { hasPermission } = useAuth();
  const canRun = hasPermission("erp_sync.run");

  const [page, setPage] = useState(1);
  const [sourceId, setSourceId] = useState("");
  const [datasetId, setDatasetId] = useState("");
  const [stationId, setStationId] = useState("");
  const [status, setStatus] = useState("");
  const [syncMode, setSyncMode] = useState("");
  const [triggerType, setTriggerType] = useState("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [sortBy, setSortBy] = useState("created_at");
  const [sortDir, setSortDir] = useState("desc");

  const params = useMemo(() => {
    const query: Record<string, string> = {
      page: String(page),
      page_size: "20",
      sort_by: sortBy,
      sort_dir: sortDir,
    };
    if (sourceId) query.source_id = sourceId;
    if (datasetId) query.dataset_id = datasetId;
    if (stationId) query.station_id = stationId;
    if (status) query.status = status;
    if (syncMode) query.sync_mode = syncMode;
    if (triggerType) query.trigger_type = triggerType;
    if (createdFrom) query.created_from = new Date(createdFrom).toISOString();
    if (createdTo) query.created_to = new Date(`${createdTo}T23:59:59`).toISOString();
    return query;
  }, [page, sourceId, datasetId, stationId, status, syncMode, triggerType, createdFrom, createdTo, sortBy, sortDir]);

  const { data: sources = [] } = useQuery({
    queryKey: ["xpert-sources"],
    queryFn: fetchXpertSources,
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ["xpert-datasets", sourceId],
    queryFn: () => fetchXpertDatasets(sourceId || undefined),
  });

  const { data: stationsData } = useQuery({
    queryKey: ["stations-list"],
    queryFn: () => fetchStations({ page_size: 200 }),
  });

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ["xpert-runs", params],
    queryFn: () => fetchXpertRuns(params),
    refetchInterval: (q) => {
      const items = q.state.data?.items ?? [];
      const hasActive = items.some((run) => ACTIVE_STATUSES.includes(run.status));
      return hasActive ? 5000 : false;
    },
  });

  const totalPages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20)));

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Execuções XPERT</h1>
        <div className="flex gap-2">
          {canRun && (
            <Link className="rounded bg-slate-900 px-3 py-2 text-sm text-white" to="/integrations/xpert/sync">
              Nova sincronização
            </Link>
          )}
          <Link className="text-sm text-blue-600 hover:underline" to="/integrations/xpert">
            Dashboard
          </Link>
        </div>
      </div>

      <section className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-4">
        <select className="rounded border px-2 py-2 text-sm" value={sourceId} onChange={(e) => { setSourceId(e.target.value); setPage(1); }}>
          <option value="">Todas as fontes</option>
          {sources.map((s) => (
            <option key={s.id} value={s.id}>{s.name}</option>
          ))}
        </select>
        <select className="rounded border px-2 py-2 text-sm" value={datasetId} onChange={(e) => { setDatasetId(e.target.value); setPage(1); }}>
          <option value="">Todos os datasets</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>{d.code}</option>
          ))}
        </select>
        <select className="rounded border px-2 py-2 text-sm" value={stationId} onChange={(e) => { setStationId(e.target.value); setPage(1); }}>
          <option value="">Todos os postos</option>
          {(stationsData?.items ?? []).map((s) => (
            <option key={s.id} value={s.id}>{s.trade_name}</option>
          ))}
        </select>
        <select className="rounded border px-2 py-2 text-sm" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          {STATUS_OPTIONS.map((s) => (
            <option key={s || "all"} value={s}>{s || "Todos os status"}</option>
          ))}
        </select>
        <select className="rounded border px-2 py-2 text-sm" value={syncMode} onChange={(e) => { setSyncMode(e.target.value); setPage(1); }}>
          <option value="">Todos os modos</option>
          <option value="FULL">FULL</option>
          <option value="FULL_SNAPSHOT_HASH">FULL_SNAPSHOT_HASH</option>
          <option value="INCREMENTAL_TIMESTAMP">INCREMENTAL_TIMESTAMP</option>
          <option value="INCREMENTAL_ID">INCREMENTAL_ID</option>
        </select>
        <select className="rounded border px-2 py-2 text-sm" value={triggerType} onChange={(e) => { setTriggerType(e.target.value); setPage(1); }}>
          <option value="">Todos os gatilhos</option>
          <option value="MANUAL">MANUAL</option>
          <option value="SCHEDULED">SCHEDULED</option>
          <option value="RETRY">RETRY</option>
          <option value="INITIAL_FULL">INITIAL_FULL</option>
        </select>
        <input type="date" className="rounded border px-2 py-2 text-sm" value={createdFrom} onChange={(e) => { setCreatedFrom(e.target.value); setPage(1); }} />
        <input type="date" className="rounded border px-2 py-2 text-sm" value={createdTo} onChange={(e) => { setCreatedTo(e.target.value); setPage(1); }} />
        <select className="rounded border px-2 py-2 text-sm" value={sortBy} onChange={(e) => setSortBy(e.target.value)}>
          <option value="created_at">Ordenar por criação</option>
          <option value="started_at">Ordenar por início</option>
        </select>
        <select className="rounded border px-2 py-2 text-sm" value={sortDir} onChange={(e) => setSortDir(e.target.value)}>
          <option value="desc">Descendente</option>
          <option value="asc">Ascendente</option>
        </select>
      </section>

      {isFetching && !isLoading && (
        <p className="text-xs text-slate-500">Atualizando lista…</p>
      )}

      {isLoading ? (
        <p className="text-sm text-slate-600">Carregando…</p>
      ) : (
        <>
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="py-2">Status</th>
                <th>Gatilho</th>
                <th>Modo</th>
                <th>Lidos</th>
                <th>Aplicados</th>
                <th>Erros</th>
                <th>Início</th>
              </tr>
            </thead>
            <tbody>
              {data?.items.map((run) => (
                <tr key={run.id} className="border-b border-slate-50">
                  <td className="py-2">
                    <Link className="text-blue-600 hover:underline" to={`/integrations/xpert/runs/${run.id}`}>
                      {run.status}
                      {ACTIVE_STATUSES.includes(run.status) ? " ●" : ""}
                    </Link>
                  </td>
                  <td>{run.trigger_type}</td>
                  <td>{run.sync_mode}</td>
                  <td>{run.rows_read}</td>
                  <td>{run.rows_applied}</td>
                  <td>{run.rows_error}</td>
                  <td>{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="flex items-center justify-between text-sm">
            <span>
              Página {data?.page ?? 1} de {totalPages} — {data?.total ?? 0} execuções
            </span>
            <div className="flex gap-2">
              <button type="button" className="rounded border px-3 py-1 disabled:opacity-40" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                Anterior
              </button>
              <button type="button" className="rounded border px-3 py-1 disabled:opacity-40" disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
                Próxima
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
