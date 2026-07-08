import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchStations } from "../api/stations";
import { useAuth } from "../auth/AuthProvider";

export function StationsPage() {
  const { hasPermission } = useAuth();
  const canWrite = hasPermission("stations.write");
  const { data, isLoading } = useQuery({
    queryKey: ["stations"],
    queryFn: () => fetchStations({ page: 1, page_size: 50 }),
  });

  return (
    <div className="rounded-lg border border-slate-200 bg-white p-6">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Postos</h1>
          <p className="text-sm text-slate-500">Cadastro e gestão dos postos autorizados.</p>
        </div>
        {canWrite && (
          <Link to="/stations/new" className="rounded bg-slate-900 px-4 py-2 text-sm text-white">
            Novo posto
          </Link>
        )}
      </div>

      {isLoading ? (
        <p className="mt-6">Carregando...</p>
      ) : (
        <div className="mt-6 overflow-x-auto">
          <table className="min-w-full text-left text-sm">
            <thead className="border-b border-slate-200 text-slate-500">
              <tr>
                <th className="px-2 py-2">Posto</th>
                <th className="px-2 py-2">Tipo</th>
                <th className="px-2 py-2">CNPJ</th>
                <th className="px-2 py-2">Bandeira</th>
                <th className="px-2 py-2">Status</th>
                {canWrite && <th className="px-2 py-2">Ações</th>}
              </tr>
            </thead>
            <tbody>
              {data?.items.map((station) => (
                <tr key={station.id} className="border-b border-slate-100">
                  <td className="px-2 py-2">{station.trade_name}</td>
                  <td className="px-2 py-2">{station.station_type}</td>
                  <td className="px-2 py-2">{station.cnpj}</td>
                  <td className="px-2 py-2">{station.brand_name ?? station.brand_type}</td>
                  <td className="px-2 py-2">{station.active ? "Ativo" : "Inativo"}</td>
                  {canWrite && (
                    <td className="px-2 py-2">
                      <Link to={`/stations/${station.id}`} className="text-slate-900 underline">
                        Editar
                      </Link>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
