import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { fetchFuelPurchaseInvoices, fetchFuelPurchasesFreshness } from "../api/fuel-purchases-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

function defaultDateRange() {
  const to = new Date();
  const from = new Date();
  from.setDate(from.getDate() - 30);
  return { date_from: from.toISOString().slice(0, 10), date_to: to.toISOString().slice(0, 10) };
}

export function FuelPurchaseInvoicesPage() {
  const { hasPermission } = useAuth();
  const canViewCost = hasPermission("fuel_purchases.view_cost");
  const [range] = useState(defaultDateRange);
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");

  const invoicesQuery = useQuery({
    queryKey: ["fuel-purchase-invoices", range, page, q],
    queryFn: () =>
      fetchFuelPurchaseInvoices({
        page,
        page_size: 20,
        date_from: range.date_from,
        date_to: range.date_to,
        q: q || undefined,
      }),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-purchases-freshness"],
    queryFn: fetchFuelPurchasesFreshness,
  });

  const items = invoicesQuery.data?.items ?? [];
  const total = invoicesQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-6">
      <div>
        <Link to="/analytics/fuel-purchases" className="text-sm text-slate-500 underline">
          Voltar ao dashboard
        </Link>
        <h1 className="mt-2 text-2xl font-semibold text-slate-900">Notas fiscais de entrada</h1>
        <p className="text-sm text-slate-600">Compras sincronizadas do ERP com status de XML e elegibilidade.</p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />

      <div className="flex flex-wrap gap-3">
        <input
          type="search"
          placeholder="Buscar nota ou chave..."
          className="rounded border border-slate-300 px-3 py-2 text-sm"
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setPage(1);
          }}
        />
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        {invoicesQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhuma nota no período.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Entrada</th>
                  <th className="py-2 pr-4">Nota</th>
                  <th className="py-2 pr-4">Distribuidora</th>
                  <th className="py-2 pr-4">Posto</th>
                  <th className="py-2 pr-4">Volume</th>
                  <th className="py-2 pr-4">Total</th>
                  {canViewCost && <th className="py-2 pr-4">Custo/L</th>}
                  <th className="py-2 pr-4">XML no ERP</th>
                  <th className="py-2 pr-4">Arquivo XML</th>
                  <th className="py-2 pr-4">Status</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.entry_date}</td>
                    <td className="py-2 pr-4">
                      <Link to={`/analytics/fuel-purchases/invoices/${row.id}`} className="text-slate-900 underline">
                        {row.source_series ? `${row.source_series}/` : ""}
                        {row.source_document_number}
                      </Link>
                    </td>
                    <td className="py-2 pr-4">{row.distributor_name ?? "—"}</td>
                    <td className="py-2 pr-4">{row.station_name}</td>
                    <td className="py-2 pr-4">{row.purchased_volume_liters}</td>
                    <td className="py-2 pr-4">{row.total_amount}</td>
                    {canViewCost && <td className="py-2 pr-4">{row.delivered_cost_per_liter ?? "—"}</td>}
                    <td className="py-2 pr-4">{row.xml_imported_in_erp ? "Sim" : "Não"}</td>
                    <td className="py-2 pr-4">
                      {row.has_xml ? (row.xml_reconciliation_status ?? "Disponível") : "—"}
                    </td>
                    <td className="py-2 pr-4">
                      {row.is_cancelled ? "Cancelada" : row.metric_eligibility_status}
                    </td>
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
