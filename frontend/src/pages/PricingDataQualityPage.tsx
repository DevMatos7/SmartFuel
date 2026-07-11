import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchPricingDataQuality } from "../api/pricing";

export function PricingDataQualityPage() {
  const q = useQuery({ queryKey: ["pricing-quality"], queryFn: fetchPricingDataQuality });
  const entries = Object.entries(q.data?.by_quality_status ?? {});
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/pricing">
        ← Precificação
      </Link>
      <h1 className="text-xl font-semibold">Qualidade dos dados de precificação</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      <p className="text-sm">Total: {q.data?.total ?? 0}</p>
      {!entries.length && !q.isLoading ? <p className="text-sm text-slate-500">Sem recomendações.</p> : null}
      <ul className="space-y-1 text-sm">
        {entries.map(([k, v]) => (
          <li key={k}>
            {k}: {v}
          </li>
        ))}
      </ul>
    </div>
  );
}
