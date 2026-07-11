import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  fetchBelowFloor,
  fetchPricingRecommendations,
  fetchPricingRuns,
  fetchPricingSummary,
  runSyntheticPricingHomologation,
} from "../api/pricing";
import { useAuth } from "../auth/AuthProvider";

export function PricingDashboardPage() {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const summaryQ = useQuery({ queryKey: ["pricing-summary"], queryFn: fetchPricingSummary });
  const itemsQ = useQuery({ queryKey: ["pricing-items"], queryFn: fetchPricingRecommendations });
  const belowQ = useQuery({ queryKey: ["pricing-below-floor"], queryFn: fetchBelowFloor });
  const runsQ = useQuery({ queryKey: ["pricing-runs"], queryFn: fetchPricingRuns });

  const synthM = useMutation({
    mutationFn: async () => {
      const stationId = localStorage.getItem("active_station_id");
      const first = itemsQ.data?.[0];
      const productId = first?.canonical_product_id ?? localStorage.getItem("pricing_synthetic_product_id");
      if (!stationId || !productId) {
        throw new Error(
          "Defina o posto ativo e um produto (gere uma recomendação ou salve pricing_synthetic_product_id).",
        );
      }
      return runSyntheticPricingHomologation(stationId, productId);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["pricing-summary"] });
      qc.invalidateQueries({ queryKey: ["pricing-items"] });
      qc.invalidateQueries({ queryKey: ["pricing-runs"] });
      qc.invalidateQueries({ queryKey: ["pricing-below-floor"] });
    },
  });

  const s = summaryQ.data;
  const cards = [
    { label: "Produtos monitorados", value: s?.monitored_products ?? "—" },
    { label: "Abaixo do piso", value: s?.below_floor ?? "—" },
    { label: "Margem média / L", value: s?.average_margin_per_liter ?? "—" },
    { label: "Aumentos", value: s?.increase_recommendations ?? "—" },
    { label: "Reduções", value: s?.decrease_recommendations ?? "—" },
    { label: "Pendentes aprovação", value: s?.pending_approval ?? "—" },
    { label: "Aprovadas não implantadas", value: s?.approved_not_implemented ?? "—" },
    { label: "Implantações divergentes", value: s?.divergent_implementations ?? "—" },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold">Precificação</h1>
          <p className="text-sm text-slate-600">
            Margem bruta comercial estimada · recomendação ≠ aprovado ≠ implantado · sem escrita no XPERT
          </p>
        </div>
        {hasPermission("pricing.generate_recommendation") ? (
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

      {s?.disclaimer ? <p className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm">{s.disclaimer}</p> : null}
      {synthM.isError ? (
        <p className="text-sm text-red-600">{(synthM.error as Error).message}</p>
      ) : null}

      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="underline" to="/pricing/margins">
          Margens atuais
        </Link>
        <Link className="underline" to="/pricing/recommendations">
          Recomendações
        </Link>
        <Link className="underline" to="/pricing/approvals">
          Aprovações
        </Link>
        <Link className="underline" to="/pricing/implementations">
          Implementações
        </Link>
        <Link className="underline" to="/pricing/policies">
          Políticas
        </Link>
        <Link className="underline" to="/pricing/quality">
          Qualidade
        </Link>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map((c) => (
          <div key={c.label} className="rounded border border-slate-200 bg-white p-3">
            <div className="text-xs text-slate-500">{c.label}</div>
            <div className="mt-1 text-lg font-semibold">{c.value}</div>
          </div>
        ))}
      </div>

      <section>
        <h2 className="mb-2 text-sm font-semibold">Abaixo do piso</h2>
        {belowQ.isLoading ? <p className="text-sm">Carregando…</p> : null}
        {!belowQ.isLoading && !(belowQ.data?.length) ? (
          <p className="text-sm text-slate-500">Nenhum produto abaixo do piso.</p>
        ) : null}
        <ul className="space-y-1 text-sm">
          {(belowQ.data ?? []).map((r) => (
            <li key={r.id}>
              <Link className="underline" to={`/pricing/recommendations/${r.id}`}>
                gap {r.gap}
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold">Últimas recomendações</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead>
              <tr className="border-b text-slate-500">
                <th className="py-2 pr-3">Status</th>
                <th className="py-2 pr-3">Preço</th>
                <th className="py-2 pr-3">Custo/L</th>
                <th className="py-2 pr-3">Margem/L</th>
                <th className="py-2 pr-3">Piso</th>
                <th className="py-2 pr-3">Alvo</th>
                <th className="py-2 pr-3">Rec.</th>
                <th className="py-2">Qualidade</th>
              </tr>
            </thead>
            <tbody>
              {(itemsQ.data ?? []).slice(0, 20).map((i) => (
                <tr key={i.id} className="border-b border-slate-100">
                  <td className="py-2 pr-3">
                    <Link className="underline" to={`/pricing/recommendations/${i.id}`}>
                      {i.recommendation_status}
                    </Link>
                  </td>
                  <td className="py-2 pr-3">{i.current_price ?? "—"}</td>
                  <td className="py-2 pr-3">{i.cost_per_liter ?? "—"}</td>
                  <td className="py-2 pr-3">{i.current_margin_per_liter ?? "—"}</td>
                  <td className="py-2 pr-3">{i.commercial_floor_price ?? "—"}</td>
                  <td className="py-2 pr-3">{i.target_price ?? "—"}</td>
                  <td className="py-2 pr-3">{i.recommended_price ?? "—"}</td>
                  <td className="py-2">{i.quality_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold">Runs</h2>
        <ul className="space-y-1 text-sm">
          {(runsQ.data ?? []).slice(0, 10).map((r) => (
            <li key={r.id}>
              {r.trigger_type} · {r.status} · itens {r.item_count} · {r.snapshot_hash?.slice(0, 8)}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
