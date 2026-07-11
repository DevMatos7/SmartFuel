import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchIncidents } from "../api/executive";

export function OperationalIncidentsPage() {
  const q = useQuery({ queryKey: ["ops-incidents"], queryFn: fetchIncidents });
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive">
        ← Visão executiva
      </Link>
      <h1 className="text-xl font-semibold">Incidentes</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !(q.data?.length) ? <p className="text-sm text-slate-500">Nenhum incidente.</p> : null}
      <ul className="space-y-2 text-sm">
        {(q.data ?? []).map((i) => (
          <li key={String(i.id)} className="rounded border p-3">
            [{String(i.severity)}] {String(i.title)} · {String(i.status)}
            {i.postmortem_required ? <span className="ml-2 text-amber-700">postmortem</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
