import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchOperationsJobs } from "../api/executive";

export function OperationalJobsPage() {
  const q = useQuery({ queryKey: ["ops-jobs"], queryFn: fetchOperationsJobs });
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive/health">
        ← Saúde
      </Link>
      <h1 className="text-xl font-semibold">Jobs operacionais</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !(q.data?.length) ? <p className="text-sm text-slate-500">Nenhum evento de outbox.</p> : null}
      <ul className="space-y-2 text-sm">
        {(q.data ?? []).map((j) => (
          <li key={String(j.id)} className="rounded border p-3">
            {String(j.job_type)} · {String(j.status)}
            {j.stuck ? <span className="ml-2 text-red-700">STUCK</span> : null}
            <div className="text-xs text-slate-500">tentativas {String(j.attempt_count)}</div>
          </li>
        ))}
      </ul>
    </div>
  );
}
