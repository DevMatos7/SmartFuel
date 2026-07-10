import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  createXpertSource,
  fetchXpertDatasets,
  fetchXpertSources,
  testXpertConnection,
  updateXpertDataset,
  updateXpertSource,
  validateXpertContract,
  type XpertDataset,
  type XpertSource,
  type XpertSourceInput,
} from "../api/xpert-integration";
import { useAuth } from "../auth/AuthProvider";

const EMPTY_SOURCE: XpertSourceInput = {
  code: "",
  name: "",
  host: "",
  port: 1433,
  database_name: "atxdados",
  driver_name: "ODBC Driver 18 for SQL Server",
  encrypt_connection: true,
  trust_server_certificate: true,
  secret_ref: "xpert_atx",
  source_timezone: "America/Cuiaba",
  enabled: false,
};

export function XpertSourcePage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("erp_integration.manage");
  const canTest = hasPermission("erp_integration.test");
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [form, setForm] = useState<XpertSourceInput>(EMPTY_SOURCE);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const { data: sources = [], refetch } = useQuery({
    queryKey: ["xpert-sources"],
    queryFn: fetchXpertSources,
  });

  const selected = sources.find((s) => s.id === selectedId) ?? sources[0] ?? null;

  function loadSource(source: XpertSource) {
    setSelectedId(source.id);
    setForm({
      code: source.code,
      name: source.name,
      host: source.host,
      port: source.port,
      database_name: source.database_name,
      driver_name: source.driver_name,
      encrypt_connection: source.encrypt_connection,
      trust_server_certificate: source.trust_server_certificate,
      secret_ref: source.secret_ref,
      source_timezone: source.source_timezone,
      enabled: source.enabled,
    });
  }

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (selected) {
        const { code: _c, ...patch } = form;
        return updateXpertSource(selected.id, patch);
      }
      return createXpertSource(form);
    },
    onSuccess: async (source) => {
      setMessage("Fonte salva com sucesso.");
      loadSource(source);
      await queryClient.invalidateQueries({ queryKey: ["xpert-sources"] });
    },
    onError: (e: Error) => setMessage(e.message),
  });

  async function handleTest() {
    if (!selected || !canTest) return;
    setTesting(true);
    setMessage(null);
    try {
      await testXpertConnection(selected.id);
      await refetch();
      setMessage("Teste de conexão concluído.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Falha no teste.");
    } finally {
      setTesting(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Fonte XPERT</h1>
        <Link className="text-sm text-blue-600 hover:underline" to="/integrations/xpert">
          Dashboard
        </Link>
      </div>

      {sources.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {sources.map((s) => (
            <button
              key={s.id}
              type="button"
              className={`rounded border px-3 py-1 text-sm ${selected?.id === s.id ? "border-slate-900 bg-slate-900 text-white" : ""}`}
              onClick={() => loadSource(s)}
            >
              {s.name}
            </button>
          ))}
        </div>
      )}

      {canManage && (
        <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <h2 className="mb-3 font-medium">{selected ? "Editar fonte" : "Nova fonte"}</h2>
          <div className="grid gap-3 sm:grid-cols-2">
            {!selected && (
              <label className="block">
                Código
                <input className="mt-1 w-full rounded border px-2 py-1" value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} />
              </label>
            )}
            <label className="block">
              Nome
              <input className="mt-1 w-full rounded border px-2 py-1" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label className="block">
              Host
              <input className="mt-1 w-full rounded border px-2 py-1" value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} />
            </label>
            <label className="block">
              Porta
              <input type="number" className="mt-1 w-full rounded border px-2 py-1" value={form.port} onChange={(e) => setForm({ ...form, port: Number(e.target.value) })} />
            </label>
            <label className="block">
              Banco
              <input className="mt-1 w-full rounded border px-2 py-1" value={form.database_name} onChange={(e) => setForm({ ...form, database_name: e.target.value })} />
            </label>
            <label className="block">
              Secret ref
              <input className="mt-1 w-full rounded border px-2 py-1" value={form.secret_ref} onChange={(e) => setForm({ ...form, secret_ref: e.target.value })} />
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.encrypt_connection} onChange={(e) => setForm({ ...form, encrypt_connection: e.target.checked })} />
              Criptografar conexão
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.trust_server_certificate} onChange={(e) => setForm({ ...form, trust_server_certificate: e.target.checked })} />
              Confiar certificado
            </label>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} />
              Habilitada
            </label>
          </div>
          <div className="mt-4 flex gap-2">
            <button type="button" className="rounded bg-slate-900 px-4 py-2 text-white" disabled={saveMutation.isPending} onClick={() => saveMutation.mutate()}>
              Salvar
            </button>
            {!selected && (
              <button type="button" className="rounded border px-4 py-2" onClick={() => { setSelectedId(null); setForm(EMPTY_SOURCE); }}>
                Limpar
              </button>
            )}
          </div>
        </section>
      )}

      {selected && (
        <section className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
          <dl className="grid gap-3 sm:grid-cols-2">
            <div><dt className="text-slate-500">Status</dt><dd>{selected.connection_status}</dd></div>
            <div><dt className="text-slate-500">Driver</dt><dd>{selected.driver_name}</dd></div>
            <div><dt className="text-slate-500">Timezone</dt><dd>{selected.source_timezone}</dd></div>
            <div><dt className="text-slate-500">Último teste</dt><dd>{selected.last_tested_at ? new Date(selected.last_tested_at).toLocaleString() : "—"}</dd></div>
          </dl>
          {canTest && (
            <button type="button" className="mt-4 rounded border px-4 py-2" disabled={testing} onClick={() => void handleTest()}>
              {testing ? "Testando…" : "Testar conexão"}
            </button>
          )}
          {selected.last_test_result && (
            <pre className="mt-4 max-h-48 overflow-auto rounded bg-slate-50 p-3 text-xs">{JSON.stringify(selected.last_test_result, null, 2)}</pre>
          )}
        </section>
      )}

      {message && <p className="text-sm text-slate-700">{message}</p>}
    </div>
  );
}

