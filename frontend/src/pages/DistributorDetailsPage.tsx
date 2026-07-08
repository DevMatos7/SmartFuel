import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { z } from "zod";
import {
  createDistributionBase,
  createDistributor,
  deactivateDistributionBase,
  deactivateDistributor,
  fetchDistributor,
  fetchDistributorBases,
  fetchErpSuppliers,
  ignoreErpSupplier,
  mapErpSupplier,
  MAPPING_STATUS_LABELS,
  reactivateDistributor,
  updateDistributionBase,
  updateDistributor,
} from "../api/master-data";
import { useAuth } from "../auth/AuthProvider";

const distributorSchema = z.object({
  internal_code: z.string().min(1).max(60),
  corporate_name: z.string().min(1).max(200),
  trade_name: z.string().min(1).max(200),
  cnpj: z.string().optional(),
  notes: z.string().optional(),
  active: z.boolean(),
});

const baseSchema = z.object({
  name: z.string().min(1).max(150),
  city: z.string().min(1).max(150),
  state: z.string().length(2, "UF com 2 letras"),
  external_code: z.string().optional(),
  notes: z.string().optional(),
  active: z.boolean(),
});

type DistributorForm = z.infer<typeof distributorSchema>;
type BaseForm = z.infer<typeof baseSchema>;

type Tab = "general" | "bases" | "erp";

