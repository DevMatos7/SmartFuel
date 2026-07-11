import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchFeatureFlags, fetchOperationsReadiness } from "../api/executive";

export function ProductionReadinessPage() {
  const q = useQuery({ queryKey: ["ops-readiness"], queryFn: fetchOperationsReadiness });
  const flagsQ = useQuery({ queryKey: ["feature-flags"], queryFn: fetchFeatureFlags });
  const r = q.data;
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive">
        ← Visão executiva
      </Link>
      <h1 className="text-xl font-semibold">Prontidão para produção</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {r ? (
        <>
          <p className="text-lg font-semibold">
            Status: {r.status}
            {r.reason ? <span className="ml-2 text-sm font-normal text-red-700">{r.reason}</span> : null}
          </p>
          <p className="text-sm text-slate-600">
            Produção com sa bloqueada: {String(r.production_with_sa_blocked)} · Scheduler bloqueado:{" "}
            {String(r.scheduler_blocked)}
          </p>
          <ul className="space-y-1 text-sm">
            {r.gates.map((g) => (
              <li key={g.gate} className="rounded border px-3 py-2">
                <span className="font-mono text-xs">{g.status}</span> · {g.gate}
                {g.reason ? <span className="text-slate-500"> ({g.reason})</span> : null}
              </li>
            ))}
          </ul>
        </>
      ) : null}
      <h2 className="text-sm font-semibold">Feature flags</h2>
      <ul className="text-sm">
        {(flagsQ.data ?? []).map((f) => (
          <li key={f.flag_code}>
            {f.flag_code}: {f.enabled ? "on" : "off"}
          </li>
        ))}
      </ul>
    </div>
  );
}
