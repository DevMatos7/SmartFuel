import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { fetchQuotes } from "../api/quotes";
import { useAuth } from "../auth/AuthProvider";
import { QuoteStatusBadge } from "../components/quotes/QuoteStatusBadge";

export function QuotesPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("quotes.write");
  const [searchParams, setSearchParams] = useSearchParams();

  const filters = useMemo(
    () => ({
      status: searchParams.get("status") || undefined,
      source_channel: searchParams.get("source_channel") || undefined,
      search: searchParams.get("search") || undefined,
      page: Number(searchParams.get("page") || "1"),
      page_size: Number(searchParams.get("page_size") || "20"),
    }),
    [searchParams],
  );

  const { data, isLoading, isError } = useQuery({
    queryKey: ["quotes", filters],
    queryFn: () => fetchQuotes(filters),
  });

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.set("page", "1");
    setSearchParams(next);
  }

  const summary = data?.summary ?? {};

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Cotações</h1>
          <p className="text-sm text-slate-500">Central de cotações manuais por posto e distribuidora.</p>
        </div>
        {canWrite && (
          <Link to="/quotes/new" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            Nova cotação
          </Link>
        )}
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        {[
          ["ACTIVE", "Ativas"],
          ["DRAFT", "Rascunhos"],
          ["EXPIRED", "Expiradas"],
          ["CANCELLED", "Canceladas"],
          ["SUPERSEDED", "Substituídas"],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => updateFilter("status", filters.status === key ? "" : key)}
            className={`rounded-lg border p-4 text-left ${
              filters.status === key ? "border-slate-900 bg-slate-50" : "border-slate-200 bg-white"
            }`}
          >
            <div className="text-2xl font-semibold">{summary[key] ?? 0}</div>
            <div className="text-sm text-slate-500">{label}</div>
          </button>
        ))}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label className="text-xs text-slate-500">Busca</label>
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={filters.search ?? ""}
              onChange={(e) => updateFilter("search", e.target.value)}
              placeholder="Vendedor, referência..."
            />
          </div>
          <div>
            <label className="text-xs text-slate-500">Canal</label>
            <select
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={filters.source_channel ?? ""}
              onChange={(e) => updateFilter("source_channel", e.target.value)}
            >
              <option value="">Todos</option>
              <option value="WHATSAPP">WhatsApp</option>
              <option value="PORTAL">Portal</option>
              <option value="EMAIL">E-mail</option>
              <option value="PHONE">Telefone</option>
              <option value="OTHER">Outro</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500">Status</label>
            <select
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={filters.status ?? ""}
              onChange={(e) => updateFilter("status", e.target.value)}
            >
              <option value="">Todos</option>
              <option value="DRAFT">Rascunho</option>
              <option value="ACTIVE">Ativa</option>
              <option value="EXPIRED">Expirada</option>
              <option value="CANCELLED">Cancelada</option>
            </select>
          </div>
        </div>

        {isLoading && <p className="mt-6 text-sm text-slate-500">Carregando cotações...</p>}
        {isError && <p className="mt-6 text-sm text-rose-600">Não foi possível carregar as cotações.</p>}
        {!isLoading && !isError && data?.items.length === 0 && (
          <p className="mt-6 text-sm text-slate-500">Nenhuma cotação encontrada.</p>
        )}

        {data && data.items.length > 0 && (
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b text-left text-slate-500">
                  <th className="py-2 pr-4">Número</th>
                  <th className="py-2 pr-4">Data</th>
                  <th className="py-2 pr-4">Validade</th>
                  <th className="py-2 pr-4">Canal</th>
                  <th className="py-2 pr-4">Itens</th>
                  <th className="py-2 pr-4">Status</th>
                  <th className="py-2">Ações</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((quote) => (
                  <tr key={quote.id} className="border-b border-slate-100">
                    <td className="py-3 pr-4 font-medium">#{String(quote.quote_number).padStart(6, "0")}</td>
                    <td className="py-3 pr-4">{new Date(quote.quoted_at).toLocaleString("pt-BR")}</td>
                    <td className="py-3 pr-4">{new Date(quote.valid_until).toLocaleString("pt-BR")}</td>
                    <td className="py-3 pr-4">{quote.source_channel}</td>
                    <td className="py-3 pr-4">{quote.item_count}</td>
                    <td className="py-3 pr-4">
                      <QuoteStatusBadge status={quote.status} effectiveStatus={quote.effective_status} />
                    </td>
                    <td className="py-3">
                      <Link to={`/quotes/${quote.id}`} className="text-slate-900 underline">
                        Abrir
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
