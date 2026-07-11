import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { fetchFuelPurchasesFreshness, fetchNfeDocuments } from "../api/fuel-purchases-analytics";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

export function NfeDocumentsPage() {
  const { hasPermission } = useAuth();
  const canDownload = hasPermission("nfe_documents.download");
  const canImport = hasPermission("nfe_documents.import");
  const canReconcile = hasPermission("nfe_documents.reconcile");
  const [page, setPage] = useState(1);
  const [q, setQ] = useState("");

  const documentsQuery = useQuery({
    queryKey: ["nfe-documents", page, q],
    queryFn: () => fetchNfeDocuments({ page, page_size: 20, q: q || undefined }),
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-purchases-freshness"],
    queryFn: fetchFuelPurchasesFreshness,
  });

  const items = documentsQuery.data?.items ?? [];
  const total = documentsQuery.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Documentos NF-e</h1>
          <p className="text-sm text-slate-600">XMLs importados com status de parse e reconciliação ERP.</p>
        </div>
        {canImport && (
          <button type="button" className="rounded bg-slate-900 px-4 py-2 text-sm text-white opacity-50" disabled>
            Importar XML (em breve)
          </button>
        )}
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />

      <input
        type="search"
        placeholder="Buscar chave ou número..."
        className="rounded border border-slate-300 px-3 py-2 text-sm"
        value={q}
        onChange={(e) => {
          setQ(e.target.value);
          setPage(1);
        }}
      />

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        {documentsQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : items.length === 0 ? (
          <p className="text-sm text-slate-500">Nenhum documento NF-e importado.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Emissão</th>
                  <th className="py-2 pr-4">Número</th>
                  <th className="py-2 pr-4">Chave</th>
                  <th className="py-2 pr-4">Posto</th>
                  <th className="py-2 pr-4">Total</th>
                  <th className="py-2 pr-4">Parse</th>
                  <th className="py-2 pr-4">Reconciliação</th>
                  <th className="py-2 pr-4">Nota ERP</th>
                  {(canDownload || canReconcile) && <th className="py-2 pr-4">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.issue_datetime.slice(0, 10)}</td>
                    <td className="py-2 pr-4">
                      {row.series}/{row.document_number}
                    </td>
                    <td className="py-2 pr-4 font-mono text-xs">{row.access_key.slice(0, 12)}…</td>
                    <td className="py-2 pr-4">{row.station_name}</td>
                    <td className="py-2 pr-4">{row.total_amount}</td>
                    <td className="py-2 pr-4">{row.parse_status}</td>
                    <td className="py-2 pr-4">{row.reconciliation_status}</td>
                    <td className="py-2 pr-4">
                      {row.purchase_invoice_id ? (
                        <Link
                          to={`/analytics/fuel-purchases/invoices/${row.purchase_invoice_id}`}
                          className="text-slate-900 underline"
                        >
                          Ver nota
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                    {(canDownload || canReconcile) && (
                      <td className="py-2 pr-4 text-xs text-slate-500">
                        {canDownload && "Download "}
                        {canReconcile && "Reconciliar"}
                      </td>
                    )}
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
