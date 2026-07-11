import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchOperationsSlo } from "../api/executive";

export function OperationalSloPage() {
  const q = useQuery({ queryKey: ["ops-slo"], queryFn: fetchOperationsSlo });
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive">
        ← Visão executiva
      </Link>
      <h1 className="text-xl font-semibold">SLOs operacionais</h1>
      <p className="text-sm text-slate-600">Conformidade não é inventada sem medição.</p>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      <ul className="space-y-2 text-sm">
        {(q.data ?? []).map((r, idx) => (
          <li key={`${r.indicator_code}-${idx}`} className="rounded border p-3">
            {String(r.service_name)} · {String(r.indicator_code)} · alvo {String(r.target_value)} ·{" "}
            {String(r.status)} · observado {String(r.observed_value ?? "—")}
          </li>
        ))}
      </ul>
    </div>
  );
}
