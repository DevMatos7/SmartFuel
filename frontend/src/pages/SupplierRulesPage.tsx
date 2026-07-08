import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { useSearchParams } from "react-router-dom";
import { z } from "zod";
import { fetchStations } from "../api/stations";
import {
  closeSupplierRuleValidity,
  createSupplierRule,
  deactivateSupplierRule,
  fetchDistributors,
  fetchEffectiveSupplierRule,
  fetchProducts,
  fetchSupplierRules,
  RULE_SOURCE_LABELS,
  type EffectiveRule,
} from "../api/master-data";
import { useAuth } from "../auth/AuthProvider";

const ruleSchema = z.object({
  station_id: z.string().min(1, "Posto obrigatório"),
  distributor_id: z.string().min(1, "Distribuidor obrigatório"),
  product_id: z.string().optional(),
  allowed: z.boolean(),
  minimum_volume_liters: z.coerce.number().positive(),
  valid_from: z.string().min(1),
  valid_until: z.string().optional(),
  contract_reference: z.string().optional(),
  reason: z.string().optional(),
  notes: z.string().optional(),
  priority: z.coerce.number().int().min(1),
  active: z.boolean(),
});

type RuleForm = z.infer<typeof ruleSchema>;

function EffectiveRuleSimulator() {
  const [stationId, setStationId] = useState(localStorage.getItem("active_station_id") ?? "");
  const [distributorId, setDistributorId] = useState("");
  const [productId, setProductId] = useState("");
  const [referenceDate, setReferenceDate] = useState(new Date().toISOString().slice(0, 10));
  const [result, setResult] = useState<EffectiveRule | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { data: stations } = useQuery({
    queryKey: ["stations"],
    queryFn: () => fetchStations({ page: 1, page_size: 100, active: true }),
  });

  const { data: distributors } = useQuery({
    queryKey: ["distributors", { active: true }],
    queryFn: () => fetchDistributors({ active: true, page: 1, page_size: 100 }),
  });

  const { data: products } = useQuery({
    queryKey: ["products", { active: true }],
    queryFn: () => fetchProducts({ active: true, page: 1, page_size: 100 }),
  });

  async function simulate() {
    if (!stationId || !distributorId || !productId) {
      setError("Preencha posto, distribuidor e produto.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await fetchEffectiveSupplierRule({
        station_id: stationId,
        distributor_id: distributorId,
        product_id: productId,
        reference_date: referenceDate,
      });
      setResult(data);
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Erro ao simular.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="rounded border border-slate-200 p-4">
      <h2 className="text-sm font-semibold">Simulador de regra efetiva</h2>
      <p className="mt-1 text-xs text-slate-500">
        Verifique qual regra seria aplicada para um posto, distribuidor e produto em uma data.
      </p>

      <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="text-xs text-slate-500">Posto</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={stationId}
            onChange={(e) => setStationId(e.target.value)}
          >
            <option value="">Selecione...</option>
            {stations?.items.map((s) => (
              <option key={s.id} value={s.id}>
                {s.trade_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500">Distribuidor</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={distributorId}
            onChange={(e) => setDistributorId(e.target.value)}
          >
            <option value="">Selecione...</option>
            {distributors?.items.map((d) => (
              <option key={d.id} value={d.id}>
                {d.trade_name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500">Produto</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={productId}
            onChange={(e) => setProductId(e.target.value)}
          >
            <option value="">Selecione...</option>
            {products?.items.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs text-slate-500">Data de referência</label>
          <input
            type="date"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
            value={referenceDate}
            onChange={(e) => setReferenceDate(e.target.value)}
          />
        </div>
      </div>

      <button
        type="button"
        className="mt-4 rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
        disabled={loading}
        onClick={simulate}
      >
        {loading ? "Simulando..." : "Simular"}
      </button>

      {error && (
        <p className="mt-3 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      {result && (
        <dl className="mt-4 grid gap-2 rounded bg-slate-50 p-4 text-sm md:grid-cols-2">
          <div>
            <dt className="text-slate-500">Permitido</dt>
            <dd className="font-medium">{result.allowed ? "Sim" : "Não"}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Volume mínimo (L)</dt>
            <dd className="font-medium">{result.minimum_volume_liters}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Origem da regra</dt>
            <dd className="font-medium">{RULE_SOURCE_LABELS[result.rule_source] ?? result.rule_source}</dd>
          </div>
          <div>
            <dt className="text-slate-500">Vigência</dt>
            <dd className="font-medium">
              {result.valid_from ?? "—"}
              {result.valid_until ? ` até ${result.valid_until}` : ""}
            </dd>
          </div>
          {result.reason && (
            <div className="md:col-span-2">
              <dt className="text-slate-500">Motivo</dt>
              <dd>{result.reason}</dd>
            </div>
          )}
        </dl>
      )}
    </section>
  );
}

export function SupplierRulesPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("supplier_rules.write");
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const stationId = searchParams.get("station_id") || localStorage.getItem("active_station_id") || undefined;

  const filters = useMemo(
    () => ({
      station_id: stationId,
      distributor_id: searchParams.get("distributor_id") || undefined,
      product_id: searchParams.get("product_id") || undefined,
      allowed: searchParams.get("allowed") === "false" ? false : searchParams.get("allowed") === "true" ? true : undefined,
      active: searchParams.get("active") === "false" ? false : searchParams.get("active") === "true" ? true : undefined,
      page: Number(searchParams.get("page") || "1"),
      page_size: Number(searchParams.get("page_size") || "20"),
    }),
    [searchParams, stationId],
  );

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-rules", filters],
    queryFn: () => fetchSupplierRules(filters),
  });

  const { data: stations } = useQuery({
    queryKey: ["stations"],
    queryFn: () => fetchStations({ page: 1, page_size: 100, active: true }),
  });

  const { data: distributors } = useQuery({
    queryKey: ["distributors"],
    queryFn: () => fetchDistributors({ active: true, page: 1, page_size: 100 }),
  });

  const { data: products } = useQuery({
    queryKey: ["products"],
    queryFn: () => fetchProducts({ active: true, page: 1, page_size: 100 }),
  });

  const form = useForm<RuleForm>({
    resolver: zodResolver(ruleSchema),
    defaultValues: {
      station_id: stationId ?? "",
      distributor_id: "",
      product_id: "",
      allowed: true,
      minimum_volume_liters: 5000,
      valid_from: new Date().toISOString().slice(0, 10),
      valid_until: "",
      contract_reference: "",
      reason: "",
      notes: "",
      priority: 100,
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
    mutationFn: (values: RuleForm) =>
      createSupplierRule({
        ...values,
        product_id: values.product_id || null,
        valid_until: values.valid_until || null,
        contract_reference: values.contract_reference || null,
        reason: values.reason || null,
        notes: values.notes || null,
        minimum_volume_liters: String(values.minimum_volume_liters),
      }),
    onSuccess: async () => {
      form.reset();
      await queryClient.invalidateQueries({ queryKey: ["supplier-rules"] });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => deactivateSupplierRule(id, reason),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["supplier-rules"] });
    },
  });

  const closeMutation = useMutation({
    mutationFn: ({ id, valid_until, reason }: { id: string; valid_until: string; reason?: string }) =>
      closeSupplierRuleValidity(id, { valid_until, reason }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["supplier-rules"] });
    },
  });

  const stationMap = useMemo(() => {
    const map = new Map<string, string>();
    stations?.items.forEach((s) => map.set(s.id, s.trade_name));
    return map;
  }, [stations]);

  const distributorMap = useMemo(() => {
    const map = new Map<string, string>();
    distributors?.items.forEach((d) => map.set(d.id, d.trade_name));
    return map;
  }, [distributors]);

  const productMap = useMemo(() => {
    const map = new Map<string, string>();
    products?.items.forEach((p) => map.set(p.id, p.name));
    return map;
  }, [products]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / filters.page_size)) : 1;

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <h1 className="text-xl font-semibold">Regras de fornecimento</h1>
        <p className="text-sm text-slate-500">
          Defina quais distribuidores podem abastecer cada posto e produto, com volumes mínimos.
        </p>

        <EffectiveRuleSimulator />

        <div className="mt-6 grid gap-3 md:grid-cols-4">
          <div>
            <label className="text-xs text-slate-500">Distribuidor</label>
            <select
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={filters.distributor_id ?? ""}
              onChange={(e) => updateFilter("distributor_id", e.target.value)}
            >
              <option value="">Todos</option>
              {distributors?.items.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.trade_name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500">Produto</label>
            <select
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={filters.product_id ?? ""}
              onChange={(e) => updateFilter("product_id", e.target.value)}
            >
              <option value="">Todos</option>
              {products?.items.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500">Permitido</label>
            <select
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={filters.allowed === undefined ? "" : filters.allowed ? "true" : "false"}
              onChange={(e) => updateFilter("allowed", e.target.value)}
            >
              <option value="">Todos</option>
              <option value="true">Sim</option>
              <option value="false">Não</option>
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
              <option value="true">Ativas</option>
              <option value="false">Inativas</option>
            </select>
          </div>
        </div>

        {canWrite && (
          <form
            className="mt-6 grid gap-4 rounded border border-slate-200 p-4 md:grid-cols-3"
            onSubmit={form.handleSubmit((v) => saveMutation.mutate(v))}
          >
            <h2 className="md:col-span-3 text-sm font-semibold">Nova regra</h2>
            <div>
              <label className="text-sm font-medium">Posto</label>
              <select className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("station_id")}>
                <option value="">Selecione...</option>
                {stations?.items.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.trade_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Distribuidor</label>
              <select
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                {...form.register("distributor_id")}
              >
                <option value="">Selecione...</option>
                {distributors?.items.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.trade_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Produto (opcional)</label>
              <select className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("product_id")}>
                <option value="">Geral (todos)</option>
                {products?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Volume mínimo (L)</label>
              <input
                type="number"
                className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
                {...form.register("minimum_volume_liters")}
              />
            </div>
            <div>
              <label className="text-sm font-medium">Válido de</label>
              <input type="date" className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("valid_from")} />
            </div>
            <div>
              <label className="text-sm font-medium">Válido até</label>
              <input type="date" className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("valid_until")} />
            </div>
            <div>
              <label className="text-sm font-medium">Prioridade</label>
              <input type="number" className="mt-1 w-full rounded border border-slate-300 px-3 py-2" {...form.register("priority")} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...form.register("allowed")} />
              Fornecimento permitido
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input type="checkbox" {...form.register("active")} />
              Ativa
            </label>
            <div className="md:col-span-3">
              <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
                Adicionar regra
              </button>
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
                    <th className="px-2 py-2">Posto</th>
                    <th className="px-2 py-2">Distribuidor</th>
                    <th className="px-2 py-2">Produto</th>
                    <th className="px-2 py-2">Permitido</th>
                    <th className="px-2 py-2">Vol. mín.</th>
                    <th className="px-2 py-2">Vigência</th>
                    <th className="px-2 py-2">Status</th>
                    {canWrite && <th className="px-2 py-2">Ações</th>}
                  </tr>
                </thead>
                <tbody>
                  {data?.items.map((rule) => (
                    <tr key={rule.id} className="border-b border-slate-100">
                      <td className="px-2 py-2">{stationMap.get(rule.station_id) ?? rule.station_id}</td>
                      <td className="px-2 py-2">{distributorMap.get(rule.distributor_id) ?? rule.distributor_id}</td>
                      <td className="px-2 py-2">
                        {rule.product_id ? productMap.get(rule.product_id) ?? rule.product_id : "Geral"}
                      </td>
                      <td className="px-2 py-2">{rule.allowed ? "Sim" : "Não"}</td>
                      <td className="px-2 py-2">{rule.minimum_volume_liters} L</td>
                      <td className="px-2 py-2">
                        {rule.valid_from}
                        {rule.valid_until ? ` → ${rule.valid_until}` : ""}
                      </td>
                      <td className="px-2 py-2">{rule.active ? "Ativa" : "Inativa"}</td>
                      {canWrite && (
                        <td className="px-2 py-2">
                          {rule.active && (
                            <>
                              <button
                                type="button"
                                className="mr-2 underline"
                                onClick={() => {
                                  const valid_until = window.prompt("Encerrar vigência em (AAAA-MM-DD):");
                                  if (valid_until) closeMutation.mutate({ id: rule.id, valid_until });
                                }}
                              >
                                Encerrar
                              </button>
                              <button
                                type="button"
                                className="text-red-700 underline"
                                onClick={() => {
                                  const reason = window.prompt("Motivo:");
                                  if (reason && reason.length >= 3) deactivateMutation.mutate({ id: rule.id, reason });
                                }}
                              >
                                Desativar
                              </button>
                            </>
                          )}
                        </td>
                      )}
                    </tr>
                  ))}
                  {!data?.items.length && (
                    <tr>
                      <td colSpan={canWrite ? 8 : 7} className="px-2 py-4 text-slate-500">
                        Nenhuma regra encontrada.
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
    </div>
  );
}
