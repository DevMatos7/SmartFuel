import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";
import {
  createPaymentTerm,
  deactivatePaymentTerm,
  fetchPaymentTerms,
  PAYMENT_TYPE_LABELS,
  reactivatePaymentTerm,
  updatePaymentTerm,
} from "../api/master-data";
import { useAuth } from "../auth/AuthProvider";

const schema = z.object({
  code: z.string().min(1).max(60),
  name: z.string().min(1).max(120),
  payment_type: z.string().min(1),
  days: z.coerce.number().int().min(0),
  description: z.string().optional(),
  active: z.boolean(),
});

type FormValues = z.infer<typeof schema>;

export function PaymentTermsPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("payment_terms.write");
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [editingId, setEditingId] = useState<string | null>(null);

  const filters = useMemo(
    () => ({
      search: searchParams.get("search") || undefined,
      payment_type: searchParams.get("payment_type") || undefined,
      active: searchParams.get("active") === "false" ? false : searchParams.get("active") === "true" ? true : undefined,
      page: Number(searchParams.get("page") || "1"),
      page_size: Number(searchParams.get("page_size") || "20"),
    }),
    [searchParams],
  );

  const { data, isLoading } = useQuery({
    queryKey: ["payment-terms", filters],
    queryFn: () => fetchPaymentTerms(filters),
  });

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      code: "",
      name: "",
      payment_type: "TERM",
      days: 30,
      description: "",
      active: true,
    },
  });

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams);
    if (value) next.set(key, value);
    else next.delete(key);
    if (key !== "page") next.set("page", "1");
    setSearchParams(next);
  }

  const saveMutation = useMutation({
    mutationFn: (values: FormValues) => {
      const payload = { ...values, description: values.description || null };
      if (editingId) return updatePaymentTerm(editingId, payload);
      return createPaymentTerm(payload);
    },
    onSuccess: async () => {
      form.reset({ code: "", name: "", payment_type: "TERM", days: 30, description: "", active: true });
      setEditingId(null);
      await queryClient.invalidateQueries({ queryKey: ["payment-terms"] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => deactivatePaymentTerm(id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["payment-terms"] });
    },
  });

  const reactivateMutation = useMutation({
    mutationFn: (id: string) => reactivatePaymentTerm(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["payment-terms"] });
    },
  });

  const totalPages = data ? Math.max(1, Math.ceil(data.total / filters.page_size)) : 1;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div>
        <h1 className="text-xl font-semibold">Prazos de pagamento</h1>
        <p className="text-sm text-slate-500">Condições comerciais utilizadas nas operações de compra.</p>
      </div>

      <div className="mt-6 grid gap-3 md:grid-cols-3">
        <div>
          <label className="text-xs text-slate-500">Busca</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.search ?? ""}
            onChange={(e) => updateFilter("search", e.target.value)}
          />
        </div>
        <div>
          <label className="text-xs text-slate-500">Tipo</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={filters.payment_type ?? ""}
            onChange={(e) => updateFilter("payment_type", e.target.value)}
          >
            <option value="">Todos</option>
            <option value="CASH">À vista</option>
            <option value="TERM">Prazo</option>
            <option value="ANTICIPATED">Antecipado</option>
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

      {canWrite && (
        <form
          className="mt-6 grid gap-4 rounded border border-slate-200 p-4 md:grid-cols-3"
          onSubmit={form.handleSubmit((v) => saveMutation.mutate(v))}
        >
          <h2 className="md:col-span-3 text-sm font-semibold">
            {editingId ? "Editar prazo" : "Novo prazo de pagamento"}
          </h2>
          <div>
            <label className="text-sm font-medium">Código</label>
            <input className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("code")} />
          </div>
          <div>
            <label className="text-sm font-medium">Nome</label>
            <input className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("name")} />
          </div>
          <div>
            <label className="text-sm font-medium">Tipo</label>
            <select className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("payment_type")}>
              <option value="CASH">À vista</option>
              <option value="TERM">Prazo</option>
              <option value="ANTICIPATED">Antecipado</option>
            </select>
          </div>
          <div>
            <label className="text-sm font-medium">Dias</label>
            <input
              type="number"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              {...form.register("days")}
            />
          </div>
          <div className="md:col-span-2">
            <label className="text-sm font-medium">Descrição</label>
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              {...form.register("description")}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...form.register("active")} />
            Ativo
          </label>
          <div className="flex gap-2 md:col-span-3">
            <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
              {editingId ? "Atualizar" : "Adicionar"}
            </button>
            {editingId && (
              <button
                type="button"
                className="rounded border border-slate-300 px-4 py-2 text-sm"
                onClick={() => {
                  setEditingId(null);
                  form.reset();
                }}
              >
                Cancelar
              </button>
            )}
          </div>
        </form>
      )}

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
                  <th className="px-2 py-2">Tipo</th>
                  <th className="px-2 py-2">Dias</th>
                  <th className="px-2 py-2">Status</th>
                  {canWrite && <th className="px-2 py-2">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {data?.items.map((term) => (
                  <tr key={term.id} className="border-b border-slate-100">
                    <td className="px-2 py-2 font-mono text-xs">{term.code}</td>
                    <td className="px-2 py-2">{term.name}</td>
                    <td className="px-2 py-2">{PAYMENT_TYPE_LABELS[term.payment_type] ?? term.payment_type}</td>
                    <td className="px-2 py-2">{term.days}</td>
                    <td className="px-2 py-2">{term.active ? "Ativo" : "Inativo"}</td>
                    {canWrite && (
                      <td className="px-2 py-2">
                        <button
                          type="button"
                          className="mr-2 underline"
                          onClick={() => {
                            setEditingId(term.id);
                            form.reset({
                              code: term.code,
                              name: term.name,
                              payment_type: term.payment_type,
                              days: term.days,
                              description: term.description ?? "",
                              active: term.active,
                            });
                          }}
                        >
                          Editar
                        </button>
                        {term.active ? (
                          <button
                            type="button"
                            className="text-red-700 underline"
                            onClick={() => {
                              const reason = window.prompt("Motivo:");
                              if (reason && reason.length >= 3) deactivateMutation.mutate({ id: term.id, reason });
                            }}
                          >
                            Desativar
                          </button>
                        ) : (
                          <button type="button" className="underline" onClick={() => reactivateMutation.mutate(term.id)}>
                            Reativar
                          </button>
                        )}
                      </td>
                    )}
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
