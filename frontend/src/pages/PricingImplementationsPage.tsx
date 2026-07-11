import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchPricingDecisions } from "../api/pricing";

export function PricingImplementationsPage() {
  const q = useQuery({ queryKey: ["pricing-decisions"], queryFn: () => fetchPricingDecisions() });
  const rows = (q.data ?? []).filter((d) =>
    ["APPROVED_PENDING_IMPLEMENTATION", "IMPLEMENTED_MATCHED", "IMPLEMENTED_DIFFERENT"].includes(d.status),
  );
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/pricing">
        ← Precificação
      </Link>
      <h1 className="text-xl font-semibold">Implementações</h1>
      <p className="text-sm text-slate-600">Conferência manual ou via snapshot ERP — sem alteração automática</p>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !rows.length ? <p className="text-sm text-slate-500">Nenhuma implementação.</p> : null}
      <ul className="space-y-2 text-sm">
        {rows.map((d) => (
          <li key={d.id} className="rounded border border-slate-200 bg-white p-3">
            <Link className="underline" to={`/pricing/decisions/${d.id}`}>
              {d.status}
            </Link>
            <div>
              aprovado {d.approved_price ?? "—"} · recomendado {d.recommended_price}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
