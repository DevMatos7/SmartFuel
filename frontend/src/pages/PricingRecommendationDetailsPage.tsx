import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  createPricingDecision,
  fetchPricingRecommendation,
  fetchPricingScenarios,
  submitPricingDecision,
} from "../api/pricing";
import { useAuth } from "../auth/AuthProvider";

export function PricingRecommendationDetailsPage() {
  const { id = "" } = useParams();
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const itemQ = useQuery({
    queryKey: ["pricing-item", id],
    queryFn: () => fetchPricingRecommendation(id),
    enabled: Boolean(id),
  });
  const scenQ = useQuery({
    queryKey: ["pricing-scenarios", id],
    queryFn: () => fetchPricingScenarios(id),
    enabled: Boolean(id),
  });
  const decideM = useMutation({
    mutationFn: async () => {
      const d = await createPricingDecision(id, { required_approvals: 1, decision_reason: "Revisão operacional" });
      return submitPricingDecision(d.id);
    },
    onSuccess: (d) => {
      qc.invalidateQueries({ queryKey: ["pricing-decisions"] });
      window.location.href = `/pricing/decisions/${d.id}`;
    },
  });

  const i = itemQ.data;
  const blocking = (i?.warnings ?? []).filter((w) =>
    ["MISSING_COST", "MISSING_CURRENT_PRICE", "LOW_COST_CONFIDENCE"].includes(w),
  );

  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/pricing/recommendations">
        ← Recomendações
      </Link>
      <h1 className="text-xl font-semibold">Detalhe da recomendação</h1>
      {itemQ.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {i ? (
        <>
          <p className="text-sm text-slate-600">
            Margem bruta comercial estimada. Hash: {i.snapshot_hash.slice(0, 12)}…
          </p>
          {blocking.length ? (
            <div className="rounded border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
              Alertas bloqueantes: {blocking.join(", ")}
            </div>
          ) : null}
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Preço atual</dt>
              <dd>{i.current_price ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Custo / L</dt>
              <dd>
                {i.cost_per_liter ?? "—"} ({i.cost_confidence})
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Margem / L</dt>
              <dd>{i.current_margin_per_liter ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Piso / Alvo</dt>
              <dd>
                {i.commercial_floor_price ?? "—"} / {i.target_price ?? "—"}
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Recomendado</dt>
              <dd>
                {i.recommended_price ?? "—"} ({i.recommendation_status})
              </dd>
            </div>
            <div>
              <dt className="text-slate-500">Qualidade</dt>
              <dd>{i.quality_status}</dd>
            </div>
          </dl>
          {i.reasons?.length ? <p className="text-sm">Motivos: {i.reasons.join(", ")}</p> : null}
          {i.warnings?.length ? <p className="text-sm text-amber-700">Avisos: {i.warnings.join(", ")}</p> : null}

          <section>
            <h2 className="mb-2 text-sm font-semibold">Cenários</h2>
            <ul className="space-y-1 text-sm">
              {(scenQ.data ?? []).map((s) => (
                <li key={s.scenario_type}>
                  {s.scenario_type}: {s.rounded_price} (antes {s.calculated_price}) · margem {s.margin_per_liter}
                </li>
              ))}
            </ul>
          </section>

          {hasPermission("pricing.review") && i.recommended_price ? (
            <button
              type="button"
              className="rounded bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
              disabled={decideM.isPending || blocking.length > 0}
              onClick={() => decideM.mutate()}
            >
              Criar decisão e submeter
            </button>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
