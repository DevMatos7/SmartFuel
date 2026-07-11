import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchFuelPurchaseInvoice,
  fetchFuelPurchaseInvoiceItems,
  fetchFuelPurchaseInvoiceTitles,
  fetchFuelPurchaseInvoiceXml,
  fetchFuelPurchasesFreshness,
} from "../api/fuel-purchases-analytics";
import { fetchLatestInvoiceBenchmark, runInvoiceBenchmark } from "../api/purchase-benchmarks";
import { XpertUnsafeSourceBanner } from "../components/xpert/XpertUnsafeSourceBanner";
import { useAuth } from "../auth/AuthProvider";

type Tab = "summary" | "items" | "costs" | "taxes" | "xml" | "titles" | "quality" | "benchmark";

const TABS: { key: Tab; label: string }[] = [
  { key: "summary", label: "Resumo" },
  { key: "items", label: "Itens" },
  { key: "costs", label: "Custos" },
  { key: "taxes", label: "Tributos" },
  { key: "xml", label: "XML" },
  { key: "titles", label: "Títulos" },
  { key: "quality", label: "Qualidade" },
  { key: "benchmark", label: "Benchmark" },
];

export function FuelPurchaseInvoiceDetailsPage() {
  const { id = "" } = useParams();
  const { hasPermission } = useAuth();
  const canViewCost = hasPermission("fuel_purchases.view_cost");
  const canViewXml = hasPermission("purchase_invoices.view_xml");
  const canRunBenchmark = hasPermission("purchase_benchmarks.run");
  const canReadBenchmark = hasPermission("purchase_benchmarks.read");
  const [tab, setTab] = useState<Tab>("summary");
  const qc = useQueryClient();

  const invoiceQuery = useQuery({
    queryKey: ["fuel-purchase-invoice", id],
    queryFn: () => fetchFuelPurchaseInvoice(id),
    enabled: Boolean(id),
  });
  const itemsQuery = useQuery({
    queryKey: ["fuel-purchase-invoice-items", id],
    queryFn: () => fetchFuelPurchaseInvoiceItems(id),
    enabled: Boolean(id) && ["items", "costs", "taxes", "quality"].includes(tab),
  });
  const titlesQuery = useQuery({
    queryKey: ["fuel-purchase-invoice-titles", id],
    queryFn: () => fetchFuelPurchaseInvoiceTitles(id),
    enabled: Boolean(id) && tab === "titles",
  });
  const xmlQuery = useQuery({
    queryKey: ["fuel-purchase-invoice-xml", id],
    queryFn: () => fetchFuelPurchaseInvoiceXml(id),
    enabled: Boolean(id) && tab === "xml" && canViewXml,
  });
  const freshnessQuery = useQuery({
    queryKey: ["fuel-purchases-freshness"],
    queryFn: fetchFuelPurchasesFreshness,
  });
  const benchmarkQuery = useQuery({
    queryKey: ["invoice-benchmark", id],
    queryFn: () => fetchLatestInvoiceBenchmark(id),
    enabled: Boolean(id) && tab === "benchmark" && canReadBenchmark,
    retry: false,
  });
  const runBenchmark = useMutation({
    mutationFn: () => runInvoiceBenchmark(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["invoice-benchmark", id] }),
  });

  if (invoiceQuery.isLoading) return <p className="text-sm text-slate-500">Carregando nota...</p>;
  if (invoiceQuery.isError || !invoiceQuery.data) {
    return <p className="text-sm text-rose-600">Nota fiscal não encontrada.</p>;
  }

  const invoice = invoiceQuery.data;
  const items = itemsQuery.data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <Link to="/analytics/fuel-purchases/invoices" className="text-sm text-slate-500 underline">
          Voltar às notas
        </Link>
        <h1 className="mt-2 text-xl font-semibold">
          NF {invoice.source_series ? `${invoice.source_series}/` : ""}
          {invoice.source_document_number}
        </h1>
        <p className="text-sm text-slate-600">
          {invoice.station_name} · Entrada {invoice.entry_date}
          {invoice.is_cancelled && <span className="ml-2 text-rose-700">Cancelada</span>}
        </p>
      </div>
      <XpertUnsafeSourceBanner securityStatus={freshnessQuery.data?.security_status} />

      <div className="flex flex-wrap gap-2 border-b">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            className={`px-3 py-2 text-sm ${tab === key ? "border-b-2 border-slate-900 font-medium" : "text-slate-600"}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>

      {tab === "summary" && (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <InfoCard label="Distribuidora" value={invoice.distributor_name ?? "—"} />
          <InfoCard label="Chave de acesso" value={invoice.access_key ?? "—"} />
          <InfoCard label="XML importado no ERP" value={invoice.xml_imported_in_erp ? "Sim" : "Não"} />
          <InfoCard label="Arquivo XML no sistema" value={invoice.has_xml_file ? "Sim" : "Não"} />
          <InfoCard label="Emissão" value={invoice.issue_date} />
          <InfoCard label="Valor total" value={invoice.total_amount} />
          <InfoCard label="Volume (L)" value={invoice.purchased_volume_liters} />
          <InfoCard label="Frete" value={invoice.freight_amount} />
          <InfoCard label="Desconto" value={invoice.discount_amount} />
          {canViewCost && (
            <>
              <InfoCard label="Custo entregue" value={invoice.commercial_delivered_cost} />
              <InfoCard label="Custo/L" value={invoice.average_delivered_cost_per_liter ?? "—"} />
            </>
          )}
          <InfoCard label="Elegibilidade" value={invoice.metric_eligibility_status} />
        </section>
      )}

      {tab === "items" && (
        <TableSection loading={itemsQuery.isLoading} empty={items.length === 0} emptyText="Sem itens.">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2 pr-4">Produto</th>
                <th className="py-2 pr-4">Qtd</th>
                <th className="py-2 pr-4">Volume (L)</th>
                <th className="py-2 pr-4">Valor</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{row.product_name ?? row.source_description ?? row.source_product_id}</td>
                  <td className="py-2 pr-4">
                    {row.source_quantity} {row.source_unit ?? ""}
                  </td>
                  <td className="py-2 pr-4">{row.volume_liters ?? "—"}</td>
                  <td className="py-2 pr-4">{row.gross_item_amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableSection>
      )}

      {tab === "costs" && (
        !canViewCost ? (
          <p className="text-sm text-slate-600">Você não possui permissão para visualizar custos.</p>
        ) : (
          <TableSection loading={itemsQuery.isLoading} empty={items.length === 0} emptyText="Sem itens.">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Produto</th>
                  <th className="py-2 pr-4">Custo entregue</th>
                  <th className="py-2 pr-4">Custo/L</th>
                  <th className="py-2 pr-4">Custo ERP</th>
                  <th className="py-2 pr-4">Frete alocado</th>
                </tr>
              </thead>
              <tbody>
                {items.map((row) => (
                  <tr key={row.id} className="border-b border-slate-100">
                    <td className="py-2 pr-4">{row.product_name ?? row.source_product_id}</td>
                    <td className="py-2 pr-4">{row.commercial_delivered_cost}</td>
                    <td className="py-2 pr-4">{row.delivered_cost_per_liter ?? "—"}</td>
                    <td className="py-2 pr-4">{row.erp_recorded_cost ?? "—"}</td>
                    <td className="py-2 pr-4">{row.allocated_freight_amount}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableSection>
        )
      )}

      {tab === "taxes" && (
        <TableSection loading={itemsQuery.isLoading} empty={items.length === 0} emptyText="Sem itens.">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2 pr-4">Produto</th>
                <th className="py-2 pr-4">ICMS</th>
                <th className="py-2 pr-4">ICMS-ST</th>
                <th className="py-2 pr-4">FCP</th>
                <th className="py-2 pr-4">PIS</th>
                <th className="py-2 pr-4">COFINS</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{row.product_name ?? row.source_product_id}</td>
                  <td className="py-2 pr-4">{row.icms_amount ?? "—"}</td>
                  <td className="py-2 pr-4">{row.icms_st_amount ?? "—"}</td>
                  <td className="py-2 pr-4">{row.fcp_amount ?? "—"}</td>
                  <td className="py-2 pr-4">{row.pis_amount ?? "—"}</td>
                  <td className="py-2 pr-4">{row.cofins_amount ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableSection>
      )}

      {tab === "xml" && (
        !canViewXml ? (
          <p className="text-sm text-slate-600">Você não possui permissão para visualizar XML.</p>
        ) : xmlQuery.isLoading ? (
          <p className="text-sm text-slate-500">Carregando...</p>
        ) : !xmlQuery.data?.id ? (
          <div className="space-y-2 text-sm text-slate-500">
            <p>Arquivo XML não disponível no sistema (MinIO / nfe_xml_documents).</p>
            <p>
              XML importado no ERP:{" "}
              <span className="font-medium text-slate-700">
                {invoice.xml_imported_in_erp ? "Sim" : "Não"}
              </span>
              {" "}— isso não implica arquivo para download.
            </p>
          </div>
        ) : (
          <section className="grid gap-4 md:grid-cols-2">
            <InfoCard label="Chave" value={xmlQuery.data.access_key ?? "—"} />
            <InfoCard label="Parse" value={xmlQuery.data.parse_status ?? "—"} />
            <InfoCard label="Reconciliação" value={xmlQuery.data.reconciliation_status ?? "—"} />
            <InfoCard label="Tamanho" value={xmlQuery.data.xml_size_bytes?.toString() ?? "—"} />
            {xmlQuery.data.reconciliation_details && (
              <div className="col-span-full rounded border border-slate-200 bg-slate-50 p-3 text-xs">
                <pre>{JSON.stringify(xmlQuery.data.reconciliation_details, null, 2)}</pre>
              </div>
            )}
          </section>
        )
      )}

      {tab === "titles" && (
        <TableSection
          loading={titlesQuery.isLoading}
          empty={(titlesQuery.data ?? []).length === 0}
          emptyText="Sem títulos vinculados."
        >
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="py-2 pr-4">Parcela</th>
                <th className="py-2 pr-4">Vencimento</th>
                <th className="py-2 pr-4">Original</th>
                <th className="py-2 pr-4">Pago</th>
                <th className="py-2 pr-4">Aberto</th>
                <th className="py-2 pr-4">Status</th>
              </tr>
            </thead>
            <tbody>
              {(titlesQuery.data ?? []).map((row) => (
                <tr key={row.id} className="border-b border-slate-100">
                  <td className="py-2 pr-4">{row.installment_number ?? "—"}</td>
                  <td className="py-2 pr-4">{row.due_date}</td>
                  <td className="py-2 pr-4">{row.original_amount}</td>
                  <td className="py-2 pr-4">{row.paid_amount ?? "—"}</td>
                  <td className="py-2 pr-4">{row.open_amount}</td>
                  <td className="py-2 pr-4">{row.normalized_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </TableSection>
      )}

      {tab === "quality" && (
        <section className="space-y-4">
          <InfoCard label="Elegibilidade" value={invoice.metric_eligibility_status} />
          {invoice.metric_exclusion_reasons && invoice.metric_exclusion_reasons.length > 0 ? (
            <div className="rounded border border-amber-200 bg-amber-50 p-4 text-sm">
              <p className="font-medium">Motivos de exclusão (nota)</p>
              <ul className="mt-2 list-disc pl-5">
                {invoice.metric_exclusion_reasons.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Nota sem motivos de exclusão registrados.</p>
          )}
          {items.some((i) => (i.metric_exclusion_reasons ?? []).length > 0) && (
            <TableSection loading={itemsQuery.isLoading} empty={false} emptyText="">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-slate-500">
                    <th className="py-2 pr-4">Item</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Motivos</th>
                  </tr>
                </thead>
                <tbody>
                  {items
                    .filter((i) => (i.metric_exclusion_reasons ?? []).length > 0)
                    .map((row) => (
                      <tr key={row.id} className="border-b border-slate-100">
                        <td className="py-2 pr-4">{row.product_name ?? row.source_product_id}</td>
                        <td className="py-2 pr-4">{row.metric_eligibility_status}</td>
                        <td className="py-2 pr-4">{(row.metric_exclusion_reasons ?? []).join(", ")}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </TableSection>
          )}
        </section>
      )}

      {tab === "benchmark" && (
        !canReadBenchmark ? (
          <p className="text-sm text-slate-600">Sem permissão para ver benchmark.</p>
        ) : (
          <section className="space-y-4">
            {canRunBenchmark && (
              <button
                type="button"
                className="rounded border px-3 py-2 text-sm"
                disabled={runBenchmark.isPending}
                onClick={() => runBenchmark.mutate()}
              >
                Executar benchmark
              </button>
            )}
            {benchmarkQuery.isLoading ? (
              <p className="text-sm text-slate-500">Carregando…</p>
            ) : benchmarkQuery.isError || !benchmarkQuery.data ? (
              <p className="text-sm text-slate-500">Nenhum benchmark para esta nota.</p>
            ) : (
              <div className="space-y-3 text-sm">
                <p>
                  Status: {benchmarkQuery.data.status} · Confiança:{" "}
                  {benchmarkQuery.data.reference_confidence} · Origem:{" "}
                  {benchmarkQuery.data.reference_source}
                </p>
                <p>
                  Diferença: {benchmarkQuery.data.cost_variance_amount ?? "—"} · Oportunidade:{" "}
                  {benchmarkQuery.data.opportunity_amount ?? "—"}
                </p>
                <Link
                  className="underline"
                  to={`/analytics/purchase-benchmarks/runs/${benchmarkQuery.data.id}`}
                >
                  Abrir detalhe da run
                </Link>
              </div>
            )}
          </section>
        )
      )}
    </div>
  );
}

function InfoCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium break-all">{value}</p>
    </div>
  );
}

function TableSection({
  loading,
  empty,
  emptyText,
  children,
}: {
  loading: boolean;
  empty: boolean;
  emptyText: string;
  children: ReactNode;
}) {
  return (
    <section className="rounded-lg border border-slate-200 bg-white p-4">
      {loading ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : empty ? (
        <p className="text-sm text-slate-500">{emptyText}</p>
      ) : (
        <div className="overflow-x-auto">{children}</div>
      )}
    </section>
  );
}
