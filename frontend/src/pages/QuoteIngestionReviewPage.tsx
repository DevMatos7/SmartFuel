import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import {
  approveIngestion,
  createDraftFromIngestion,
  fetchIngestionDocument,
  rejectIngestion,
  saveIngestionReview,
  startIngestionReview,
} from "../api/quote-ingestion";
import { useAuth } from "../auth/AuthProvider";

function confidenceBand(value: string | null | undefined) {
  if (!value) return "indisponível";
  const n = Number(value);
  if (Number.isNaN(n)) return value;
  if (n >= 0.9) return `alta (${value})`;
  if (n >= 0.7) return `média (${value})`;
  return `baixa (${value})`;
}

export function QuoteIngestionReviewPage() {
  const { documentId = "" } = useParams();
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ["quote-ingestion-doc", documentId],
    queryFn: () => fetchIngestionDocument(documentId),
    enabled: Boolean(documentId),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["quote-ingestion-doc", documentId] });
  const startM = useMutation({ mutationFn: () => startIngestionReview(documentId), onSuccess: invalidate });
  const saveM = useMutation({
    mutationFn: () => saveIngestionReview(documentId, { reviewed: true }, "correção manual registrada"),
    onSuccess: invalidate,
  });
  const approveM = useMutation({
    mutationFn: () => approveIngestion(documentId, true),
    onSuccess: invalidate,
  });
  const rejectM = useMutation({
    mutationFn: () => rejectIngestion(documentId, "rejeitado na revisão"),
    onSuccess: invalidate,
  });
  const draftM = useMutation({
    mutationFn: () => createDraftFromIngestion(documentId, {}),
    onSuccess: invalidate,
  });

  const data = q.data;

  return (
    <div className="space-y-4">
      <div>
        <Link className="text-sm underline" to="/quotes/ai">
          ← Importar com IA
        </Link>
        <h1 className="text-xl font-semibold">Revisão de extração</h1>
        <p className="text-sm text-slate-600">
          Evidência + campos sugeridos. Nenhuma cotação é ativada nesta tela.
        </p>
      </div>

      {q.isLoading ? <p>Carregando…</p> : null}
      {q.isError ? <p className="text-red-700">{(q.error as Error).message}</p> : null}

      {data ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <section className="rounded border p-3">
            <h2 className="mb-2 font-medium">Evidência original</h2>
            <p className="mb-2 text-xs text-slate-500">
              status {data.document.status} · tipo {data.document.document_type} · hash{" "}
              {data.document.sha256.slice(0, 12)}…
            </p>
            <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs">
              {data.document.raw_text || "(sem texto extraído — OCR/planilha pode estar pendente)"}
            </pre>
          </section>

          <section className="space-y-3 rounded border p-3">
            <h2 className="font-medium">Campos extraídos</h2>
            <p className="text-sm">
              Confiança do documento:{" "}
              <strong>{confidenceBand(data.extraction?.document_confidence)}</strong>
              {" · "}
              provedor {data.extraction?.provider}/{data.extraction?.model}
            </p>
            {(data.extraction?.warnings ?? []).length ? (
              <ul className="list-disc pl-5 text-sm text-amber-800">
                {data.extraction!.warnings.map((w) => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            ) : null}

            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b text-xs uppercase text-slate-500">
                  <th className="py-1">Campo</th>
                  <th>Valor</th>
                  <th>Confiança</th>
                  <th>Origem</th>
                </tr>
              </thead>
              <tbody>
                {data.fields.map((f) => (
                  <tr key={f.field_path} className="border-b align-top">
                    <td className="py-1 font-mono text-xs">{f.field_path}</td>
                    <td>{f.raw_value}</td>
                    <td>{confidenceBand(f.confidence)}</td>
                    <td>{f.value_origin}</td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div>
              <h3 className="mb-1 text-sm font-medium">Entidades</h3>
              <ul className="space-y-1 text-sm">
                {data.matches.map((m) => (
                  <li key={`${m.entity_type}-${m.raw_value}`}>
                    {m.entity_type}: {m.raw_value} → <strong>{m.status}</strong>
                    {m.matched_entity_id ? ` (${m.matched_entity_id.slice(0, 8)}…)` : " (sem criação automática)"}
                  </li>
                ))}
              </ul>
            </div>

            <div className="flex flex-wrap gap-2">
              {hasPermission("quote_ingestion.review") ? (
                <>
                  <button type="button" className="rounded border px-3 py-1 text-sm" onClick={() => startM.mutate()}>
                    Iniciar revisão
                  </button>
                  <button type="button" className="rounded border px-3 py-1 text-sm" onClick={() => saveM.mutate()}>
                    Salvar correções
                  </button>
                </>
              ) : null}
              {hasPermission("quote_ingestion.approve") ? (
                <>
                  <button
                    type="button"
                    className="rounded bg-emerald-700 px-3 py-1 text-sm text-white"
                    onClick={() => approveM.mutate()}
                  >
                    Aprovar
                  </button>
                  <button
                    type="button"
                    className="rounded bg-red-700 px-3 py-1 text-sm text-white"
                    onClick={() => rejectM.mutate()}
                  >
                    Rejeitar
                  </button>
                </>
              ) : null}
              {hasPermission("quote_ingestion.create_draft") ? (
                <button
                  type="button"
                  className="rounded bg-slate-900 px-3 py-1 text-sm text-white disabled:opacity-50"
                  disabled={draftM.isPending}
                  onClick={() => draftM.mutate()}
                >
                  Criar rascunho
                </button>
              ) : null}
            </div>

            {draftM.data ? (
              <p className="text-sm text-emerald-800">
                Rascunho {draftM.data.quote_id} ({draftM.data.quote_status}) · activated=
                {String(draftM.data.activated)} ·{" "}
                <Link className="underline" to={`/quotes/${draftM.data.quote_id}`}>
                  abrir na Central
                </Link>
              </p>
            ) : null}
            {draftM.isError ? <p className="text-sm text-red-700">{(draftM.error as Error).message}</p> : null}
            {data.draft_link ? (
              <p className="text-sm">
                Já existe rascunho:{" "}
                <Link className="underline" to={`/quotes/${data.draft_link.quote_id}`}>
                  {data.draft_link.quote_id}
                </Link>
              </p>
            ) : null}
            <p className="text-xs text-slate-500">
              auto_activation={String(data.auto_activation)} · human_review_required=
              {String(data.human_review_required)}
            </p>
          </section>
        </div>
      ) : null}
    </div>
  );
}
