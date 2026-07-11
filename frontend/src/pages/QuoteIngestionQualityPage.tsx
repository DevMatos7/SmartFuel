import { useMutation } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchQuoteAiAnalyticsSummary, runQuoteAiEvaluation } from "../api/quote-ingestion";
import { useAuth } from "../auth/AuthProvider";
import { useQuery } from "@tanstack/react-query";

export function QuoteIngestionQualityPage() {
  const { hasPermission } = useAuth();
  const summaryQ = useQuery({ queryKey: ["quote-ai-summary"], queryFn: fetchQuoteAiAnalyticsSummary });
  const evalM = useMutation({ mutationFn: runQuoteAiEvaluation });

  return (
    <div className="space-y-4">
      <div>
        <Link className="text-sm underline" to="/quotes/ai">
          ← Importar com IA
        </Link>
        <h1 className="text-xl font-semibold">Qualidade da extração</h1>
        <p className="text-sm text-slate-600">Metas de homologação · revisão humana permanece obrigatória</p>
      </div>
      <pre className="rounded bg-slate-50 p-3 text-xs">{JSON.stringify(summaryQ.data ?? {}, null, 2)}</pre>
      {hasPermission("quote_ingestion.run_evaluation") ? (
        <button
          type="button"
          className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
          onClick={() => evalM.mutate()}
        >
          Rodar avaliação sintética
        </button>
      ) : null}
      {evalM.data ? (
        <p className="text-sm">
          Run {evalM.data.id}: {evalM.data.passed_count}/{evalM.data.case_count} ok
        </p>
      ) : null}
    </div>
  );
}
