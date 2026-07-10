import { useQueries, useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchXpertSummary } from "../api/xpert-integration";
import {
  fetchErpProducts,
  fetchProducts,
  MAPPING_STATUS_LABELS,
  type ErpProduct,
} from "../api/master-data";
import { BulkMappingDialog } from "../components/master-data/BulkMappingDialog";
import { MappingDrawer } from "../components/master-data/MappingDrawer";
import { useAuth } from "../auth/AuthProvider";

const STATUS_CARDS = ["PENDING", "MAPPED", "IGNORED", "CONFLICT"] as const;

export function ErpProductsPage() {
  const { hasPermission } = useAuth();
  const canMap = hasPermission("erp_products.map");
  const canImport = hasPermission("erp_products.import");
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [drawerProduct, setDrawerProduct] = useState<ErpProduct | null>(null);
  const [bulkOpen, setBulkOpen] = useState(false);

  const stationId = searchParams.get("station_id") || localStorage.getItem("active_station_id") || undefined;

  const filters = useMemo(
    () => ({
      station_id: stationId,
      mapping_status: searchParams.get("mapping_status") || undefined,
      search: searchParams.get("search") || undefined,
      active: searchParams.get("active") === "false" ? false : searchParams.get("active") === "true" ? true : undefined,
      page: Number(searchParams.get("page") || "1"),
      page_size: Number(searchParams.get("page_size") || "20"),
    }),
    [searchParams, stationId],
  );

  const { data, isLoading } = useQuery({
    queryKey: ["erp-products", filters],
    queryFn: () => fetchErpProducts(filters),
  });

  const { data: xpertSummary } = useQuery({
    queryKey: ["xpert-summary"],
    queryFn: fetchXpertSummary,
  });

  const statusQueries = useQueries({
    queries: STATUS_CARDS.map((status) => ({
      queryKey: ["erp-products-count", status, stationId],
      queryFn: () =>
        fetchErpProducts({
          station_id: stationId,
          mapping_status: status,
          page: 1,
          page_size: 1,
        }),
    })),
  });

  const { data: products } = useQuery({
    queryKey: ["products", { active: true }],
    queryFn: () => fetchProducts({ active: true, page: 1, page_size: 100 }),
  });

  const productMap = useMemo(() => {
    const map = new Map<string, string>();
    products?.items.forEach((p) => map.set(p.id, p.name));
    return map;
  }, [products]);

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.set("page", "1");
    setSearchParams(next);
  }

  function toggleSelect(id: string) {
    setSelectedIds((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  }

  function toggleSelectAll() {
    if (!data?.items.length) return;
    const pageIds = data.items.map((i) => i.id);
    const allSelected = pageIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !pageIds.includes(id)));
    } else {
      setSelectedIds((prev) => Array.from(new Set([...prev, ...pageIds])));
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / filters.page_size)) : 1;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Produtos ERP</h1>
          <p className="text-sm text-slate-500">Mapeamento dos produtos importados do ERP para o catálogo canônico.</p>
          {xpertSummary && (
            <p className="mt-2 text-xs text-slate-600">
              Última sincronização XPERT:{" "}
              {xpertSummary.last_success_at
                ? new Date(xpertSummary.last_success_at).toLocaleString()
                : "nunca"}
              {" · "}
              Status: {xpertSummary.status}
              {" · "}
              {xpertSummary.pending_products} produto(s) aguardando mapeamento
            </p>
          )}
        </div>
        {canImport && (
          <Link to="/erp-products/import" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            Importar CSV
          </Link>
        )}
      </div>

      <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {STATUS_CARDS.map((status, index) => (
          <button
            key={status}
            type="button"
            className={`rounded-lg border p-4 text-left transition ${
              filters.mapping_status === status
                ? "border-slate-900 bg-slate-50"
                : "border-slate-200 hover:border-slate-300"
            }`}
            onClick={() => updateFilter("mapping_status", filters.mapping_status === status ? "" : status)}
          >
            <p className="text-xs uppercase tracking-wide text-slate-500">{MAPPING_STATUS_LABELS[status]}</p>
            <p className="mt-1 text-2xl font-semibold">{statusQueries[index].data?.total ?? "—"}</p>
          </button>
        ))}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <div>
          <label className="text-xs text-slate-500">Busca</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.search ?? ""}
            onChange={(e) => updateFilter("search", e.target.value)}
            placeholder="Descrição ou código..."
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Status de mapeamento</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.mapping_status ?? ""}
            onChange={(e) => updateFilter("mapping_status", e.target.value)}
          >
            <option value="">Todos</option>
            {STATUS_CARDS.map((s) => (
              <option key={s} value={s}>
                {MAPPING_STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500">Ativo no ERP</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.active === undefined ? "" : filters.active ? "true" : "false"}
            onChange={(e) => updateFilter("active", e.target.value)}
          >
            <option value="">Todos</option>
            <option value="true">Sim</option>
            <option value="false">Não</option>
          </select>
        </div>
      </div>

      {canMap && selectedIds.length > 0 && (
        <div className="mt-4 flex items-center gap-3 rounded bg-slate-50 px-4 py-3 text-sm">
          <span>{selectedIds.length} selecionado(s)</span>
          <button
            type="button"
            className="rounded bg-slate-900 px-3 py-1.5 text-white"
            onClick={() => setBulkOpen(true)}
          >
            Mapear em lote
          </button>
          <button type="button" className="underline" onClick={() => setSelectedIds([])}>
            Limpar
          </button>
        </div>
      )}

      {isLoading ? (
        <p className="mt-6">Carregando...</p>
      ) : (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500">
                <tr>
                  {canMap && (
                    <th className="px-2 py-2">
                      <input
                        type="checkbox"
                        aria-label="Selecionar todos"
                        checked={!!data?.items.length && data.items.every((i) => selectedIds.includes(i.id))}
                        onChange={toggleSelectAll}
                      />
                    </th>
                  )}
                  <th className="px-2 py-2">Descrição ERP</th>
                  <th className="px-2 py-2">Código</th>
                  <th className="px-2 py-2">Status</th>
                  <th className="px-2 py-2">Produto canônico</th>
                  <th className="px-2 py-2">Ações</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((item) => (
                  <tr key={item.id} className="border-b border-slate-100">
                    {canMap && (
                      <td className="px-2 py-2">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(item.id)}
                          onChange={() => toggleSelect(item.id)}
                        />
                      </td>
                    )}
                    <td className="px-2 py-2">{item.erp_description}</td>
                    <td className="px-2 py-2 font-mono text-xs">{item.erp_product_code ?? item.erp_product_id}</td>
                    <td className="px-2 py-2">
                      <span className="rounded bg-slate-100 px-2 py-0.5 text-xs">
                        {MAPPING_STATUS_LABELS[item.mapping_status] ?? item.mapping_status}
                      </span>
                    </td>
                    <td className="px-2 py-2">
                      {item.canonical_product_id
                        ? productMap.get(item.canonical_product_id) ?? item.canonical_product_id
                        : "—"}
                    </td>
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        className="text-slate-900 underline"
                        onClick={() => setDrawerProduct(item)}
                      >
                        Detalhes
                      </button>
                    </td>
                  </tr>
                ))}
                {!data?.items.length && (
                  <tr>
                    <td colSpan={canMap ? 6 : 5} className="px-2 py-4 text-slate-500">
                      Nenhum produto ERP encontrado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center gap-3 text-sm">
            <button
              type="button"
              className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
              disabled={filters.page <= 1}
              onClick={() => updateFilter("page", String(filters.page - 1))}
            >
              Anterior
            </button>
            <span>
              Página {filters.page} de {totalPages} ({data?.total ?? 0} registros)
            </span>
            <button
              type="button"
              className="rounded border border-slate-300 px-3 py-1 disabled:opacity-50"
              disabled={filters.page >= totalPages}
              onClick={() => updateFilter("page", String(filters.page + 1))}
            >
              Próxima
            </button>
          </div>
        </>
      )}

      <MappingDrawer
        erpProduct={drawerProduct}
        open={!!drawerProduct}
        onClose={() => setDrawerProduct(null)}
        onSuccess={() => setSelectedIds([])}
      />

      <BulkMappingDialog
        open={bulkOpen}
        selectedIds={selectedIds}
        onClose={() => setBulkOpen(false)}
        onSuccess={() => setSelectedIds([])}
      />
    </div>
  );
}
