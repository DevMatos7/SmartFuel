import { useMutation, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  createXpertSyncRuns,
  fetchXpertCheckpoints,
  fetchXpertDatasets,
  fetchXpertRuns,
  fetchXpertSources,
  type XpertDataset,
} from "../api/xpert-integration";
import { fetchStations } from "../api/stations";
import { useAuth } from "../auth/AuthProvider";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";

const FULL_MODES = ["FULL", "FULL_SNAPSHOT_HASH"];
const INCREMENTAL_MODES = ["INCREMENTAL_TIMESTAMP", "INCREMENTAL_ID"];

function isFullMode(mode: string) {
  return FULL_MODES.includes(mode);
}

function defaultHistoryRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return {
    history_start_date: from.toISOString().slice(0, 10),
    history_end_date: to.toISOString().slice(0, 10),
  };
}

export function XpertManualSyncPage() {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canRun = hasPermission("erp_sync.run");

  const [sourceId, setSourceId] = useState("");
  const [datasetCode, setDatasetCode] = useState("");
  const [stationIds, setStationIds] = useState<string[]>([]);
  const [syncMode, setSyncMode] = useState("FULL_SNAPSHOT_HASH");
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [unsafeConfirmOpen, setUnsafeConfirmOpen] = useState(false);
  const [unsafeAck, setUnsafeAck] = useState(false);
  const [unsafePhrase, setUnsafePhrase] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [historyRange, setHistoryRange] = useState(defaultHistoryRange);

  const { data: sources = [] } = useQuery({
    queryKey: ["xpert-sources"],
    queryFn: fetchXpertSources,
  });

  const { data: datasets = [] } = useQuery({
    queryKey: ["xpert-datasets", sourceId],
    queryFn: () => fetchXpertDatasets(sourceId),
    enabled: Boolean(sourceId),
  });

  const { data: stationsData } = useQuery({
    queryKey: ["stations-sync"],
    queryFn: () => fetchStations({ page_size: 200, active: true }),
  });

  const selectedSource = sources.find((s) => s.id === sourceId) ?? null;
  const selectedDataset = datasets.find((d) => d.code === datasetCode) ?? null;
  const isUnsafeSource = selectedSource?.security_status === "UNSAFE";
  const primaryStationId = stationIds[0] ?? "";

  const { data: checkpoints = [] } = useQuery({
    queryKey: ["xpert-checkpoints", sourceId, selectedDataset?.id, primaryStationId],
    queryFn: () =>
      fetchXpertCheckpoints({
        source_id: sourceId,
        dataset_id: selectedDataset?.id ?? "",
        station_id: primaryStationId,
      }),
    enabled: Boolean(sourceId && selectedDataset?.id && primaryStationId),
  });

  const { data: completedFull } = useQuery({
    queryKey: ["xpert-full-runs", selectedDataset?.id, primaryStationId],
    queryFn: () =>
      fetchXpertRuns({
        dataset_id: selectedDataset?.id ?? "",
        station_id: primaryStationId,
        status: "COMPLETED",
        sync_mode: "FULL_SNAPSHOT_HASH",
        page_size: "1",
      }),
    enabled: Boolean(selectedDataset?.id && primaryStationId),
  });

  const stations = useMemo(
    () => (stationsData?.items ?? []).filter((s) => s.erp_branch_id),
    [stationsData],
  );

  const checkpoint = checkpoints[0] ?? null;
  const lastFullAt = completedFull?.items[0]?.finished_at ?? null;

  const stationsBlocked = datasetCode === "STATIONS";
  const isFuelSales = datasetCode === "FUEL_SALES_ITEMS";
  const needsHistoryWindow =
    isFuelSales && INCREMENTAL_MODES.includes(syncMode) && !checkpoint?.watermark_value;
  const contractInvalid = selectedDataset != null && selectedDataset.contract_status !== "VALID";
  const incrementalBlocked =
    INCREMENTAL_MODES.includes(syncMode) &&
    !isFuelSales &&
    !lastFullAt &&
    (completedFull?.total ?? 0) === 0;
  const historyWindowIncomplete =
    needsHistoryWindow && (!historyRange.history_start_date || !historyRange.history_end_date);

  const allowedModes = useMemo(() => {
    if (!selectedDataset) return FULL_MODES;
    const modes = [...FULL_MODES];
    if (selectedDataset.sync_mode && INCREMENTAL_MODES.includes(selectedDataset.sync_mode)) {
      modes.push(selectedDataset.sync_mode);
    } else {
      modes.push("INCREMENTAL_TIMESTAMP", "INCREMENTAL_ID");
    }
    return [...new Set(modes)];
  }, [selectedDataset]);

  const createMutation = useMutation({
    mutationFn: () =>
      createXpertSyncRuns({
        source_id: sourceId,
        dataset_codes: [datasetCode],
        station_ids: stationIds,
        sync_mode: syncMode,
        unsafe_homologation_acknowledged: isUnsafeSource ? unsafeAck : undefined,
        history_start_date: needsHistoryWindow ? historyRange.history_start_date : undefined,
        history_end_date: needsHistoryWindow ? historyRange.history_end_date : undefined,
      }),
    onSuccess: () => navigate("/integrations/xpert/runs"),
    onError: (e: Error) => setError(e.message),
  });

  function toggleStation(id: string) {
    setStationIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function handleSubmit() {
    setError(null);
    if (!canRun) return;
    if (stationsBlocked) {
      setError("Dataset STATIONS permanece bloqueado.");
      return;
    }
    if (contractInvalid) {
      setError("Contrato do dataset não validado.");
      return;
    }
    if (historyWindowIncomplete) {
      setError("Informe o período histórico (início e fim) para a primeira carga de vendas.");
      return;
    }
    if (incrementalBlocked) {
      setError("Incremental requer uma carga completa anterior concluída.");
      return;
    }
    if (isUnsafeSource) {
      setUnsafeConfirmOpen(true);
      return;
    }
    if (isFullMode(syncMode)) {
      setConfirmOpen(true);
      return;
    }
    createMutation.mutate();
  }

  if (!canRun) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Sincronização manual</h1>
        <p className="text-sm text-red-600">Você não possui permissão para executar sincronizações.</p>
      </div>
    );
  }

  const stationLabel = stations.find((s) => s.id === primaryStationId);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Sincronização manual</h1>
        <Link className="text-sm text-blue-600 hover:underline" to="/integrations/xpert/runs">
          Execuções
        </Link>
      </div>

      <XpertUnsafeSourceBanner securityStatus={selectedSource?.security_status} />

      <section className="grid gap-4 rounded-lg border border-slate-200 bg-white p-4 md:grid-cols-2">
        <label className="block text-sm">
          <span className="text-slate-600">Fonte</span>
          <select
            aria-label="Fonte"
            className="mt-1 w-full rounded border px-3 py-2"
            value={sourceId}
            onChange={(e) => {
              setSourceId(e.target.value);
              setDatasetCode("");
            }}
          >
            <option value="">Selecione…</option>
            {sources.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name} ({s.connection_status})
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm">
          <span className="text-slate-600">Dataset</span>
          <select
            aria-label="Dataset"
            className="mt-1 w-full rounded border px-3 py-2"
            value={datasetCode}
            onChange={(e) => setDatasetCode(e.target.value)}
            disabled={!sourceId}
          >
            <option value="">Selecione…</option>
            {datasets.map((d: XpertDataset) => (
              <option key={d.id} value={d.code} disabled={d.code === "STATIONS"}>
                {d.name} — {d.contract_status}
              </option>
            ))}
          </select>
        </label>

        <label className="block text-sm md:col-span-2">
          <span className="text-slate-600">Modo</span>
          <select
            aria-label="Modo de sincronização"
            className="mt-1 w-full rounded border px-3 py-2"
            value={syncMode}
            onChange={(e) => setSyncMode(e.target.value)}
          >
            {allowedModes.map((mode) => (
              <option key={mode} value={mode}>
                {mode}
              </option>
            ))}
          </select>
        </label>

        <div className="md:col-span-2">
          <p className="mb-2 text-sm text-slate-600">Postos (erp_branch_id obrigatório)</p>
          <div className="flex flex-wrap gap-2">
            {stations.map((s) => (
              <label key={s.id} className="flex items-center gap-2 rounded border px-3 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={stationIds.includes(s.id)}
                  onChange={() => toggleStation(s.id)}
                />
                {s.trade_name} ({s.erp_branch_id})
              </label>
            ))}
          </div>
        </div>

        {needsHistoryWindow && (
          <div className="grid gap-4 md:col-span-2 md:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-600">Início do histórico</span>
              <input
                type="date"
                className="mt-1 w-full rounded border px-3 py-2"
                value={historyRange.history_start_date}
                onChange={(e) =>
                  setHistoryRange((prev) => ({ ...prev, history_start_date: e.target.value }))
                }
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-600">Fim do histórico</span>
              <input
                type="date"
                className="mt-1 w-full rounded border px-3 py-2"
                value={historyRange.history_end_date}
                onChange={(e) =>
                  setHistoryRange((prev) => ({ ...prev, history_end_date: e.target.value }))
                }
              />
            </label>
            <p className="text-xs text-amber-700 md:col-span-2">
              Primeira carga de vendas: use inicialmente 30 dias e um posto de homologação.
            </p>
          </div>
        )}
      </section>

      {selectedDataset && primaryStationId && (
        <section className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm">
          <p>
            <span className="text-slate-500">Checkpoint atual:</span>{" "}
            {checkpoint?.watermark_value ?? "—"}
          </p>
          <p>
            <span className="text-slate-500">Última full concluída:</span>{" "}
            {lastFullAt ? new Date(lastFullAt).toLocaleString() : "Nenhuma"}
          </p>
          {stationsBlocked && (
            <p className="mt-2 text-amber-700">STATIONS bloqueado até validação do DBA.</p>
          )}
          {contractInvalid && (
            <p className="mt-2 text-amber-700">Contrato inválido ou pendente de validação.</p>
          )}
          {incrementalBlocked && (
            <p className="mt-2 text-amber-700">Incremental bloqueado sem full anterior.</p>
          )}
          {needsHistoryWindow && (
            <p className="mt-2 text-amber-700">
              Primeira carga incremental de vendas — informe o período histórico abaixo.
            </p>
          )}
        </section>
      )}

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="button"
        className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
        disabled={
          !sourceId ||
          !datasetCode ||
          stationIds.length === 0 ||
          stationsBlocked ||
          contractInvalid ||
          incrementalBlocked ||
          historyWindowIncomplete ||
          createMutation.isPending
        }
        onClick={handleSubmit}
      >
        {createMutation.isPending ? "Criando…" : "Iniciar sincronização"}
      </button>

      {unsafeConfirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-w-lg rounded-lg bg-white p-6 shadow-lg">
            <h2 className="text-lg font-semibold text-red-800">Fonte XPERT insegura</h2>
            <p className="mt-3 text-sm text-slate-700">
              A fonte XPERT está configurada com privilégios administrativos. A aplicação executará
              apenas consultas SELECT validadas, porém a conta possui permissões de escrita no ERP.
            </p>
            <label className="mt-4 flex items-start gap-2 text-sm">
              <input type="checkbox" checked={unsafeAck} onChange={(e) => setUnsafeAck(e.target.checked)} />
              <span>Reconheço que esta fonte está classificada como insegura.</span>
            </label>
            <label className="mt-3 block text-sm">
              <span className="text-slate-600">Digite: CONFIRMAR HOMOLOGAÇÃO XPERT</span>
              <input
                className="mt-1 w-full rounded border px-3 py-2"
                value={unsafePhrase}
                onChange={(e) => setUnsafePhrase(e.target.value)}
              />
            </label>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded border px-3 py-2 text-sm" onClick={() => setUnsafeConfirmOpen(false)}>
                Cancelar
              </button>
              <button
                type="button"
                className="rounded bg-red-700 px-3 py-2 text-sm text-white disabled:opacity-50"
                disabled={!unsafeAck || unsafePhrase !== "CONFIRMAR HOMOLOGAÇÃO XPERT"}
                onClick={() => {
                  setUnsafeConfirmOpen(false);
                  if (isFullMode(syncMode)) setConfirmOpen(true);
                  else createMutation.mutate();
                }}
              >
                Continuar
              </button>
            </div>
          </div>
        </div>
      )}

      {confirmOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="max-w-lg rounded-lg bg-white p-6 shadow-lg">
            <h2 className="text-lg font-semibold">Confirmar sincronização completa</h2>
            <p className="mt-3 text-sm text-slate-700">
              Você iniciará uma sincronização completa de <strong>{datasetCode}</strong>
              {stationLabel ? ` para o posto ${stationLabel.erp_branch_id}` : ""}.
            </p>
            <ul className="mt-3 list-disc space-y-1 pl-5 text-sm text-slate-600">
              <li>A operação será somente leitura no XPERT.</li>
              <li>Registros novos poderão entrar na fila de mapeamento.</li>
              <li>
                Registros ausentes poderão ser marcados como inativos na origem após a conclusão
                integral da execução.
              </li>
            </ul>
            <div className="mt-4 flex justify-end gap-2">
              <button type="button" className="rounded border px-3 py-2 text-sm" onClick={() => setConfirmOpen(false)}>
                Cancelar
              </button>
              <button
                type="button"
                className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
                onClick={() => {
                  setConfirmOpen(false);
                  createMutation.mutate();
                }}
              >
                Confirmar
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
