import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchExecutiveSummary } from "../api/executive";
import { apiFetch } from "../api/client";

export function DataQualityOverviewPage() {
  const summaryQ = useQuery({ queryKey: ["executive-summary"], queryFn: fetchExecutiveSummary });
  const dq = useQuery({
    queryKey: ["executive-dq"],
    queryFn: () => apiFetch<{ by_quality_status: Record<string, number>; total: number }>("/executive/data-quality"),
  });
  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/executive">
        ← Visão executiva
      </Link>
      <h1 className="text-xl font-semibold">Qualidade dos dados (executivo)</h1>
      <p className="text-sm">Total snapshots: {dq.data?.total ?? 0}</p>
      <ul className="text-sm">
        {Object.entries(dq.data?.by_quality_status ?? {}).map(([k, v]) => (
          <li key={k}>
            {k}: {v}
          </li>
        ))}
      </ul>
      <h2 className="text-sm font-semibold">Cards com empty_reason</h2>
      <ul className="text-sm">
        {(summaryQ.data?.cards ?? [])
          .filter((c) => !c.value)
          .map((c) => (
            <li key={c.metric_code}>
              {c.metric_code}: {c.empty_reason ?? c.quality_status}
            </li>
          ))}
      </ul>
    </div>
  );
}