function DatasetRow({ dataset, canManage }: { dataset: XpertDataset; canManage: boolean }) {
  const queryClient = useQueryClient();
  const [overlap, setOverlap] = useState(dataset.overlap_seconds);
  const [batch, setBatch] = useState(dataset.batch_size);
  const [schedule, setSchedule] = useState(dataset.schedule_enabled);
  const [interval, setInterval] = useState(dataset.schedule_interval_minutes ?? 60);
  const [enabled, setEnabled] = useState(dataset.enabled);

  const saveMutation = useMutation({
    mutationFn: () =>
      updateXpertDataset(dataset.id, {
        overlap_seconds: overlap,
        batch_size: batch,
        schedule_enabled: schedule,
        schedule_interval_minutes: interval,
        enabled,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["xpert-datasets"] }),
  });

  const isStations = dataset.code === "STATIONS";

  return (
    <tr className="border-b border-slate-50 align-top">
      <td className="py-3 font-medium">{dataset.code}</td>
      <td>{dataset.contract_status}</td>
      <td className="font-mono text-xs">{dataset.query_hash?.slice(0, 12) ?? "—"}</td>
      <td>{dataset.sync_mode}</td>
      <td>{enabled ? "Sim" : "Não"}</td>
      <td className="space-y-2">
        {isStations ? (
          <span className="text-amber-700">Indisponível até validação DBA</span>
        ) : (
          <>
            {dataset.contract_status !== "VALID" && (
              <button type="button" className="block text-blue-600 hover:underline" onClick={() => void validateXpertContract(dataset.id).then(() => queryClient.invalidateQueries({ queryKey: ["xpert-datasets"] }))}>
                Validar contrato
              </button>
            )}
            {canManage && dataset.contract_status === "VALID" && (
              <div className="grid gap-1 text-xs">
                <label className="flex items-center gap-1">
                  <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />
                  Habilitado
                </label>
                <label>
                  Overlap (s)
                  <input type="number" className="ml-1 w-16 rounded border px-1" value={overlap} onChange={(e) => setOverlap(Number(e.target.value))} />
                </label>
                <label>
                  Batch
                  <input type="number" className="ml-1 w-16 rounded border px-1" value={batch} onChange={(e) => setBatch(Number(e.target.value))} />
                </label>
                <label className="flex items-center gap-1">
                  <input type="checkbox" checked={schedule} onChange={(e) => setSchedule(e.target.checked)} />
                  Agenda ({interval} min)
                </label>
                {schedule && (
                  <input type="number" className="w-20 rounded border px-1" value={interval} onChange={(e) => setInterval(Number(e.target.value))} />
                )}
                <button type="button" className="text-left text-blue-600 hover:underline" onClick={() => saveMutation.mutate()}>
                  Salvar configuração
                </button>
              </div>
            )}
          </>
        )}
      </td>
    </tr>
  );
}

export function XpertDatasetsPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("erp_integration.manage");

  const { data: datasets = [] } = useQuery({
    queryKey: ["xpert-datasets"],
    queryFn: () => fetchXpertDatasets(),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Datasets XPERT</h1>
        <Link className="text-sm text-blue-600 hover:underline" to="/integrations/xpert">
          Dashboard
        </Link>
      </div>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Código</th>
            <th>Contrato</th>
            <th>Hash</th>
            <th>Modo</th>
            <th>Ativo</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          {datasets.map((d) => (
            <DatasetRow key={d.id} dataset={d} canManage={canManage} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
