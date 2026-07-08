import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchProducts } from "../api/master-data";
import { useAuth } from "../auth/AuthProvider";

export function ProductsPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("products.write");
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(
    () => ({
      search: searchParams.get("search") || undefined,
      fuel_family: searchParams.get("fuel_family") || undefined,
      active: searchParams.get("active") === "false" ? false : searchParams.get("active") === "true" ? true : undefined,
      page: Number(searchParams.get("page") || "1"),
      page_size: Number(searchParams.get("page_size") || "20"),
    }),
    [searchParams],
  );

  const { data, isLoading } = useQuery({
    queryKey: ["products", filters],
    queryFn: () => fetchProducts(filters),
  });

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.set("page", "1");
    setSearchParams(next);
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / filters.page_size)) : 1;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Produtos</h1>
          <p className="text-sm text-slate-500">Catálogo canônico de combustíveis da organização.</p>
        </div>
        {canWrite && (
          <Link to="/products/new" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            Novo produto
          </Link>
        )}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <div>
          <label className="text-xs text-slate-500">Busca</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.search ?? ""}
            onChange={(e) => updateFilter("search", e.target.value)}
            placeholder="Nome ou código..."
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Família</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.fuel_family ?? ""}
            onChange={(e) => updateFilter("fuel_family", e.target.value)}
          >
            <option value="">Todas</option>
            <option value="ETHANOL">Etanol</option>
            <option value="GASOLINE_C">Gasolina C</option>
            <option value="DIESEL_B_S10">Diesel B S10</option>
            <option value="DIESEL_B_S500">Diesel B S500</option>
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500">Status</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.active === undefined ? "" : filters.active ? "true" : "false"}
            onChange={(e) => updateFilter("active", e.target.value)}
          >
            <option value="">Todos</option>
            <option value="true">Ativos</option>
            <option value="false">Inativos</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <p className="mt-6">Carregando...</p>
      ) : (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="px-2 py-2">Código</th>
                  <th className="px-2 py-2">Nome</th>
                  <th className="px-2 py-2">Família</th>
                  <th className="px-2 py-2">Variante</th>
                  <th className="px-2 py-2">Compra</th>
                  <th className="px-2 py-2">Venda</th>
                  <th className="px-2 py-2">Status</th>
                  {canWrite && <th className="px-2 py-2">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {data?.items.map((product) => (
                  <tr key={product.id} className="border-b border-slate-100">
                    <td className="px-2 py-2 font-mono text-xs">{product.code}</td>
                    <td className="px-2 py-2">{product.name}</td>
                    <td className="px-2 py-2">{product.fuel_family}</td>
                    <td className="px-2 py-2">{product.commercial_variant}</td>
                    <td className="px-2 py-2">{product.purchasable ? "Sim" : "Não"}</td>
                    <td className="px-2 py-2">{product.sellable ? "Sim" : "Não"}</td>
                    <td className="px-2 py-2">{product.active ? "Ativo" : "Inativo"}</td>
                    {canWrite && (
                      <td className="px-2 py-2">
                        <Link to={`/products/${product.id}`} className="text-slate-900 underline">
                          Editar
                        </Link>
                      </td>
                    )}
                  </tr>
                ))}
                {!data?.items.length && (
                  <tr>
                    <td colSpan={canWrite ? 8 : 7} className="px-2 py-4 text-slate-500">
                      Nenhum produto encontrado.
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
    </div>
  );
}
