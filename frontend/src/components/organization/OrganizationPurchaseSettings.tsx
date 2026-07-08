import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import {
  fetchOrganizationBusinessSettings,
  updateOrganizationBusinessSettings,
} from "../../api/organization-settings";
import { useAuth } from "../../auth/AuthProvider";

export function OrganizationPurchaseSettings() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("organizations.write");
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["organization-business-settings"],
    queryFn: fetchOrganizationBusinessSettings,
  });

  const [form, setForm] = useState({
    default_supplier_allowed: false,
    default_minimum_volume_liters: 5000,
  });
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setForm({
        default_supplier_allowed: data.default_supplier_allowed,
        default_minimum_volume_liters: Number(data.default_minimum_volume_liters),
      });
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: () => updateOrganizationBusinessSettings(form),
    onSuccess: async () => {
      setMessage("Política de compra salva com sucesso.");
      setError(null);
      await queryClient.invalidateQueries({ queryKey: ["organization-business-settings"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  if (isLoading) return <p>Carregando política de compra...</p>;

  return (
    <section className="mt-8 border-t border-slate-200 pt-6">
      <h2 className="text-lg font-semibold">Política de compra</h2>
      <p className="mt-1 text-sm text-slate-500">
        Regras padrão de fornecimento quando não houver regra específica.
      </p>

      {message && <p className="mt-4 text-sm text-green-700">{message}</p>}
      {error && (
        <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
          {error}
        </p>
      )}

      <form
        className="mt-6 grid gap-4 md:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          saveMutation.mutate();
        }}
      >
        <label className="flex items-center gap-2 text-sm md:col-span-2">
          <input
            type="checkbox"
            checked={form.default_supplier_allowed}
            disabled={!canWrite}
            onChange={(e) => setForm((f) => ({ ...f, default_supplier_allowed: e.target.checked }))}
          />
          Fornecimento permitido por padrão
        </label>
        <div>
          <label className="text-sm font-medium" htmlFor="default-min-volume">
            Volume mínimo padrão (L)
          </label>
          <input
            id="default-min-volume"
            type="number"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.default_minimum_volume_liters}
            disabled={!canWrite}
            onChange={(e) =>
              setForm((f) => ({ ...f, default_minimum_volume_liters: Number(e.target.value) }))
            }
          />
        </div>
        {canWrite && (
          <div className="md:col-span-2">
            <button
              type="submit"
              className="rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-60"
              disabled={saveMutation.isPending}
            >
              {saveMutation.isPending ? "Salvando..." : "Salvar política"}
            </button>
          </div>
        )}
      </form>
    </section>
  );
}
