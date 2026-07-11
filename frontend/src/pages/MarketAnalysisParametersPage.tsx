import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchMarketParameters } from "../api/market-correlation";
import { useAuth } from "../auth/AuthProvider";

export function MarketAnalysisParametersPage() {
  const { hasPermission } = useAuth();
  const canManage = hasPermission("market_analysis.manage_parameters");
  const q = useQuery({ queryKey: ["market-params"], queryFn: fetchMarketParameters });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Parâmetros de análise de mercado</h1>
        <p className="text-sm text-slate-600">
          Amostra mínima, lags e limiar de variação de referência. Vigência versionada.
        </p>
      </div>
      <Link className="text-sm underline" to="/analytics/market-correlation">
        Voltar
      </Link>
      {!canManage ? (
        <p className="text-sm text-slate-600">Somente ADMIN altera parâmetros; visualização liberada.</p>
      ) : null}
      <pre className="overflow-auto rounded bg-slate-50 p-3 text-xs">
        {JSON.stringify(q.data ?? {}, null, 2)}
      </pre>
    </div>
  );
}