export function DistributorDetailsPage() {
  const { distributorId } = useParams();
  const isNew = !distributorId || distributorId === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("distributors.write");
  const canWriteBases = hasPermission("distribution_bases.write");
  const [searchParams, setSearchParams] = useSearchParams();
  const tab = (searchParams.get("tab") as Tab) || "general";
  const stationId = localStorage.getItem("active_station_id") || undefined;

  const { data: distributor } = useQuery({
    queryKey: ["distributor", distributorId],
    queryFn: () => fetchDistributor(distributorId!),
    enabled: !isNew,
  });

  const { data: bases } = useQuery({
    queryKey: ["distributor-bases", distributorId],
    queryFn: () => fetchDistributorBases(distributorId!, { page: 1, page_size: 100 }),
    enabled: !isNew && tab === "bases",
  });

  const { data: erpSuppliers } = useQuery({
    queryKey: ["erp-suppliers", distributorId, stationId],
    queryFn: () =>
      fetchErpSuppliers({
        distributor_id: distributorId,
        station_id: stationId,
        page: 1,
        page_size: 50,
      }),
    enabled: !isNew && tab === "erp" && !!distributorId,
  });

  const distributorForm = useForm<DistributorForm>({
    resolver: zodResolver(distributorSchema),
    defaultValues: {
      internal_code: "",
      corporate_name: "",
      trade_name: "",
      cnpj: "",
      notes: "",
      active: true,
    },
  });

  const baseForm = useForm<BaseForm>({
    resolver: zodResolver(baseSchema),
    defaultValues: {
      name: "",
      city: "",
      state: "",
      external_code: "",
      notes: "",
      active: true,
    },
  });

  const [editingBaseId, setEditingBaseId] = useState<string | null>(null);
  const [mapTarget, setMapTarget] = useState<string | null>(null);

  useEffect(() => {
    if (distributor) {
      distributorForm.reset({
        internal_code: distributor.internal_code,
        corporate_name: distributor.corporate_name,
        trade_name: distributor.trade_name,
        cnpj: distributor.cnpj ?? "",
        notes: distributor.notes ?? "",
        active: distributor.active,
      });
    }
  }, [distributor, distributorForm]);

  const saveDistributor = useMutation({
    mutationFn: (values: DistributorForm) => {
      const payload = {
        ...values,
        cnpj: values.cnpj?.replace(/\D/g, "") || null,
        notes: values.notes || null,
      };
      if (isNew) return createDistributor(payload);
      return updateDistributor(distributorId!, payload);
    },
    onSuccess: async (result) => {
      await queryClient.invalidateQueries({ queryKey: ["distributors"] });
      if (isNew) navigate(`/distributors/${result.id}`);
      else await queryClient.invalidateQueries({ queryKey: ["distributor", distributorId] });
    },
  });

  const deactivateMut = useMutation({
    mutationFn: (reason: string) => deactivateDistributor(distributorId!, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["distributor", distributorId] });
    },
  });

  const reactivateMut = useMutation({
    mutationFn: () => reactivateDistributor(distributorId!),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["distributor", distributorId] });
    },
  });

  const saveBase = useMutation({
    mutationFn: (values: BaseForm) => {
      const payload = {
        distributor_id: distributorId!,
        ...values,
        external_code: values.external_code || null,
        notes: values.notes || null,
        state: values.state.toUpperCase(),
      };
      if (editingBaseId) return updateDistributionBase(editingBaseId, payload);
      return createDistributionBase(payload);
    },
    onSuccess: async () => {
      baseForm.reset();
      setEditingBaseId(null);
      await queryClient.invalidateQueries({ queryKey: ["distributor-bases", distributorId] });
    },
  });

  const deactivateBaseMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => deactivateDistributionBase(id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["distributor-bases", distributorId] });
    },
  });

  const mapSupplierMut = useMutation({
    mutationFn: (erpSupplierId: string) =>
      mapErpSupplier(erpSupplierId, { distributor_id: distributorId! }),
    onSuccess: async () => {
      setMapTarget(null);
      await queryClient.invalidateQueries({ queryKey: ["erp-suppliers", distributorId] });
    },
  });

  const ignoreSupplierMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => ignoreErpSupplier(id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["erp-suppliers", distributorId] });
    },
  });

  function setTab(next: Tab) {
    const params = new URLSearchParams(searchParams);
    params.set("tab", next);
    setSearchParams(params);
  }

  const tabs: { id: Tab; label: string }[] = [
    { id: "general", label: "Geral" },
    { id: "bases", label: "Bases" },
    { id: "erp", label: "Mapeamentos ERP" },
  ];

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">
            {isNew ? "Novo distribuidor" : distributor?.trade_name ?? "Distribuidor"}
          </h1>
          {!isNew && distributor && (
            <p className="text-sm text-slate-500">{distributor.corporate_name}</p>
          )}
        </div>
        <Link to="/distributors" className="text-sm underline">
          Voltar
        </Link>
      </div>

      {saveDistributor.error && (
        <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {saveDistributor.error.message}
        </p>
      )}

      {!isNew && (
        <nav className="mt-6 flex flex-wrap gap-2 border-b border-slate-200">
          {tabs.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`border-b-2 px-3 py-2 text-sm ${
                tab === t.id ? "border-slate-900 font-medium" : "border-transparent text-slate-500"
              }`}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      )}

      {(isNew || tab === "general") && (
        <form
          className="mt-6 grid gap-4 md:grid-cols-2"
          onSubmit={distributorForm.handleSubmit((v) => saveDistributor.mutate(v))}
        >
          <div>
            <label className="text-sm font-medium">Código interno</label>
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              {...distributorForm.register("internal_code")}
              disabled={!canWrite}
            />
          </div>
          <div>
            <label className="text-sm font-medium">CNPJ</label>
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              {...distributorForm.register("cnpj")}
              disabled={!canWrite}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Razão social</label>
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              {...distributorForm.register("corporate_name")}
              disabled={!canWrite}
            />
          </div>
          <div>
            <label className="text-sm font-medium">Nome fantasia</label>
            <input
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              {...distributorForm.register("trade_name")}
              disabled={!canWrite}
            />
          </div>
          <div className="md:col-span-2">
            <label className="text-sm font-medium">Observações</label>
            <textarea
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
              rows={3}
              {...distributorForm.register("notes")}
              disabled={!canWrite}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" {...distributorForm.register("active")} disabled={!canWrite} />
            Ativo
          </label>
          {canWrite && (
            <div className="md:col-span-2">
              <button
                type="submit"
                className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
                disabled={saveDistributor.isPending}
              >
                {saveDistributor.isPending ? "Salvando..." : "Salvar"}
              </button>
            </div>
          )}

          {!isNew && distributor && canWrite && (
            <div className="md:col-span-2 border-t border-slate-200 pt-4">
              {distributor.active ? (
                <button
                  type="button"
                  className="rounded border border-red-300 px-4 py-2 text-sm text-red-700"
                  onClick={() => {
                    const reason = window.prompt("Motivo da desativação:");
                    if (reason && reason.length >= 3) deactivateMut.mutate(reason);
                  }}
                >
                  Desativar distribuidor
                </button>
              ) : (
                <button
                  type="button"
                  className="rounded border border-slate-300 px-4 py-2 text-sm"
                  onClick={() => reactivateMut.mutate()}
                >
                  Reativar distribuidor
                </button>
              )}
            </div>
          )}
        </form>
      )}

      {!isNew && tab === "bases" && (
        <div className="mt-6 space-y-6">
          {canWriteBases && (
            <form
              className="grid gap-4 rounded border border-slate-200 p-4 md:grid-cols-2"
              onSubmit={baseForm.handleSubmit((v) => saveBase.mutate(v))}
            >
              <h2 className="md:col-span-2 text-sm font-semibold">
                {editingBaseId ? "Editar base" : "Nova base de distribuição"}
              </h2>
              <div>
                <label className="text-sm font-medium">Nome</label>
                <input className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...baseForm.register("name")} />
              </div>
              <div>
                <label className="text-sm font-medium">Código externo</label>
                <input
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                  {...baseForm.register("external_code")}
                />
              </div>
              <div>
                <label className="text-sm font-medium">Cidade</label>
                <input className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...baseForm.register("city")} />
              </div>
              <div>
                <label className="text-sm font-medium">UF</label>
                <input
                  className="mt-1 w-full rounded border border-slate-300 px-3 py-2 uppercase"
                  maxLength={2}
                  {...baseForm.register("state")}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" {...baseForm.register("active")} />
                Ativa
              </label>
              <div className="flex gap-2 md:col-span-2">
                <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
                  {editingBaseId ? "Atualizar" : "Adicionar"}
                </button>
                {editingBaseId && (
                  <button
                    type="button"
                    className="rounded border border-slate-300 px-4 py-2 text-sm"
                    onClick={() => {
                      setEditingBaseId(null);
                      baseForm.reset();
                    }}
                  >
                    Cancelar
                  </button>
                )}
              </div>
            </form>
          )}

          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="px-2 py-2">Nome</th>
                  <th className="px-2 py-2">Cidade/UF</th>
                  <th className="px-2 py-2">Código</th>
                  <th className="px-2 py-2">Status</th>
                  {canWriteBases && <th className="px-2 py-2">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {bases?.items.map((base) => (
                  <tr key={base.id} className="border-b border-slate-100">
                    <td className="px-2 py-2">{base.name}</td>
                    <td className="px-2 py-2">
                      {base.city}/{base.state}
                    </td>
                    <td className="px-2 py-2">{base.external_code ?? "—"}</td>
                    <td className="px-2 py-2">{base.active ? "Ativa" : "Inativa"}</td>
                    {canWriteBases && (
                      <td className="px-2 py-2">
                        <button
                          type="button"
                          className="mr-2 underline"
                          onClick={() => {
                            setEditingBaseId(base.id);
                            baseForm.reset({
                              name: base.name,
                              city: base.city,
                              state: base.state,
                              external_code: base.external_code ?? "",
                              notes: base.notes ?? "",
                              active: base.active,
                            });
                          }}
                        >
                          Editar
                        </button>
                        {base.active && (
                          <button
                            type="button"
                            className="text-red-700 underline"
                            onClick={() => {
                              const reason = window.prompt("Motivo:");
                              if (reason && reason.length >= 3) deactivateBaseMut.mutate({ id: base.id, reason });
                            }}
                          >
                            Desativar
                          </button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {!bases?.items.length && (
                  <tr>
                    <td colSpan={canWriteBases ? 5 : 4} className="px-2 py-4 text-slate-500">
                      Nenhuma base cadastrada.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!isNew && tab === "erp" && (
        <div className="mt-6 space-y-4">
          <p className="text-sm text-slate-500">
            Fornecedores do ERP vinculados a este distribuidor ou pendentes de mapeamento.
          </p>
          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead className="border-b border-slate-200 text-slate-500">
                <tr>
                  <th className="px-2 py-2">Nome ERP</th>
                  <th className="px-2 py-2">CNPJ</th>
                  <th className="px-2 py-2">Status</th>
                  {canWrite && <th className="px-2 py-2">Ações</th>}
                </tr>
              </thead>
              <tbody>
                {erpSuppliers?.items.map((s) => (
                  <tr key={s.id} className="border-b border-slate-100">
                    <td className="px-2 py-2">{s.erp_name}</td>
                    <td className="px-2 py-2">{s.erp_cnpj ?? "—"}</td>
                    <td className="px-2 py-2">{MAPPING_STATUS_LABELS[s.mapping_status] ?? s.mapping_status}</td>
                    {canWrite && (
                      <td className="px-2 py-2">
                        {s.mapping_status === "PENDING" && (
                          <>
                            <button
                              type="button"
                              className="mr-2 underline"
                              disabled={mapSupplierMut.isPending && mapTarget === s.id}
                              onClick={() => {
                                setMapTarget(s.id);
                                mapSupplierMut.mutate(s.id);
                              }}
                            >
                              Vincular
                            </button>
                            <button
                              type="button"
                              className="text-slate-600 underline"
                              onClick={() => {
                                const reason = window.prompt("Motivo para ignorar:");
                                if (reason && reason.length >= 3) ignoreSupplierMut.mutate({ id: s.id, reason });
                              }}
                            >
                              Ignorar
                            </button>
                          </>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
                {!erpSuppliers?.items.length && (
                  <tr>
                    <td colSpan={canWrite ? 4 : 3} className="px-2 py-4 text-slate-500">
                      Nenhum fornecedor ERP encontrado.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
