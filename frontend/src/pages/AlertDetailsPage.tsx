import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { fetchAlert } from "../api/executive";

export function AlertDetailsPage() {
  const { id = "" } = useParams();
  const q = useQuery({ queryKey: ["alert", id], queryFn: () => fetchAlert(id), enabled: Boolean(id) });
  const a = q.data;
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive/alerts">
        ← Alertas
      </Link>
      <h1 className="text-xl font-semibold">Detalhe do alerta</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {a ? (
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-slate-500">Código</dt>
            <dd>{String(a.alert_code)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Status</dt>
            <dd>{String(a.status)}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Severidade</dt>
            <dd>
              {String(a.severity)} / {String(a.priority)}
            </dd>
          </div>
          <div>
            <dt className="text-slate-500">Título</dt>
            <dd>{String(a.title)}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Resumo</dt>
            <dd>{String(a.summary)}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-slate-500">Descrição</dt>
            <dd>{String(a.description ?? "—")}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Dismissível</dt>
            <dd>{a.dismissible ? "sim" : "não (ex.: UNSAFE XPERT)"}</dd>
          </div>
          {a.deep_link ? (
            <div>
              <dt className="text-slate-500">Contexto</dt>
              <dd>
                <Link className="underline" to={String(a.deep_link)}>
                  Abrir
                </Link>
              </dd>
            </div>
          ) : null}
        </dl>
      ) : null}
    </div>
  );
}
