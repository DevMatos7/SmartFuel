import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createStation, fetchStations, updateStation } from "../api/stations";
import { fetchOrganization } from "../api/organizations";

export function StationFormPage() {
  const { stationId } = useParams();
  const isNew = !stationId || stationId === "new";
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: org } = useQuery({ queryKey: ["organization"], queryFn: fetchOrganization });
  const { data: stations } = useQuery({
    queryKey: ["stations"],
    queryFn: () => fetchStations({ page: 1, page_size: 100 }),
    enabled: !isNew,
  });

  const [form, setForm] = useState({
    station_type: "BRANCH",
    corporate_name: "",
    trade_name: "",
    cnpj: "",
    erp_branch_id: "",
    anp_code: "",
    brand_type: "WHITE_LABEL",
    brand_name: "",
    timezone: "America/Cuiaba",
    active: true,
  });

  useEffect(() => {
    if (!isNew && stations?.items.length) {
      const station = stations.items.find((s) => s.id === stationId);
      if (station) {
        setForm({
          station_type: station.station_type,
          corporate_name: station.corporate_name,
          trade_name: station.trade_name,
          cnpj: station.cnpj,
          erp_branch_id: station.erp_branch_id ?? "",
          anp_code: station.anp_code ?? "",
          brand_type: station.brand_type,
          brand_name: station.brand_name ?? "",
          timezone: station.timezone,
          active: station.active,
        });
      }
    }
  }, [isNew, stationId, stations]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        ...form,
        cnpj: form.cnpj.replace(/\D/g, ""),
        erp_branch_id: form.erp_branch_id || null,
        anp_code: form.anp_code || null,
        brand_name: form.brand_name || null,
        organization_id: org?.id,
      };
      if (isNew) return createStation(payload);
      return updateStation(stationId!, payload);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["stations"] });
      navigate("/stations");
    },
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <h1 className="text-xl font-semibold">{isNew ? "Novo posto" : "Editar posto"}</h1>
      <form
        className="mt-6 grid gap-4 md:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          saveMutation.mutate();
        }}
      >
        <div>
          <label className="text-sm font-medium">Tipo</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.station_type}
            onChange={(e) => setForm((f) => ({ ...f, station_type: e.target.value }))}
          >
            <option value="HEADQUARTERS">Matriz</option>
            <option value="BRANCH">Filial</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Razão social</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.corporate_name}
            onChange={(e) => setForm((f) => ({ ...f, corporate_name: e.target.value }))}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium">Nome fantasia</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.trade_name}
            onChange={(e) => setForm((f) => ({ ...f, trade_name: e.target.value }))}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium">CNPJ</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.cnpj}
            onChange={(e) => setForm((f) => ({ ...f, cnpj: e.target.value }))}
            required
          />
        </div>
        <div>
          <label className="text-sm font-medium">Código ERP</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.erp_branch_id}
            onChange={(e) => setForm((f) => ({ ...f, erp_branch_id: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-sm font-medium">Código ANP</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.anp_code}
            onChange={(e) => setForm((f) => ({ ...f, anp_code: e.target.value }))}
          />
        </div>
        <div>
          <label className="text-sm font-medium">Tipo de bandeira</label>
          <select
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.brand_type}
            onChange={(e) => setForm((f) => ({ ...f, brand_type: e.target.value }))}
          >
            <option value="WHITE_LABEL">Bandeira branca</option>
            <option value="BRANDED">Bandeirado</option>
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Nome da bandeira</label>
          <input
            className="mt-1 w-full rounded border border-slate-300 px-3 py-2"
            value={form.brand_name}
            onChange={(e) => setForm((f) => ({ ...f, brand_name: e.target.value }))}
          />
        </div>
        <div className="md:col-span-2">
          <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-white" disabled={saveMutation.isPending}>
            Salvar
          </button>
        </div>
      </form>
    </div>
  );
}
