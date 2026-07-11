import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { approvePricingDecision, fetchPricingDecisions, rejectPricingDecision } from "../api/pricing";
import { useAuth } from "../auth/AuthProvider";

export function PricingApprovalQueuePage() {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["pricing-decisions", "PENDING_APPROVAL"],
    queryFn: () => fetchPricingDecisions("PENDING_APPROVAL"),
  });
  const approveM = useMutation({
    mutationFn: (id: string) => approvePricingDecision(id, "Aprovado na fila"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pricing-decisions"] }),
  });
  const rejectM = useMutation({
    mutationFn: (id: string) => rejectPricingDecision(id, "Rejeitado na fila"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pricing-decisions"] }),
  });

  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/pricing">
        ← Precificação
      </Link>
      <h1 className="text-xl font-semibold">Fila de aprovações</h1>
      {q.isLoading ? <p className="text-sm">Carregando…</p> : null}
      {!q.isLoading && !(q.data?.length) ? <p className="text-sm text-slate-500">Fila vazia.</p> : null}
      <ul className="space-y-3 text-sm">
        {(q.data ?? []).map((d) => (
          <li key={d.id} className="rounded border border-slate-200 bg-white p-3">
            <Link className="underline" to={`/pricing/decisions/${d.id}`}>
              {d.status}
            </Link>
            <div>Preço recomendado: {d.recommended_price}</div>
            {hasPermission("pricing.approve") ? (
              <div className="mt-2 flex gap-2">
                <button
                  type="button"
                  className="rounded bg-emerald-700 px-2 py-1 text-white"
                  onClick={() => approveM.mutate(d.id)}
                >
                  Aprovar
                </button>
                <button
                  type="button"
                  className="rounded bg-red-700 px-2 py-1 text-white"
                  onClick={() => rejectM.mutate(d.id)}
                >
                  Rejeitar
                </button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </div>
  );
}
