import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { fetchAuditLogs, type AuditLogItem } from "../api/audit";

function JsonPanel({ title, data }: { title: string; data: Record<string, unknown> | null }) {
  if (!data) return null;
  return (
    <div className="mt-4">
      <h3 className="text-sm font-medium">{title}</h3>
      <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-50 p-3 text-xs">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export function AuditPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [selected, setSelected] = useState<AuditLogItem | null>(null);

  const filters = useMemo(
    () => ({
      entity_type: searchParams.get("entity_type") || undefined,
      action: searchParams.get("action") || undefined,
      user_id: searchParams.get("user_id") || undefined,
      date_from: searchParams.get("date_from") || undefined,
      date_to: searchParams.get("date_to") || undefined,
      page: Number(searchParams.get("page") || "1"),
      page_size: Number(searchParams.get("page_size") || "20"),
    }),
    [searchParams],
  );

  const { data, isLoading, isError } = useQuery({
    queryKey: ["audit", filters],
    queryFn: () => fetchAuditLogs(filters),
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
      <h1 className="text-xl font-semibold">Auditoria</h1>
      <p className="text-sm text-slate-500">Registros administrativos com filtros e detalhes.</p>

      <div className="mt-6 grid gap-3 md:grid-cols-4">
        <div>
          <label className="text-xs text-slate-500">Entidade</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.entity_type ?? ""}
            onChange={(e) => updateFilter("entity_type", e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Ação</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.action ?? ""}
            onChange={(e) => updateFilter("action", e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Usuário (ID)</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.user_id ?? ""}
            onChange={(e) => updateFilter("user_id", e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">De</label>
          <input
            type="datetime-local"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.date_from ?? ""}
            onChange={(e) => updateFilter("date_from", e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Até</label>
          <input
            type="datetime-local"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.date_to ?? ""}
            onChange={(e) => updateFilter("date_to", e.target.value)}
          />
        </div>
      </div>

      {isLoading && <p className="mt-6">Carregando...</p>}
      {isError && (
        <p className="mt-6 text-sm text-red-700" role="alert">
          Não foi possível carregar a auditoria.
        </p>
      )}

      {!isLoading && !isError && data?.items.length === 0 && (
        <p className="mt-6 text-sm text-slate-500">Nenhum registro encontrado.</p>
      )}

      {data && data.items.length > 0 && (
        <>
          <div className="mt-6 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="px-2 py-2">Data</th>
                  <th className="px-2 py-2">Entidade</th>
                  <th className="px-2 py-2">Ação</th>
                  <th className="px-2 py-2">Request ID</th>
                  <th className="px-2 py-2">IP</th>
                  <th className="px-2 py-2">Detalhes</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id} className="border-b border-slate-100">
                    <td className="px-2 py-2">{new Date(item.created_at).toLocaleString("pt-BR")}</td>
                    <td className="px-2 py-2">{item.entity_type}</td>
                    <td className="px-2 py-2">{item.action}</td>
                    <td className="px-2 py-2 font-mono text-xs">{item.request_id ?? "—"}</td>
                    <td className="px-2 py-2">{item.ip_address ?? "—"}</td>
                    <td className="px-2 py-2">
                      <button
                        type="button"
                        className="text-slate-900 underline"
                        onClick={() => setSelected(item)}
                      >
                        Ver
                      </button>
                    </td>
                  </tr>
                ))}
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
              Página {filters.page} de {totalPages} ({data.total} registros)
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

      {selected && (
        <div className="mt-6 rounded border border-slate-200 p-4">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">Detalhe do registro</h2>
            <button type="button" className="text-sm underline" onClick={() => setSelected(null)}>
              Fechar
            </button>
          </div>
          <p className="mt-2 text-sm text-slate-600">
            {selected.entity_type} / {selected.action}
          </p>
          <JsonPanel title="Antes" data={selected.before_data} />
          <JsonPanel title="Depois" data={selected.after_data} />
          <JsonPanel title="Metadata" data={selected.metadata} />
        </div>
      )}
    </div>
  );
}
