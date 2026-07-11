import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import {
  fetchFuelSalesDataQuality,
  fetchFuelSalesFreshness,
  fetchFuelSalesUnmapped,
  reconcileFuelSalesMappings,
} from "../api/fuel-sales-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return { date_from: from.toISOString().slice(0, 10), date_to: to.toISOString().slice(0, 10) };
}

export function FuelSalesDataQualityPage() {
  const { hasPermission } = useAuth();
  const canReconcile = hasPermission("fuel_sales_data_quality.reconcile");
  const queryClient = useQueryClient();
  const [range] = useState(defaultDateRange);
  const [reconcileMessage, setReconcileMessage] = useState<string | null>(null);

  const qualityQuery = useQuery({
    queryKey: ["fuel-sales-quality", range],
    queryFn: () => fetchFuelSalesDataQuality(range),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-sales-freshness"],
    queryFn: fetchFuelSalesFreshness,
  });
  const unmappedQuery = useQuery({
    queryKey: ["fuel-sales-unmapped", range],
    queryFn: () => fetchFuelSalesUnmapped(range),
  });

  const reconcileMutation = useMutation({
    mutationFn: reconcileFuelSalesMappings,
    onSuccess: (data) => {
      const total = data.runs.reduce((sum, run) => sum + run.affected_facts, 0);
      setReconcileMessage(
        data.runs.length === 0
          ? "Nenhum produto mapeado com vendas pendentes de reconciliação."
          : `Reconciliação concluída: ${data.runs.length} execução(ões), ${total} fato(s) atualizado(s).`,
      );
      void queryClient.invalidateQueries({ queryKey: ["fuel-sales-quality"] });
      void queryClient.invalidateQueries({ queryKey: ["fuel-sales-unmapped"] });
      void queryClient.invalidateQueries({ queryKey: ["fuel-sales-summary"] });
    },
    onError: () => setReconcileMessage("Falha na reconciliação. Verifique permissões e mapeamentos."),
  });

  const q = qualityQuery.data as
    | {
        unmapped_item_count: number;
        unmapped_volume_liters: string;
        missing_cost_item_count: number;
        missing_cost_volume_liters: string;
        quarantined_item_count: number;
        pending_payment_methods: number;
      }
    | undefined;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Qualidade dos dados — vendas</h1>
          <p className="text-sm text-slate-600">Itens sem mapeamento, sem custo e formas de pagamento pendentes.</p>
        </div>
        {canReconcile && (
          <button
            type="button"
            className="rounded-md bg-sky-600 px-4 py-2 text-sm font-medium text-white hover:bg-sky-700 disabled:opacity-50"
            disabled={reconcileMutation.isPending}
            onClick={() => reconcileMutation.mutate()}
          >
            {reconcileMutation.isPending ? "Reconciliando..." : "Reconciliar mapeamentos"}
          </button>
        )}
      </div>
      {reconcileMessage && <p className="text-sm text-slate-700">{reconcileMessage}</p>}
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MetricCard label="Vendas sem produto mapeado" value={q?.unmapped_item_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Volume sem mapeamento (L)" value={q?.unmapped_volume_liters ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Vendas sem custo" value={q?.missing_cost_item_count ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Volume sem custo (L)" value={q?.missing_cost_volume_liters ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Métodos de pagamento pendentes" value={q?.pending_payment_methods ?? "—"} loading={qualityQuery.isLoading} />
        <MetricCard label="Linhas excluídas" value={q?.quarantined_item_count ?? "—"} loading={qualityQuery.isLoading} />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Produtos ERP sem mapeamento</h2>
        {unmappedQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : (unmappedQuery.data ?? []).length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum item sem mapeamento no período.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Código ERP</th>
                  <th className="py-2 pr-4">Descrição</th>
                  <th className="py-2 pr-4">Itens</th>
                  <th className="py-2 pr-4">Volume (L)</th>
                </tr>
              </thead>
              <tbody>
                {(unmappedQuery.data ?? []).map((row) => (
                  <tr key={row.erp_product_id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.erp_product_code ?? row.erp_product_id}</td>
                    <td className="py-2 pr-4">{row.erp_description}</td>
                    <td className="py-2 pr-4">{row.item_count}</td>
                    <td className="py-2 pr-4">{row.volume_liters}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

function MetricCard({ label, value, loading }: { label: string; value: string | number; loading: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold">{loading ? "..." : value}</p>
    </div>
  );
}
