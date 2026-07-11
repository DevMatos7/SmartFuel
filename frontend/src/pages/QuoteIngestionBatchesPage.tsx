import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { listIngestionBatches } from "../api/quote-ingestion";

export function QuoteIngestionBatchesPage() {
  const q = useQuery({ queryKey: ["quote-ingestion-batches"], queryFn: listIngestionBatches });
  return (
    <div className="space-y-4">
      <div>
        <Link className="text-sm underline" to="/quotes/ai">
          ← Importar com IA
        </Link>
        <h1 className="text-xl font-semibold">Lotes de ingestão</h1>
      </div>
      <ul className="divide-y rounded border">
        {(q.data?.items ?? []).map((b) => (
          <li key={b.id} className="px-3 py-2 text-sm">
            {b.id.slice(0, 8)}… · {b.status} · {b.total_documents} documento(s)
          </li>
        ))}
        {!q.isLoading && (q.data?.items ?? []).length === 0 ? (
          <li className="px-3 py-4 text-sm text-slate-500">Nenhum lote.</li>
        ) : null}
      </ul>
    </div>
  );
}
