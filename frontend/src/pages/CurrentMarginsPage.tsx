import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchPricingRecommendations } from "../api/pricing";

export function CurrentMarginsPage() {
  const q = useQuery({ queryKey: ["pricing-items"], queryFn: fetchPricingRecommendations });
  return (
    <div className="space-y-4">
      <div>
        <Link className="text-sm underline" to="/pricing">
          ← Precificação
        </Link>
        <h1 className="text-xl font-semibold">Margens atuais</h1>
        <p className="text-sm text-slate-600">Margem bruta comercial estimada — não é lucro líquido</p>
      </div>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {q.isError ? <p className="text-sm text-red-600">Erro ao carregar.</p> : null}
      {!q.isLoading && !(q.data?.length) ? <p className="text-sm text-slate-500">Sem dados.</p> : null}
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Preço</th>
            <th className="py-2">Custo/L</th>
            <th className="py-2">Margem/L</th>
            <th className="py-2">Piso</th>
            <th className="py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {(q.data ?? []).map((i) => (
            <tr key={i.id} className="border-b border-slate-100">
              <td className="py-2">{i.current_price ?? "—"}</td>
              <td className="py-2">{i.cost_per_liter ?? "—"}</td>
              <td
                className={`py-2 ${
                  i.current_margin_per_liter && Number(i.current_margin_per_liter) < 0 ? "text-red-600" : ""
                }`}
              >
                {i.current_margin_per_liter ?? "—"}
              </td>
              <td className="py-2">{i.commercial_floor_price ?? "—"}</td>
              <td className="py-2">
                <Link className="underline" to={`/pricing/recommendations/${i.id}`}>
                  {i.recommendation_status}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
