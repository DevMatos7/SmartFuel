import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchExecutiveByStation } from "../api/executive";

export function ExecutiveStationDetailsPage() {
  const q = useQuery({ queryKey: ["executive-stations"], queryFn: fetchExecutiveByStation });
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive">
        ← Visão executiva
      </Link>
      <h1 className="text-xl font-semibold">Indicadores por posto</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !(q.data?.length) ? <p className="text-sm text-slate-500">Sem dados por posto.</p> : null}
      <table className="min-w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Posto</th>
            <th className="py-2">Margem/L</th>
            <th className="py-2">Qualidade</th>
            <th className="py-2">Freshness</th>
            <th className="py-2">Cobertura</th>
          </tr>
        </thead>
        <tbody>
          {(q.data ?? []).map((r) => (
            <tr key={String(r.station_id)} className="border-b border-slate-100">
              <td className="py-2 font-mono text-xs">{String(r.station_id).slice(0, 8)}</td>
              <td className="py-2">{(r.margin_per_liter as string) ?? "NO_DATA"}</td>
              <td className="py-2">{String(r.quality_status)}</td>
              <td className="py-2">{String(r.freshness_status)}</td>
              <td className="py-2">{(r.coverage_percentage as string) ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
