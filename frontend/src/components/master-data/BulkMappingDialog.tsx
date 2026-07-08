import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { bulkMapErpProducts, fetchProducts } from "../../api/master-data";

type BulkMappingDialogProps = {
  open: boolean;
  selectedIds: string[];
  onClose: () => void;
  onSuccess?: () => void;
};

export function BulkMappingDialog({ open, selectedIds, onClose, onSuccess }: BulkMappingDialogProps) {
  const queryClient = useQueryClient();
  const [productId, setProductId] = useState("");
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [failures, setFailures] = useState<{ erp_product_id: string; message: string }[]>([]);

  const { data: products } = useQuery({
    queryKey: ["products", { active: true }],
    queryFn: () => fetchProducts({ active: true, page: 1, page_size: 100 }),
    enabled: open,
  });

  const mutation = useMutation({
    mutationFn: () =>
      bulkMapErpProducts({
        erp_product_ids: selectedIds,
        canonical_product_id: productId,
        reason: reason || undefined,
      }),
    onSuccess: async (result) => {
      setError(null);
      setFailures(result.failures.map((f) => ({ erp_product_id: f.erp_product_id, message: f.message })));
      await queryClient.invalidateQueries({ queryKey: ["erp-products"] });
      if (result.failures.length === 0) {
        onSuccess?.();
        onClose();
        setProductId("");
        setReason("");
        setFailures([]);
      }
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40"
        aria-label="Fechar diálogo"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Mapeamento em lote</h2>
        <p className="mt-1 text-sm text-slate-500">
          {selectedIds.length} produto(s) ERP selecionado(s)
        </p>

        {error && (
          <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <div className="mt-4 space-y-3">
          <div>
            <label className="text-sm font-medium" htmlFor="bulk-product">
              Produto canônico
            </label>
            <select
              id="bulk-product"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
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
          </div>
          <div>
            <label className="text-sm font-medium" htmlFor="bulk-reason">
              Motivo (opcional)
            </label>
            <input
              id="bulk-reason"
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
            />
          </div>
        </div>

        {failures.length > 0 && (
          <div className="mt-4 rounded bg-amber-50 px-3 py-2 text-sm text-amber-900">
            <p className="font-medium">{failures.length} falha(s):</p>
            <ul className="mt-1 max-h-32 overflow-y-auto text-xs">
              {failures.map((f) => (
                <li key={f.erp_product_id}>
                  {f.erp_product_id}: {f.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            className="rounded border border-slate-300 px-4 py-2 text-sm"
            onClick={onClose}
          >
            Cancelar
          </button>
          <button
            type="button"
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
            disabled={!productId || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Mapeando..." : "Confirmar"}
          </button>
        </div>
      </div>
    </div>
  );
}
