import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchDistributors } from "../api/master-data";
import { useAuth } from "../auth/AuthProvider";

export function DistributorsPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("distributors.write");
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(
    () => ({
      search: searchParams.get("search") || undefined,
      registration_status: searchParams.get("registration_status") || undefined,
      active: searchParams.get("active") === "false" ? false : searchParams.get("active") === "true" ? true : undefined,
      page: Number(searchParams.get("page") || "1"),
      page_size: Number(searchParams.get("page_size") || "20"),
    }),
    [searchParams],
  );

  const { data, isLoading } = useQuery({
    queryKey: ["distributors", filters],
    queryFn: () => fetchDistributors(filters),
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
          <h1 className="text-xl font-semibold">Distribuidores</h1>
          <p className="text-sm text-slate-500">Cadastro de distribuidoras e bases de abastecimento.</p>
        </div>
        {canWrite && (
          <Link to="/distributors/new" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            Novo distribuidor
          </Link>
        )}
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <div>
          <label className="text-xs text-slate-500">Busca</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.search ?? ""}
            onChange={(e) => updateFilter("search", e.target.value)}
            placeholder="Nome, CNPJ ou código..."
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Cadastro</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.registration_status ?? ""}
            onChange={(e) => updateFilter("registration_status", e.target.value)}
          >
            <option value="">Todos</option>
            <option value="COMPLETE">Completo</option>
            <option value="INCOMPLETE">Incompleto</option>
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
                  <th className="px-2 py-2">Nome fantasia</th>
                  <th className="px-2 py-2">CNPJ</th>
                  <th className="px-2 py-2">Cadastro</th>
                  <th className="px-2 py-2">Status</th>
                  <th className="px-2 py-2">Ações</th>
                </tr>
              </thead>
              <tbody>
                {data?.items.map((d) => (
                  <tr key={d.id} className="border-b border-slate-100">
                    <td className="px-2 py-2 font-mono text-xs">{d.internal_code}</td>
                    <td className="px-2 py-2">{d.trade_name}</td>
                    <td className="px-2 py-2">{d.cnpj ?? "—"}</td>
                    <td className="px-2 py-2">{d.registration_status === "COMPLETE" ? "Completo" : "Incompleto"}</td>
                    <td className="px-2 py-2">{d.active ? "Ativo" : "Inativo"}</td>
                    <td className="px-2 py-2">
                      <Link to={`/distributors/${d.id}`} className="text-slate-900 underline">
                        Detalhes
                      </Link>
                    </td>
                  </tr>
                ))}
                {!data?.items.length && (
                  <tr>
                    <td colSpan={6} className="px-2 py-4 text-slate-500">
                      Nenhum distribuidor encontrado.
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
