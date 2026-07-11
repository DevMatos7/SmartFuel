import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { bootstrapExternalCatalog, fetchExternalIndicesSummary } from "../api/external-indices";
import { useAuth } from "../auth/AuthProvider";

export function ExternalIndicesDashboardPage() {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const canManage = hasPermission("external_data.manage_sources");

  const summaryQ = useQuery({
    queryKey: ["external-indices-summary"],
    queryFn: fetchExternalIndicesSummary,
  });

  const seedM = useMutation({
    mutationFn: bootstrapExternalCatalog,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["external-indices-summary"] }),
  });

  const s = summaryQ.data;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Índices externos</h1>
          <p className="text-sm text-slate-600">
            Coleta, histórico e freshness — sem correlação ou recomendação (Sprint 10 fora de escopo)
          </p>
        </div>
        {canManage ? (
          <button
            type="button"
            className="rounded bg-slate-800 px-3 py-2 text-sm text-white"
            onClick={() => seedM.mutate()}
            disabled={seedM.isPending}
          >
            Inicializar catálogo padrão
          </button>
        ) : null}
      </div>

      <p className="rounded border border-slate-200 bg-slate-50 p-3 text-sm text-slate-700">
        {s?.disclaimer ??
          "Esta tela apresenta séries históricas. Não conclui causalidade entre índices e preços."}
      </p>

      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="underline" to="/analytics/external-indices/series">
          Séries
        </Link>
        <Link className="underline" to="/analytics/external-indices/sources">
          Fontes
        </Link>
        <Link className="underline" to="/analytics/external-indices/imports">
          Importação
        </Link>
        <Link className="underline" to="/analytics/external-indices/runs">
          Execuções
        </Link>
        <Link className="underline" to="/analytics/external-indices/quality">
          Qualidade
        </Link>
      </div>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Séries atrasadas" value={s?.stale_series_count?.toString()} loading={summaryQ.isLoading} />
        <Card
          label="Problemas de qualidade"
          value={s?.open_quality_issues?.toString()}
          loading={summaryQ.isLoading}
        />
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {(s?.cards ?? []).map((card) => (
          <article key={card.series_id} className="rounded border border-slate-200 p-4">
            <div className="text-xs uppercase tracking-wide text-slate-500">{card.series_code}</div>
            <h2 className="font-medium">{card.series_name}</h2>
            <p className="mt-2 text-2xl font-semibold">
              {card.value ?? "—"}{" "}
              <span className="text-sm font-normal text-slate-500">{card.unit}</span>
            </p>
            <dl className="mt-3 space-y-1 text-xs text-slate-600">
              <div>Data econômica: {card.observation_datetime ?? "—"}</div>
              <div>Publicação: {card.published_at ?? "—"}</div>
              <div>Coleta: {card.fetched_at ?? "—"}</div>
              <div>
                Freshness: <strong>{card.freshness}</strong>
              </div>
              <div>Variação: {card.change_pct ? `${card.change_pct}%` : "—"}</div>
              <div>Frequência: {card.frequency}</div>
            </dl>
            <Link className="mt-3 inline-block text-sm underline" to={`/analytics/external-indices/series/${card.series_id}`}>
              Detalhe
            </Link>
          </article>
        ))}
        {!summaryQ.isLoading && (s?.cards?.length ?? 0) === 0 ? (
          <p className="text-sm text-slate-600">Nenhuma série. Inicialize o catálogo padrão.</p>
        ) : null}
      </section>
    </div>
  );
}

function Card({
  label,
  value,
  loading,
}: {
  label: string;
  value?: string | null;
  loading?: boolean;
}) {
  return (
    <div className="rounded border border-slate-200 p-4">
      <div className="text-xs uppercase text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold">{loading ? "…" : (value ?? "—")}</div>
    </div>
  );
}
