import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  fetchErpProductHistory,
  fetchProducts,
  ignoreErpProduct,
  mapErpProduct,
  MAPPING_STATUS_LABELS,
  reopenErpProduct,
  type ErpProduct,
} from "../../api/master-data";
import { useAuth } from "../../auth/AuthProvider";

type MappingDrawerProps = {
  erpProduct: ErpProduct | null;
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
};

export function MappingDrawer({ erpProduct, open, onClose, onSuccess }: MappingDrawerProps) {
  const { hasPermission } = useAuth();
  const queryClient = useQueryClient();
  const canMap = hasPermission("erp_products.map");
  const canIgnore = hasPermission("erp_products.ignore");

  const [productId, setProductId] = useState("");
  const [reason, setReason] = useState("");
  const [ignoreReason, setIgnoreReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: products } = useQuery({
    queryKey: ["products", { active: true }],
    queryFn: () => fetchProducts({ active: true, page: 1, page_size: 100 }),
    enabled: open,
  });

  const { data: history } = useQuery({
    queryKey: ["erp-product-history", erpProduct?.id],
    queryFn: () => fetchErpProductHistory(erpProduct!.id),
    enabled: open && !!erpProduct?.id,
  });

  useEffect(() => {
    if (erpProduct) {
      setProductId(erpProduct.canonical_product_id ?? "");
      setReason("");
      setIgnoreReason("");
      setError(null);
    }
  }, [erpProduct]);

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["erp-products"] });
    onSuccess?.();
  };

  const mapMutation = useMutation({
    mutationFn: () =>
      mapErpProduct(erpProduct!.id, {
        canonical_product_id: productId,
        reason: reason || undefined,
      }),
    onSuccess: async () => {
      setError(null);
      await invalidate();
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  const ignoreMutation = useMutation({
    mutationFn: () => ignoreErpProduct(erpProduct!.id, ignoreReason),
    onSuccess: async () => {
      setError(null);
      await invalidate();
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  const reopenMutation = useMutation({
    mutationFn: () => reopenErpProduct(erpProduct!.id, reason || undefined),
    onSuccess: async () => {
      setError(null);
      await invalidate();
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!open || !erpProduct) return null;

  const statusLabel = MAPPING_STATUS_LABELS[erpProduct.mapping_status] ?? erpProduct.mapping_status;

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40"
        aria-label="Fechar painel"
        onClick={onClose}
      />
      <aside className="relative z-10 flex h-full w-full max-w-md flex-col overflow-y-auto bg-white shadow-xl">
        <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4">
          <div>
            <h2 className="text-lg font-semibold">Mapear produto ERP</h2>
            <p className="text-sm text-slate-500">{erpProduct.erp_description}</p>
          </div>
          <button type="button" className="text-sm underline" onClick={onClose}>
            Fechar
          </button>
        </div>

        <div className="space-y-4 px-6 py-4">
          {error && (
            <p className="rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
              {error}
            </p>
          )}

          <dl className="grid gap-2 text-sm">
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">ID ERP</dt>
              <dd className="font-mono text-xs">{erpProduct.erp_product_id}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Código</dt>
              <dd>{erpProduct.erp_product_code ?? "—"}</dd>
            </div>
            <div className="flex justify-between gap-4">
              <dt className="text-slate-500">Status</dt>
              <dd>{statusLabel}</dd>
            </div>
            {erpProduct.erp_group_name && (
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Grupo</dt>
                <dd>{erpProduct.erp_group_name}</dd>
              </div>
            )}
          </dl>

          {(erpProduct.mapping_status === "PENDING" || erpProduct.mapping_status === "CONFLICT") && canMap && (
            <section className="space-y-3 rounded border border-slate-200 p-4">
              <h3 className="text-sm font-semibold">Vincular produto canônico</h3>
              <select
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                value={productId}
                onChange={(e) => setProductId(e.target.value)}
              >
                <option value="">Selecione...</option>
                {products?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code})
                  </option>
                ))}
              </select>
              <input
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                placeholder="Motivo (opcional)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <button
                type="button"
                className="w-full rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
                disabled={!productId || mapMutation.isPending}
                onClick={() => mapMutation.mutate()}
              >
                {mapMutation.isPending ? "Salvando..." : "Confirmar mapeamento"}
              </button>
            </section>
          )}

          {erpProduct.mapping_status === "PENDING" && canIgnore && (
            <section className="space-y-3 rounded border border-slate-200 p-4">
              <h3 className="text-sm font-semibold">Ignorar produto</h3>
              <textarea
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                rows={3}
                placeholder="Motivo (mín. 3 caracteres)"
                value={ignoreReason}
                onChange={(e) => setIgnoreReason(e.target.value)}
              />
              <button
                type="button"
                className="w-full rounded border border-slate-300 px-4 py-2 text-sm disabled:opacity-60"
                disabled={ignoreReason.length < 3 || ignoreMutation.isPending}
                onClick={() => ignoreMutation.mutate()}
              >
                {ignoreMutation.isPending ? "Salvando..." : "Ignorar"}
              </button>
            </section>
          )}

          {(erpProduct.mapping_status === "IGNORED" || erpProduct.mapping_status === "MAPPED") && canMap && (
            <section className="space-y-3 rounded border border-slate-200 p-4">
              <h3 className="text-sm font-semibold">Reabrir para mapeamento</h3>
              <input
                className="w-full rounded border border-slate-300 px-3 py-2 text-sm"
                placeholder="Motivo (opcional)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
              />
              <button
                type="button"
                className="w-full rounded border border-slate-300 px-4 py-2 text-sm disabled:opacity-60"
                disabled={reopenMutation.isPending}
                onClick={() => reopenMutation.mutate()}
              >
                {reopenMutation.isPending ? "Salvando..." : "Reabrir"}
              </button>
            </section>
          )}

          {history && history.items.length > 0 && (
            <section>
              <h3 className="text-sm font-semibold">Histórico</h3>
              <ul className="mt-2 space-y-2 text-sm">
                {history.items.map((item) => (
                  <li key={item.id} className="rounded bg-slate-50 px-3 py-2">
                    <p>
                      {MAPPING_STATUS_LABELS[item.previous_status ?? ""] ?? item.previous_status ?? "—"} →{" "}
                      {MAPPING_STATUS_LABELS[item.new_status] ?? item.new_status}
                    </p>
                    <p className="text-xs text-slate-500">{new Date(item.created_at).toLocaleString("pt-BR")}</p>
                    {item.reason && <p className="text-xs text-slate-600">{item.reason}</p>}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </aside>
    </div>
  );
}
