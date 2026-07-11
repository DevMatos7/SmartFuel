import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchExternalSources } from "../api/external-indices";

export function ExternalDataSourcesPage() {
  const q = useQuery({ queryKey: ["external-sources"], queryFn: fetchExternalSources });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Fontes externas</h1>
        <p className="text-sm text-slate-600">
          CSOnline permanece MISCONFIGURED até contrato autorizado. Scheduler exige homologação.
        </p>
      </div>
      <Link className="text-sm underline" to="/analytics/external-indices">
        Voltar
      </Link>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Código</th>
            <th>Nome</th>
            <th>Tipo</th>
            <th>Status</th>
            <th>Conector</th>
            <th>Agenda</th>
          </tr>
        </thead>
        <tbody>
          {(q.data ?? []).map((s) => (
            <tr key={s.id} className="border-b border-slate-100">
              <td className="py-2 font-mono text-xs">{s.code}</td>
              <td>{s.name}</td>
              <td>{s.source_type}</td>
              <td>{s.status}</td>
              <td>{s.connector_status}</td>
              <td>{s.scheduler_enabled ? "ON" : "OFF"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
