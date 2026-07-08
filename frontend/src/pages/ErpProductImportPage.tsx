import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  cancelImportJob,
  confirmImportJob,
  IMPORT_STATUS_LABELS,
  uploadErpProductsImport,
  type MasterDataImportJobDetail,
} from "../api/master-data";
import { ImportPreviewTable } from "../components/master-data/ImportPreviewTable";
import { useAuth } from "../auth/AuthProvider";

type Step = 1 | 2 | 3 | 4;

export function ErpProductImportPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const stations = user?.stations.filter((s) => s.active) ?? [];

  const [step, setStep] = useState<Step>(1);
  const [stationId, setStationId] = useState(localStorage.getItem("active_station_id") ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [job, setJob] = useState<MasterDataImportJobDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: () => uploadErpProductsImport(stationId, file!),
    onSuccess: (result) => {
      setJob(result);
      setError(null);
      setStep(3);
    },
    onError: (err: Error) => setError(err.message),
  });

  const confirmMutation = useMutation({
    mutationFn: () => confirmImportJob(job!.id),
    onSuccess: async (result) => {
      setJob((prev) => (prev ? { ...prev, ...result } : prev));
      setError(null);
      setStep(4);
      await queryClient.invalidateQueries({ queryKey: ["erp-products"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const cancelMutation = useMutation({
    mutationFn: () => cancelImportJob(job!.id),
    onSuccess: () => {
      setJob(null);
      setFile(null);
      setStep(1);
    },
  });

  const steps = [
    { num: 1, label: "Posto e arquivo" },
    { num: 2, label: "Validação" },
    { num: 3, label: "Pré-visualização" },
    { num: 4, label: "Conclusão" },
  ];

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Importar produtos ERP</h1>
          <p className="text-sm text-slate-500">Envie um arquivo CSV para sincronizar produtos do ERP.</p>
        </div>
        <Link to="/erp-products" className="text-sm underline">
          Voltar para produtos ERP
        </Link>
      </div>

      <ol className="mt-6 flex flex-wrap gap-2">
        {steps.map((s) => (
          <li
            key={s.num}
            className={`rounded-full px-3 py-1 text-xs ${
              step >= s.num ? "bg-slate-900 text-white" : "bg-slate-100 text-slate-600"
            }`}
          >
            {s.num}. {s.label}
          </li>
        ))}
      </ol>

      {error && (
        <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      {step === 1 && (
        <section className="mt-6 space-y-4">
          <div>
            <label className="text-sm font-medium" htmlFor="import-station">
              Posto
            </label>
            <select
              id="import-station"
              className="mt-1 w-full max-w-md rounded border border-slate-300 px-3 py-2 text-sm"
              value={stationId}
              onChange={(e) => setStationId(e.target.value)}
            >
              <option value="">Selecione...</option>
              {stations.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.trade_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="import-file">
              Arquivo CSV
            </label>
            <input
              id="import-file"
              type="file"
              accept=".csv,text/csv"
              className="mt-1 block text-sm"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </div>
          <button
            type="button"
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
            disabled={!stationId || !file}
            onClick={() => setStep(2)}
          >
            Continuar
          </button>
        </section>
      )}

      {step === 2 && (
        <section className="mt-6 space-y-4">
          <p className="text-sm text-slate-600">
            Posto: {stations.find((s) => s.id === stationId)?.trade_name ?? stationId}
            <br />
            Arquivo: {file?.name}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              className="rounded border border-slate-300 px-4 py-2 text-sm"
              onClick={() => setStep(1)}
            >
              Voltar
            </button>
            <button
              type="button"
              className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
              disabled={uploadMutation.isPending}
              onClick={() => uploadMutation.mutate()}
            >
              {uploadMutation.isPending ? "Validando..." : "Enviar e validar"}
            </button>
          </div>
        </section>
      )}

      {step === 3 && job && (
        <section className="mt-6 space-y-4">
          <dl className="grid gap-2 text-sm md:grid-cols-3">
            <div>
              <dt className="text-slate-500">Status</dt>
              <dd className="font-medium">{IMPORT_STATUS_LABELS[job.status] ?? job.status}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Total de linhas</dt>
              <dd className="font-medium">{job.records_total}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Válidas</dt>
              <dd className="font-medium">{job.records_valid}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Com falha</dt>
              <dd className="font-medium">{job.records_failed}</dd>
            </div>
          </dl>

          <ImportPreviewTable rows={job.rows} />

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
              disabled={confirmMutation.isPending || job.status !== "READY"}
              onClick={() => confirmMutation.mutate()}
            >
              {confirmMutation.isPending ? "Confirmando..." : "Confirmar importação"}
            </button>
            <button
              type="button"
              className="rounded border border-slate-300 px-4 py-2 text-sm disabled:opacity-60"
              disabled={cancelMutation.isPending}
              onClick={() => cancelMutation.mutate()}
            >
              Cancelar
            </button>
          </div>
        </section>
      )}

      {step === 4 && job && (
        <section className="mt-6 space-y-4">
          <div className="rounded bg-green-50 px-4 py-3 text-sm text-green-900">
            Importação concluída com status: {IMPORT_STATUS_LABELS[job.status] ?? job.status}.
          </div>
          <dl className="grid gap-2 text-sm md:grid-cols-4">
            <div>
              <dt className="text-slate-500">Inseridos</dt>
              <dd>{job.records_inserted}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Atualizados</dt>
              <dd>{job.records_updated}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Sem alteração</dt>
              <dd>{job.records_unchanged}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Falhas</dt>
              <dd>{job.records_failed}</dd>
            </div>
          </dl>
          <Link to="/erp-products" className="inline-block rounded bg-slate-900 px-4 py-2 text-sm text-white">
            Ir para produtos ERP
          </Link>
        </section>
      )}
    </div>
  );
}
