import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  addPricingEvidence,
  approvePricingDecision,
  confirmImplementation,
  fetchPricingDecisions,
  rejectPricingDecision,
} from "../api/pricing";
import { useAuth } from "../auth/AuthProvider";

export function PricingDecisionDetailsPage() {
  const { id = "" } = useParams();
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["pricing-decisions"],
    queryFn: () => fetchPricingDecisions(),
  });
  const d = (q.data ?? []).find((x) => x.id === id);

  const approveM = useMutation({
    mutationFn: () => approvePricingDecision(id, "Aprovado no detalhe"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pricing-decisions"] }),
  });
  const rejectM = useMutation({
    mutationFn: () => rejectPricingDecision(id, "Rejeitado no detalhe"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pricing-decisions"] }),
  });
  const evidenceM = useMutation({
    mutationFn: () => addPricingEvidence(id, "Evidência textual de homologação"),
  });
  const implM = useMutation({
    mutationFn: () => confirmImplementation(id, d?.approved_price ?? d?.recommended_price ?? "0", "Confirmação manual"),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pricing-decisions"] }),
  });

  return (
    <div className="space-y-4">
      <Link className="text-sm underline" to="/pricing/approvals">
        ← Aprovações
      </Link>
      <h1 className="text-xl font-semibold">Decisão</h1>
      {!d && !q.isLoading ? <p className="text-sm text-slate-500">Decisão não encontrada na lista recente.</p> : null}
      {d ? (
        <>
          <dl className="grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-slate-500">Status</dt>
              <dd>{d.status}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Recomendado</dt>
              <dd>{d.recommended_price}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Aprovado</dt>
              <dd>{d.approved_price ?? "—"}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Motivo</dt>
              <dd>{d.decision_reason ?? "—"}</dd>
            </div>
          </dl>
          <p className="text-xs text-slate-500">Sem escrita no XPERT. Implementação é externa e comprovada depois.</p>
          <div className="flex flex-wrap gap-2">
            {hasPermission("pricing.approve") && d.status === "PENDING_APPROVAL" ? (
              <>
                <button type="button" className="rounded bg-emerald-700 px-3 py-1 text-sm text-white" onClick={() => approveM.mutate()}>
                  Aprovar
                </button>
                <button type="button" className="rounded bg-red-700 px-3 py-1 text-sm text-white" onClick={() => rejectM.mutate()}>
                  Rejeitar
                </button>
              </>
            ) : null}
            {hasPermission("pricing.add_evidence") ? (
              <button type="button" className="rounded border px-3 py-1 text-sm" onClick={() => evidenceM.mutate()}>
                Anexar evidência (nota)
              </button>
            ) : null}
            {hasPermission("pricing.confirm_implementation") &&
            d.status === "APPROVED_PENDING_IMPLEMENTATION" ? (
              <button type="button" className="rounded bg-slate-900 px-3 py-1 text-sm text-white" onClick={() => implM.mutate()}>
                Confirmar implantação
              </button>
            ) : null}
          </div>
        </>
      ) : null}
    </div>
  );
}
