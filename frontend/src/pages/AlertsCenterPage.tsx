import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { acknowledgeAlert, fetchAlerts, fetchAlertsSummary, resolveAlert } from "../api/executive";
import { useAuth } from "../auth/AuthProvider";

export function AlertsCenterPage() {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const summaryQ = useQuery({ queryKey: ["alerts-summary"], queryFn: fetchAlertsSummary });
  const listQ = useQuery({ queryKey: ["alerts"], queryFn: () => fetchAlerts() });
  const ackM = useMutation({
    mutationFn: (id: string) => acknowledgeAlert(id, "Reconhecido na central"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });
  const resolveM = useMutation({
    mutationFn: (id: string) => resolveAlert(id, "Resolvido na central"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["alerts"] }),
  });

  const s = summaryQ.data;

  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive">
        ← Visão executiva
      </Link>
      <h1 className="text-xl font-semibold">Central de alertas</h1>
      <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-6 text-sm">
        <div className="rounded border p-2">Críticos: {s?.critical ?? "—"}</div>
        <div className="rounded border p-2">Altos: {s?.high ?? "—"}</div>
        <div className="rounded border p-2">Não reconhecidos: {s?.unacknowledged ?? "—"}</div>
        <div className="rounded border p-2">Vencidos: {s?.overdue ?? "—"}</div>
        <div className="rounded border p-2">Atribuídos: {s?.assigned_open ?? "—"}</div>
        <div className="rounded border p-2">Recorrentes: {s?.recurring ?? "—"}</div>
      </div>
      {listQ.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!listQ.isLoading && !(listQ.data?.length) ? (
        <p className="text-sm text-slate-500">Nenhum alerta. Execute homologação sintética.</p>
      ) : null}
      <ul className="space-y-2 text-sm">
        {(listQ.data ?? []).map((a) => (
          <li key={a.id} className="rounded border border-slate-200 bg-white p-3">
            <div className="flex flex-wrap items-start justify-between gap-2">
              <div>
                <Link className="font-medium underline" to={`/executive/alerts/${a.id}`}>
                  [{a.severity}/{a.priority}] {a.title}
                </Link>
                <div className="text-slate-600">{a.summary}</div>
                <div className="text-xs text-slate-500">
                  {a.alert_code} · {a.status} · ocorrências {a.occurrence_count}
                </div>
              </div>
              <div className="flex gap-2">
                {hasPermission("alerts.acknowledge") && a.status === "OPEN" ? (
                  <button type="button" className="rounded border px-2 py-1" onClick={() => ackM.mutate(a.id)}>
                    Reconhecer
                  </button>
                ) : null}
                {hasPermission("alerts.resolve") && a.dismissible ? (
                  <button
                    type="button"
                    className="rounded bg-slate-900 px-2 py-1 text-white"
                    onClick={() => resolveM.mutate(a.id)}
                  >
                    Resolver
                  </button>
                ) : null}
              </div>
            </div>
          </li>
        ))}
      </ul>
      <Link className="text-sm underline" to="/executive/alert-rules">
        Regras de alerta
      </Link>
    </div>
  );
}
