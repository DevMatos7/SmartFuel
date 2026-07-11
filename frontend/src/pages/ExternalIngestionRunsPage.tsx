import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchIngestionRuns } from "../api/external-indices";

export function ExternalIngestionRunsPage() {
  const q = useQuery({ queryKey: ["external-runs"], queryFn: fetchIngestionRuns });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Execuções de ingestão</h1>
      </div>
      <Link className="text-sm underline" to="/analytics/external-indices">
        Voltar
      </Link>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Início</th>
            <th>Trigger</th>
            <th>Status</th>
            <th>Lidos</th>
            <th>Inseridos</th>
            <th>Revisados</th>
            <th>Iguais</th>
            <th>Rejeitados</th>
          </tr>
        </thead>
        <tbody>
          {(q.data ?? []).map((r) => (
            <tr key={r.id} className="border-b border-slate-100">
              <td className="py-2">{r.started_at}</td>
              <td>{r.trigger_type}</td>
              <td>{r.status}</td>
              <td>{r.records_read}</td>
              <td>{r.records_inserted}</td>
              <td>{r.records_revised}</td>
              <td>{r.records_unchanged}</td>
              <td>{r.records_rejected}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
