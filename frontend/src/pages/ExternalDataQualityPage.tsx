import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { fetchQualityIssues } from "../api/external-indices";

export function ExternalDataQualityPage() {
  const q = useQuery({ queryKey: ["external-quality"], queryFn: fetchQualityIssues });

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-semibold">Qualidade — índices externos</h1>
        <p className="text-sm text-slate-600">Outliers são sinalizados e preservados; não são excluídos automaticamente.</p>
      </div>
      <Link className="text-sm underline" to="/analytics/external-indices">
        Voltar
      </Link>
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b text-slate-500">
            <th className="py-2">Código</th>
            <th>Severidade</th>
            <th>Status</th>
            <th>Detalhes</th>
            <th>Criado</th>
          </tr>
        </thead>
        <tbody>
          {(q.data ?? []).map((i) => (
            <tr key={i.id} className="border-b border-slate-100">
              <td className="py-2 font-mono text-xs">{i.issue_code}</td>
              <td>{i.severity}</td>
              <td>{i.resolution_status}</td>
              <td className="max-w-md truncate font-mono text-xs">{JSON.stringify(i.details)}</td>
              <td>{i.created_at}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {!q.isLoading && (q.data?.length ?? 0) === 0 ? (
        <p className="text-sm text-slate-600">Nenhum issue aberto.</p>
      ) : null}
    </div>
  );
}
