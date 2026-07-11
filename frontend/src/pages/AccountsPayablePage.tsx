import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import {
  fetchAccountsPayableAging,
  fetchAccountsPayableSummary,
  fetchAccountsPayableTitles,
  fetchFuelPurchasesFreshness,
} from "../api/fuel-purchases-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

const AGING_LABELS: Record<string, string> = {
  OVERDUE: "Vencido",
  "0_7": "0–7 dias",
  "8_15": "8–15 dias",
  "16_30": "16–30 dias",
  "31_60": "31–60 dias",
  OVER_60: "Mais de 60 dias",
};

function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 90);
  return { date_from: from.toISOString().slice(0, 10), date_to: to.toISOString().slice(0, 10) };
}

export function AccountsPayablePage() {
  const { hasPermission } = useAuth();
  const canViewValues = hasPermission("accounts_payable.view_values");
  const [range] = useState(defaultDateRange);
  const [page, setPage] = useState(1);

  const summaryQuery = useQuery({
    queryKey: ["accounts-payable-summary", range],
    queryFn: () => fetchAccountsPayableSummary(range),
  });
  const agingQuery = useQuery({
    queryKey: ["accounts-payable-aging", range],
    queryFn: () => fetchAccountsPayableAging(range),
  });
  const titlesQuery = useQuery({
    queryKey: ["accounts-payable-titles", range, page],
    queryFn: () =>
      fetchAccountsPayableTitles({
        page,
        page_size: 20,
        date_from: range.date_from,
        date_to: range.date_to,
      }),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-purchases-freshness"],
    queryFn: fetchFuelPurchasesFreshness,
  });

  const mask = (value: string | number | null | undefined) =>
    canViewValues ? String(value ?? "—") : "Restrito";

  const summary = summaryQuery.data;
  const aging = agingQuery.data ?? [];
  const titles = titlesQuery.data?.items ?? [];
  const total = titlesQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Contas a pagar</h1>
        <p className="text-sm text-slate-600">Saldo em aberto, aging e títulos sincronizados do ERP.</p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card label="Saldo em aberto" value={mask(summary?.open_amount)} loading={summaryQuery.isLoading} />
        <Card label="Vencido" value={mask(summary?.overdue_amount)} loading={summaryQuery.isLoading} />
        <Card label="Vence em 7 dias" value={mask(summary?.due_in_7_days_amount)} loading={summaryQuery.isLoading} />
        <Card label="Vence em 30 dias" value={mask(summary?.due_in_30_days_amount)} loading={summaryQuery.isLoading} />
        <Card label="Prazo médio (dias)" value={summary?.weighted_term_days ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Títulos abertos" value={summary?.open_title_count?.toString() ?? "—"} loading={summaryQuery.isLoading} />
        <Card label="Parcialmente pagos" value={summary?.partially_paid_count?.toString() ?? "—"} loading={summaryQuery.isLoading} />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Aging</h2>
        {agingQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : aging.length === 0 ? (
          <p className="text-sm text-slate-500">Sem títulos em aberto.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Faixa</th>
                  <th className="py-2 pr-4">Títulos</th>
                  <th className="py-2 pr-4">Saldo</th>
                </tr>
              </thead>
              <tbody>
                {aging.map((row) => (
                  <tr key={row.bucket} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{AGING_LABELS[row.bucket] ?? row.bucket}</td>
                    <td className="py-2 pr-4">{row.title_count}</td>
                    <td className="py-2 pr-4">{mask(row.open_amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-lg font-medium">Títulos</h2>
        {titlesQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : titles.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum título no período.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Vencimento</th>
                  <th className="py-2 pr-4">Fornecedor</th>
                  <th className="py-2 pr-4">Posto</th>
                  <th className="py-2 pr-4">Documento</th>
                  <th className="py-2 pr-4">Original</th>
                  <th className="py-2 pr-4">Aberto</th>
                  <th className="py-2 pr-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {titles.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.due_date}</td>
                    <td className="py-2 pr-4">{row.distributor_name ?? "—"}</td>
                    <td className="py-2 pr-4">{row.station_name}</td>
                    <td className="py-2 pr-4">{row.document_number ?? "—"}</td>
                    <td className="py-2 pr-4">{mask(row.original_amount)}</td>
                    <td className="py-2 pr-4">{mask(row.open_amount)}</td>
                    <td className="py-2 pr-4">{row.normalized_status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {total > 20 && (
          <div className="mt-4 flex items-center gap-3 text-sm">
            <button
              type="button"
              className="rounded border px-3 py-1 disabled:opacity-50"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Anterior
            </button>
            <span>
              Página {page} de {totalPages}
            </span>
            <button
              type="button"
              className="rounded border px-3 py-1 disabled:opacity-50"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Próxima
            </button>
          </div>
        )}
      </section>
    </div>
  );
}

function Card({ label, value, loading }: { label: string; value: string; loading: boolean }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-900">{loading ? "..." : value}</p>
    </div>
  );
}
