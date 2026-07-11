import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchAlertRules } from "../api/executive";

export function AlertRulesPage() {
  const q = useQuery({ queryKey: ["alert-rules"], queryFn: fetchAlertRules });
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive/alerts">
        ← Alertas
      </Link>
      <h1 className="text-xl font-semibold">Regras de alerta</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !(q.data?.length) ? (
        <p className="text-sm text-slate-500">Nenhuma regra. Crie via API ou use alertas sintéticos.</p>
      ) : null}
      <ul className="space-y-2 text-sm">
        {(q.data ?? []).map((r) => (
          <li key={String(r.id)} className="rounded border p-3">
            <div className="font-medium">
              {String(r.code)} — {String(r.name)}
            </div>
            <div className="text-slate-600">
              {String(r.metric_code)} {String(r.operator)} {String(r.threshold_value ?? "—")} ·{" "}
              {String(r.severity)} · {r.active ? "ativa" : "inativa"}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
