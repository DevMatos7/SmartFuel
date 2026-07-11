import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchExternalSeries } from "../api/external-indices";

export function ExternalSeriesPage() {
  const q = useQuery({ queryKey: ["external-series"], queryFn: fetchExternalSeries });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Séries externas</h1>
        <p className="text-sm text-slate-600">Frequência e unidade preservadas — sem preenchimento artificial de dias.</p>
      </div>
      <Link className="text-sm underline" to="/analytics/external-indices">
        Voltar ao dashboard
      </Link>
      {q.isLoading ? <p>Carregando…</p> : null}
      {q.isError ? <p className="text-red-700">Erro ao carregar séries.</p> : null}
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Código</th>
            <th>Nome</th>
            <th>Frequência</th>
            <th>Unidade</th>
            <th>Moeda</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(q.data ?? []).map((s) => (
            <tr key={s.id} className="border-b border-slate-100">
              <td className="py-2 font-mono text-xs">{s.code}</td>
              <td>{s.name}</td>
              <td>{s.frequency}</td>
              <td>{s.canonical_unit}</td>
              <td>{s.currency ?? "—"}</td>
              <td>
                <Link className="underline" to={`/analytics/external-indices/series/${s.id}`}>
                  Abrir
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!q.isLoading && (q.data?.length ?? 0) === 0 ? (
        <p className="text-sm text-slate-600">Nenhuma série cadastrada.</p>
      ) : null}
    </div>
  );
}
