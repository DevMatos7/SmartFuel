import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import {
  confirmExternalImport,
  fetchExternalSeries,
  previewExternalImport,
} from "../api/external-indices";
import { useAuth } from "../auth/AuthProvider";

export function ExternalImportsPage() {
  const { hasPermission } = useAuth();
  const canImport = hasPermission("external_data.import");
  const qc = useQueryClient();
  const seriesQ = useQuery({ queryKey: ["external-series"], queryFn: fetchExternalSeries });
  const [seriesId, setSeriesId] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [previewId, setPreviewId] = useState<string | null>(null);
  const [previewRows, setPreviewRows] = useState<Array<Record<string, unknown>>>([]);

  const previewM = useMutation({
    mutationFn: async () => {
      if (!file || !seriesId) throw new Error("Selecione série e arquivo");
      const form = new FormData();
      form.append("series_id", seriesId);
      form.append("date_column", "date");
      form.append("value_column", "value");
      form.append("file", file);
      return previewExternalImport(form);
    },
    onSuccess: (data) => {
      setPreviewId(data.import_file_id);
      setPreviewRows(data.preview);
    },
  });

  const confirmM = useMutation({
    mutationFn: () => confirmExternalImport(previewId!),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["external-indices-summary"] });
      qc.invalidateQueries({ queryKey: ["external-runs"] });
    },
  });

  function onPreview(e: FormEvent) {
    e.preventDefault();
    previewM.mutate();
  }

  if (!canImport) {
    return <p className="text-sm text-slate-600">Sem permissão para importar.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Importação de índices</h1>
        <p className="text-sm text-slate-600">CSV → preview → confirmação. Nada é aplicado sem confirmação.</p>
      </div>
      <Link className="text-sm underline" to="/analytics/external-indices">
        Voltar
      </Link>

      <form onSubmit={onPreview} className="space-y-3 rounded border border-slate-200 p-4">
        <label className="block text-sm">
          Série
          <select
            className="mt-1 block w-full rounded border px-2 py-1"
            value={seriesId}
            onChange={(e) => setSeriesId(e.target.value)}
            required
          >
            <option value="">Selecione…</option>
            {(seriesQ.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.code} — {s.name}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Arquivo CSV (colunas date,value)
          <input
            type="file"
            accept=".csv"
            className="mt-1 block"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            required
          />
        </label>
        <button type="submit" className="rounded bg-slate-800 px-3 py-2 text-sm text-white" disabled={previewM.isPending}>
          Gerar preview
        </button>
      </form>

      {previewRows.length > 0 ? (
        <div className="space-y-3">
          <h2 className="font-medium">Preview</h2>
          <pre className="max-h-64 overflow-auto rounded bg-slate-50 p-3 text-xs">
            {JSON.stringify(previewRows.slice(0, 20), null, 2)}
          </pre>
          <button
            type="button"
            className="rounded bg-emerald-700 px-3 py-2 text-sm text-white"
            disabled={!previewId || confirmM.isPending}
            onClick={() => confirmM.mutate()}
          >
            Confirmar aplicação
          </button>
          {confirmM.isSuccess ? (
            <pre className="rounded bg-emerald-50 p-3 text-xs">{JSON.stringify(confirmM.data, null, 2)}</pre>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
