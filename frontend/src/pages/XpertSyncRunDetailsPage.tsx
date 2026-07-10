import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  cancelXpertRun,
  fetchXpertRun,
  fetchXpertRunErrors,
  fetchXpertRunStaging,
  retryXpertRun,
} from "../api/xpert-integration";
import { useAuth } from "../auth/AuthProvider";

const ACTIVE = ["QUEUED", "CONNECTING", "EXTRACTING", "STAGING", "VALIDATING", "APPLYING", "CANCELLATION_REQUESTED"];
const RETRYABLE = ["FAILED", "PARTIAL", "CANCELLED", "SKIPPED_LOCKED"];

export function XpertSyncRunDetailsPage() {
  const { runId = "" } = useParams();
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const canCancel = hasPermission("erp_sync.cancel");
  const canRetry = hasPermission("erp_sync.retry");
  const canViewStaging = hasPermission("erp_sync.view_staging");
  const canViewErrors = hasPermission("erp_sync.view_errors");

  const { data: run } = useQuery({
    queryKey: ["xpert-run", runId],
    queryFn: () => fetchXpertRun(runId),
    enabled: Boolean(runId),
    refetchInterval: (q) => (q.state.data && ACTIVE.includes(q.state.data.status) ? 5000 : false),
  });

  const { data: errors = [] } = useQuery({
    queryKey: ["xpert-run-errors", runId],
    queryFn: () => fetchXpertRunErrors(runId),
    enabled: Boolean(runId) && canViewErrors,
  });

  const { data: staging = [] } = useQuery({
    queryKey: ["xpert-run-staging", runId],
    queryFn: () => fetchXpertRunStaging(runId),
    enabled: Boolean(runId) && canViewStaging,
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelXpertRun(runId),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["xpert-run", runId] }),
  });

  const retryMutation = useMutation({
    mutationFn: () => retryXpertRun(runId),
    onSuccess: (data) => {
      const newRun = data.runs[0];
      if (newRun) navigate(`/integrations/xpert/runs/${newRun.id}`);
    },
  });

  if (!run) return <p className="text-sm text-slate-600">Carregando execução…</p>;

  const errorsByCode = errors.reduce<Record<string, number>>((acc, e) => {
    acc[e.error_code] = (acc[e.error_code] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Execução {run.status}</h1>
        <Link className="text-sm text-blue-600 hover:underline" to="/integrations/xpert/runs">
          Voltar
        </Link>
      </div>

      {run.error_code === "FAILED_WORKER_LOST" && (
        <p className="rounded border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900">
          Execução abandonada pelo worker. O checkpoint foi preservado. Use repetir para criar nova run.
        </p>
      )}

      <section className="grid gap-3 rounded-lg border border-slate-200 bg-white p-4 text-sm sm:grid-cols-3">
        <div><span className="text-slate-500">Trigger</span><p>{run.trigger_type}</p></div>
        <div><span className="text-slate-500">Modo</span><p>{run.sync_mode}</p></div>
        <div><span className="text-slate-500">Worker</span><p>{run.worker_id ?? "—"}</p></div>
        <div><span className="text-slate-500">Lidos</span><p>{run.rows_read}</p></div>
        <div><span className="text-slate-500">Staging</span><p>{run.rows_staged ?? "—"}</p></div>
        <div><span className="text-slate-500">Aplicados</span><p>{run.rows_applied}</p></div>
        <div><span className="text-slate-500">Inseridos</span><p>{run.rows_inserted ?? 0}</p></div>
        <div><span className="text-slate-500">Atualizados</span><p>{run.rows_updated ?? 0}</p></div>
        <div><span className="text-slate-500">Quarentena</span><p>{run.rows_quarantined}</p></div>
        <div><span className="text-slate-500">Checkpoint antes</span><p className="font-mono text-xs">{run.checkpoint_before ?? "—"}</p></div>
        <div><span className="text-slate-500">Checkpoint depois</span><p className="font-mono text-xs">{run.checkpoint_after ?? "—"}</p></div>
        <div><span className="text-slate-500">Upper bound</span><p className="font-mono text-xs">{run.source_upper_bound ?? "—"}</p></div>
        {run.error_message && (
          <div className="sm:col-span-3"><span className="text-slate-500">Erro</span><p className="text-red-700">{run.error_code}: {run.error_message}</p></div>
        )}
      </section>

      <div className="flex gap-2">
        {canCancel && ACTIVE.includes(run.status) && (
          <button type="button" className="rounded border px-3 py-1 text-sm" disabled={cancelMutation.isPending} onClick={() => cancelMutation.mutate()}>
            Cancelar
          </button>
        )}
        {canRetry && RETRYABLE.includes(run.status) && (
          <button type="button" className="rounded border px-3 py-1 text-sm" disabled={retryMutation.isPending} onClick={() => retryMutation.mutate()}>
            Repetir
          </button>
        )}
      </div>

      {canViewErrors && (
        <section>
          <h2 className="mb-2 text-lg font-medium">Erros</h2>
          {Object.keys(errorsByCode).length > 0 && (
            <div className="mb-3 flex flex-wrap gap-2 text-xs">
              {Object.entries(errorsByCode).map(([code, count]) => (
                <span key={code} className="rounded bg-slate-100 px-2 py-1">{code}: {count}</span>
              ))}
            </div>
          )}
          {errors.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhum erro registrado.</p>
          ) : (
            <ul className="max-h-64 space-y-2 overflow-auto text-sm">
              {errors.map((e) => (
                <li key={e.id} className="rounded border border-slate-100 p-2">
                  <strong>{e.error_code}</strong> ({e.phase}) — {e.message}
                  {e.source_key && <span className="ml-2 font-mono text-xs">{e.source_key}</span>}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      {canViewStaging && (
        <section>
          <h2 className="mb-2 text-lg font-medium">Staging ({staging.length})</h2>
          {staging.length === 0 ? (
            <p className="text-sm text-slate-500">Nenhum registro de staging.</p>
          ) : (
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b text-slate-500">
                  <th className="py-1">Chave</th>
                  <th>Status</th>
                  <th>Hash</th>
                  <th>Entidade</th>
                </tr>
              </thead>
              <tbody>
                {staging.slice(0, 100).map((s) => (
                  <tr key={s.id} className="border-b border-slate-50">
                    <td className="py-1 font-mono">{s.source_key}</td>
                    <td>{s.processing_status}</td>
                    <td className="font-mono">{s.record_hash?.slice(0, 10) ?? "—"}</td>
                    <td>{s.applied_entity_type ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      )}
    </div>
  );
}
