import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchOperationsHealth } from "../api/executive";

export function OperationsHealthPage() {
  const q = useQuery({ queryKey: ["ops-health"], queryFn: fetchOperationsHealth });
  const components = (q.data?.components as Array<Record<string, unknown>>) ?? [];
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive">
        ← Visão executiva
      </Link>
      <h1 className="text-xl font-semibold">Saúde operacional</h1>
      <p className="text-sm text-slate-600">
        Overall: {String(q.data?.overall ?? "—")} · XPERT write:{" "}
        {String(q.data?.xpert_write_enabled ?? false)} · Scheduler bloqueado:{" "}
        {String(q.data?.scheduler_blocked_for_unsafe ?? true)}
      </p>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      <ul className="space-y-2 text-sm">
        {components.map((c) => (
          <li key={`${c.service}-${c.component}`} className="rounded border p-3">
            <div className="font-medium">
              {String(c.service)} / {String(c.component)}
            </div>
            <div>
              Status: <span className="font-mono">{String(c.status)}</span>
              {c.latency_ms != null ? ` · ${c.latency_ms} ms` : ""}
            </div>
            {c.service === "xpert" ? (
              <div className="mt-1 text-xs text-amber-700">
                Segurança UNSAFE · produção bloqueada · agenda bloqueada · somente leitura
              </div>
            ) : null}
          </li>
        ))}
      </ul>
      <Link className="text-sm underline" to="/executive/jobs">
        Jobs / outbox
      </Link>
    </div>
  );
}
