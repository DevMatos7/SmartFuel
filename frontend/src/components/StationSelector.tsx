import { useEffect, useMemo, useState } from "react";
import { useAuth } from "../auth/AuthProvider";

const STORAGE_KEY = "active_station_id";

export function StationSelector() {
  const { user } = useAuth();
  const stations = useMemo(() => user?.stations.filter((s) => s.active) ?? [], [user]);
  const [activeId, setActiveId] = useState<string>("");

  useEffect(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    const valid = stations.some((s) => s.id === saved);
    const next = valid ? saved! : stations[0]?.id ?? "";
    setActiveId(next);
    if (next) localStorage.setItem(STORAGE_KEY, next);
    else localStorage.removeItem(STORAGE_KEY);
  }, [stations]);

  if (!stations.length) {
    return <span className="text-xs text-slate-500">Sem postos</span>;
  }

  return (
    <label className="text-sm">
      <span className="mr-2 text-xs text-slate-500">Posto ativo</span>
      <select
        className="rounded border border-slate-300 bg-white px-2 py-1 text-sm"
        value={activeId}
        onChange={(e) => {
          setActiveId(e.target.value);
          localStorage.setItem(STORAGE_KEY, e.target.value);
        }}
        aria-label="Selecionar posto ativo"
      >
        {stations.length > 1 && <option value="">Todos os postos</option>}
        {stations.map((station) => (
          <option key={station.id} value={station.id}>
            {station.station_type === "HEADQUARTERS" ? "Matriz — " : ""}
            {station.trade_name}
          </option>
        ))}
      </select>
    </label>
  );
}
