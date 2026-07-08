import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { createOrganization, fetchOrganization, updateOrganization } from "../api/organizations";
import { useAuth } from "../auth/AuthProvider";

function formatCnpj(value: string) {
  const digits = value.replace(/\D/g, "").slice(0, 14);
  return digits
    .replace(/^(\d{2})(\d)/, "$1.$2")
    .replace(/^(\d{2})\.(\d{3})(\d)/, "$1.$2.$3")
    .replace(/\.(\d{3})(\d)/, ".$1/$2")
    .replace(/(\d{4})(\d)/, "$1-$2");
}

export function OrganizationPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("organizations.write");
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["organization"], queryFn: fetchOrganization, retry: false });
  const [form, setForm] = useState({
    name: "",
    corporate_name: "",
    cnpj: "",
    timezone: "America/Cuiaba",
    active: true,
  });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (data) {
      setForm({
        name: data.name,
        corporate_name: data.corporate_name,
        cnpj: formatCnpj(data.cnpj),
        timezone: data.timezone,
        active: data.active,
      });
    }
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = { ...form, cnpj: form.cnpj.replace(/\D/g, "") };
      if (data) return updateOrganization(data.id, payload);
      return createOrganization(payload);
    },
    onSuccess: async () => {
      setMessage("Organização salva com sucesso.");
      await queryClient.invalidateQueries({ queryKey: ["organization"] });
    },
  });

  if (isLoading) return <p>Carregando organização...</p>;

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">Organização</h1>
      <p className="mt-1 text-sm text-slate-500">Dados cadastrais da organização.</p>
      {message && <p className="mt-4 text-sm text-green-700">{message}</p>}
      <form
        className="mt-6 grid gap-4 md:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          saveMutation.mutate();
        }}
      >
        <div>
          <label className="text-sm font-medium" htmlFor="org-name">
            Nome
          </label>
          <input
            id="org-name"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.name}
            disabled={!canWrite}
            onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="org-corporate">
            Razão social
          </label>
          <input
            id="org-corporate"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.corporate_name}
            disabled={!canWrite}
            onChange={(e) => setForm((f) => ({ ...f, corporate_name: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="org-cnpj">
            CNPJ
          </label>
          <input
            id="org-cnpj"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.cnpj}
            disabled={!canWrite}
            onChange={(e) => setForm((f) => ({ ...f, cnpj: formatCnpj(e.target.value) }))}
          />
        </div>
        <div>
          <label className="text-sm font-medium" htmlFor="org-timezone">
            Timezone
          </label>
          <input
            id="org-timezone"
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.timezone}
            disabled={!canWrite}
            onChange={(e) => setForm((f) => ({ ...f, timezone: e.target.value }))}
          />
        </div>
        {canWrite && (
          <div className="md:col-span-2">
            <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-white" disabled={saveMutation.isPending}>
              Salvar
            </button>
          </div>
        )}
      </form>
    </div>
  );
}
