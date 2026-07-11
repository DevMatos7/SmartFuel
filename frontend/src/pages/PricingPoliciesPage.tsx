import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchPricingPolicies } from "../api/pricing";

export function PricingPoliciesPage() {
  const q = useQuery({ queryKey: ["pricing-policies"], queryFn: fetchPricingPolicies });
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/pricing">
        ← Precificação
      </Link>
      <h1 className="text-xl font-semibold">Políticas de formação de preço</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !(q.data?.length) ? (
        <p className="text-sm text-slate-500">Nenhuma política cadastrada. Use a API ou homologação sintética.</p>
      ) : null}
      <ul className="space-y-2 text-sm">
        {(q.data ?? []).map((p) => (
          <li key={p.id} className="rounded border border-slate-200 bg-white p-3">
            <div className="font-medium">{p.name}</div>
            <div className="text-slate-600">
              {p.cost_basis_type} · piso margem {p.minimum_margin_per_liter ?? "—"} · alvo{" "}
              {p.target_margin_per_liter ?? "—"} · {p.rounding_policy} · aprovações {p.required_approvals}
            </div>
            <div className="text-xs text-slate-500">
              vigência {p.valid_from} · {p.active ? "ativa" : "inativa"}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
