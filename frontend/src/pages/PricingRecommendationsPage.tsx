import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchPricingRecommendations } from "../api/pricing";

export function PricingRecommendationsPage() {
  const q = useQuery({ queryKey: ["pricing-items"], queryFn: fetchPricingRecommendations });
  return (
    <div className="space-y-4">
      <div>
        <Link className="text-sm underline" to="/pricing">
          ← Precificação
        </Link>
        <h1 className="text-xl font-semibold">Recomendações</h1>
      </div>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !(q.data?.length) ? <p className="text-sm text-slate-500">Sem recomendações.</p> : null}
      <ul className="space-y-2 text-sm">
        {(q.data ?? []).map((i) => (
          <li key={i.id} className="rounded border border-slate-200 bg-white p-3">
            <Link className="font-medium underline" to={`/pricing/recommendations/${i.id}`}>
              {i.recommendation_status}
            </Link>
            <div className="mt-1 text-slate-600">
              atual {i.current_price ?? "—"} → rec {i.recommended_price ?? "—"} · {i.quality_status}
            </div>
            {i.reasons?.length ? <div className="mt-1 text-xs text-amber-700">{i.reasons.join(", ")}</div> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
