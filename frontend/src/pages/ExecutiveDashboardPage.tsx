import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  fetchAlertsSummary,
  fetchExecutiveSummary,
  runExecutiveSynthetic,
} from "../api/executive";
import { useAuth } from "../auth/AuthProvider";

function qualityLabel(q: string) {
  return q.replaceAll("_", " ");
}

export function ExecutiveDashboardPage() {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const summaryQ = useQuery({ queryKey: ["executive-summary"], queryFn: fetchExecutiveSummary });
  const alertsQ = useQuery({ queryKey: ["alerts-summary"], queryFn: fetchAlertsSummary });
  const synthM = useMutation({
    mutationFn: () => runExecutiveSynthetic(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["executive-summary"] });
      qc.invalidateQueries({ queryKey: ["alerts-summary"] });
      qc.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const cards = summaryQ.data?.cards ?? [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Visão executiva</h1>
          <p className="text-sm text-slate-600">
            KPIs com qualidade e freshness · ausência de dados ≠ zero · XPERT somente leitura
          </p>
        </div>
        {hasPermission("executive_dashboard.read") ? (
          <button
            type="button"
            className="rounded bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
            disabled={synthM.isPending}
            onClick={() => synthM.mutate()}
          >
            Homologação sintética
          </button>
        ) : null}
      </div>

      {summaryQ.data?.disclaimer ? (
        <p className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm">{summaryQ.data.disclaimer}</p>
      ) : null}

      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="underline" to="/executive/stations">
          Postos
        </Link>
        <Link className="underline" to="/executive/alerts">
          Alertas
        </Link>
        <Link className="underline" to="/executive/health">
          Saúde
        </Link>
        <Link className="underline" to="/executive/slo">
          SLO
        </Link>
        <Link className="underline" to="/executive/incidents">
          Incidentes
        </Link>
        <Link className="underline" to="/executive/quality">
          Qualidade
        </Link>
        <Link className="underline" to="/executive/readiness">
          Prontidão
        </Link>
      </div>

      {alertsQ.data ? (
        <p className="text-sm text-slate-600">
          Críticos: {alertsQ.data.critical ?? 0} · Altos: {alertsQ.data.high ?? 0} · Não
          reconhecidos: {alertsQ.data.unacknowledged ?? 0}
        </p>
      ) : null}

      {summaryQ.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {summaryQ.data?.empty ? (
        <p className="text-sm text-slate-500">
          Sem snapshots ({summaryQ.data.empty_reason}). Execute a homologação sintética.
        </p>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.metric_code} className="rounded border border-slate-200 bg-white p-3">
            <div className="text-xs text-slate-500">{c.label || c.metric_code}</div>
            <div className="mt-1 text-lg font-semibold">
              {c.value ?? c.empty_reason ?? "NO_DATA"}
              {c.value && c.unit ? <span className="ml-1 text-xs font-normal text-slate-500">{c.unit}</span> : null}
            </div>
            <div className="mt-2 space-y-0.5 text-xs text-slate-500">
              <div>Qualidade: {qualityLabel(c.quality_status)}</div>
              <div>Freshness: {qualityLabel(c.freshness_status)}</div>
              <div>Cobertura: {c.coverage_percentage ?? "—"}</div>
              <div>Atualizado: {c.updated_at ? new Date(c.updated_at).toLocaleString() : "—"}</div>
              <Link className="underline" to={c.deep_link}>
                Detalhar
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
