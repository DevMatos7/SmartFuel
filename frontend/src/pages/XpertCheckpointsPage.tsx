import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  fetchXpertCheckpoints,
  fetchXpertDatasets,
  fetchXpertSources,
  resetXpertCheckpoint,
  type XpertCheckpoint,
} from "../api/xpert-integration";
import { useAuth } from "../auth/AuthProvider";

export function XpertCheckpointsPage() {
  const { hasPermission } = useAuth();
  const canReset = hasPermission("erp_sync.reset_checkpoint");
  const queryClient = useQueryClient();
  const [resetTarget, setResetTarget] = useState<XpertCheckpoint | null>(null);
  const [mode, setMode] = useState<"CLEAR" | "SET">("CLEAR");
  const [newValue, setNewValue] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: checkpoints = [], isLoading } = useQuery({
    queryKey: ["xpert-checkpoints"],
    queryFn: () => fetchXpertCheckpoints(),
  });
  const { data: sources = [] } = useQuery({
    queryKey: ["xpert-sources"],
    queryFn: fetchXpertSources,
  });
  const { data: datasets = [] } = useQuery({
    queryKey: ["xpert-datasets"],
    queryFn: () => fetchXpertDatasets(),
  });

  const resetMutation = useMutation({
    mutationFn: () =>
      resetXpertCheckpoint(resetTarget!.id, {
        mode,
        new_value: mode === "SET" ? newValue : undefined,
        reason,
      }),
    onSuccess: async () => {
      setResetTarget(null);
      setReason("");
      setNewValue("");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["xpert-checkpoints"] });
    },
    onError: (e: Error) => setError(e.message),
  });

  const sourceName = (id: string) => sources.find((s) => s.id === id)?.name ?? id.slice(0, 8);
  const datasetCode = (id: string) => datasets.find((d) => d.id === id)?.code ?? id.slice(0, 8);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Checkpoints XPERT</h1>
          <p className="text-sm text-slate-500">
            Estado incremental por fonte, dataset e posto. Reset incorreto pode reprocessar dados.
          </p>
        </div>
        <Link className="text-sm text-blue-600 hover:underline" to="/integrations/xpert">
          Dashboard
        </Link>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-600">Carregando checkpoints…</p>
      ) : checkpoints.length === 0 ? (
        <p className="text-sm text-slate-500">Nenhum checkpoint registrado ainda.</p>
      ) : (
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="border-b text-slate-500">
              <th className="py-2">Fonte</th>
              <th>Dataset</th>
              <th>Posto</th>
              <th>Tipo</th>
              <th>Valor</th>
              <th>Upper bound</th>
              <th>Último sucesso</th>
              {canReset && <th />}
            </tr>
          </thead>
          <tbody>
            {checkpoints.map((cp) => (
              <tr key={cp.id} className="border-b border-slate-50">
                <td className="py-2">{sourceName(cp.erp_source_id)}</td>
                <td>{datasetCode(cp.erp_dataset_id)}</td>
                <td>{cp.station_id ? cp.station_id.slice(0, 8) : "Global"}</td>
                <td>{cp.checkpoint_type}</td>
                <td className="font-mono text-xs">{cp.watermark_value ?? "—"}</td>
                <td className="font-mono text-xs">{cp.source_upper_bound ?? "—"}</td>
                <td>{cp.last_success_at ? new Date(cp.last_success_at).toLocaleString() : "—"}</td>
                {canReset && (
                  <td>
                    <button
                      type="button"
                      className="text-amber-700 hover:underline"
                      onClick={() => {
                        setResetTarget(cp);
                        setMode("CLEAR");
                        setReason("");
                        setError(null);
                      }}
                    >
                      Reset
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {resetTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-amber-800">Reset de checkpoint</h2>
            <p className="mt-2 text-sm text-slate-600">
              Isso pode reprocessar ou inativar dados na próxima sincronização. Confirme com atenção.
            </p>
            <div className="mt-4 space-y-3 text-sm">
              <label className="block">
                Modo
                <select
                  className="mt-1 w-full rounded border px-2 py-1"
                  value={mode}
                  onChange={(e) => setMode(e.target.value as "CLEAR" | "SET")}
                >
                  <option value="CLEAR">Limpar (próxima execução será full)</option>
                  <option value="SET">Definir novo valor</option>
                </select>
              </label>
              {mode === "SET" && (
                <label className="block">
                  Novo valor
                  <input
                    className="mt-1 w-full rounded border px-2 py-1 font-mono text-xs"
                    value={newValue}
                    onChange={(e) => setNewValue(e.target.value)}
                    placeholder="2026-07-09T12:00:00+00:00"
                  />
                </label>
              )}
              <label className="block">
                Motivo (obrigatório)
                <textarea
                  className="mt-1 w-full rounded border px-2 py-1"
                  rows={3}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  minLength={5}
                />
              </label>
            </div>
            {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded border px-3 py-1" onClick={() => setResetTarget(null)}>
                Cancelar
              </button>
              <button
                type="button"
                className="rounded bg-amber-700 px-3 py-1 text-white disabled:opacity-50"
                disabled={reason.trim().length < 5 || resetMutation.isPending || (mode === "SET" && !newValue.trim())}
                onClick={() => resetMutation.mutate()}
              >
                Confirmar reset
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
