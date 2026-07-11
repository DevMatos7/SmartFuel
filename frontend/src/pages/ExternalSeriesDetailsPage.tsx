import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { createManualObservation, fetchSeriesObservations } from "../api/external-indices";
import { useAuth } from "../auth/AuthProvider";

export function ExternalSeriesDetailsPage() {
  const { id = "" } = useParams();
  const { hasPermission } = useAuth();
  const canImport = hasPermission("external_data.import");
  const qc = useQueryClient();
  const [date, setDate] = useState("");
  const [value, setValue] = useState("");

  const obsQ = useQuery({
    queryKey: ["external-obs", id],
    queryFn: () => fetchSeriesObservations(id),
    enabled: Boolean(id),
  });

  const createM = useMutation({
    mutationFn: () =>
      createManualObservation(id, {
        observation_datetime: new Date(`${date}T12:00:00Z`).toISOString(),
        value,
        published_at: new Date(`${date}T12:00:00Z`).toISOString(),
      }),
    onSuccess: () => {
      setValue("");
      qc.invalidateQueries({ queryKey: ["external-obs", id] });
      qc.invalidateQueries({ queryKey: ["external-indices-summary"] });
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!date || !value) return;
    createM.mutate();
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Detalhe da série</h1>
        <p className="text-sm text-slate-600">observation_datetime ≠ fetched_at</p>
      </div>
      <Link className="text-sm underline" to="/analytics/external-indices/series">
        Voltar
      </Link>

      {canImport ? (
        <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3 rounded border border-slate-200 p-4">
          <label className="text-sm">
            Data econômica
            <input
              type="date"
              className="mt-1 block rounded border px-2 py-1"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              required
            />
          </label>
          <label className="text-sm">
            Valor
            <input
              className="mt-1 block rounded border px-2 py-1"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="ex: 78,45"
              required
            />
          </label>
          <button type="submit" className="rounded bg-slate-800 px-3 py-2 text-sm text-white" disabled={createM.isPending}>
            Registrar observação
          </button>
          {createM.isSuccess ? (
            <span className="text-sm text-emerald-700">Resultado: {String((createM.data as { result?: string })?.result)}</span>
          ) : null}
        </form>
      ) : null}

      {obsQ.isLoading ? <p>Carregando…</p> : null}
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Data econômica</th>
            <th>Valor</th>
            <th>Unidade</th>
            <th>Publicado</th>
            <th>Coletado</th>
            <th>Rev.</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {(obsQ.data ?? []).map((o) => (
            <tr key={o.id} className="border-b border-slate-100">
              <td className="py-2">{o.observation_datetime}</td>
              <td>{o.canonical_value}</td>
              <td>{o.canonical_unit}</td>
              <td>{o.published_at ?? "—"}</td>
              <td>{o.fetched_at}</td>
              <td>{o.revision_number}</td>
              <td>{o.revision_status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!obsQ.isLoading && (obsQ.data?.length ?? 0) === 0 ? (
        <p className="text-sm text-slate-600">Sem observações.</p>
      ) : null}
    </div>
  );
}
