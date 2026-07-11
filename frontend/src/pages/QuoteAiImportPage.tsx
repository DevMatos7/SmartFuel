import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  enableQuoteAiPilot,
  ingestQuoteText,
  listIngestionDocuments,
} from "../api/quote-ingestion";
import { useAuth } from "../auth/AuthProvider";

export function QuoteAiImportPage() {
  const { hasPermission } = useAuth();
  const qc = useQueryClient();
  const docsQ = useQuery({ queryKey: ["quote-ingestion-docs"], queryFn: listIngestionDocuments });
  const enableM = useMutation({
    mutationFn: enableQuoteAiPilot,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quote-ingestion-docs"] }),
  });
  const ingestM = useMutation({
    mutationFn: (text: string) => ingestQuoteText({ text }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["quote-ingestion-docs"] }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold">Importar cotações com IA</h1>
        <p className="text-sm text-slate-600">
          A IA extrai e sugere. Revisão humana é obrigatória. Ativação automática é proibida.
        </p>
      </div>

      <div className="rounded border border-amber-200 bg-amber-50 px-3 py-2 text-sm">
        Feature flag padrão: desligada · WhatsApp não oficial: proibido · Escrita XPERT: proibida ·
        E-mail automático: desligado
      </div>

      <div className="flex flex-wrap gap-3 text-sm">
        <Link className="underline" to="/quotes/ai/batches">
          Lotes
        </Link>
        <Link className="underline" to="/quotes/ai/quality">
          Qualidade
        </Link>
        <Link className="underline" to="/quotes">
          Central de Cotações
        </Link>
      </div>

      {hasPermission("operations.manage_feature_flags") ? (
        <button
          type="button"
          className="rounded bg-slate-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          disabled={enableM.isPending}
          onClick={() => enableM.mutate()}
        >
          Habilitar piloto nesta organização
        </button>
      ) : null}

      {hasPermission("quote_ingestion.upload") ? (
        <form
          className="space-y-3"
          onSubmit={(e) => {
            e.preventDefault();
            const fd = new FormData(e.currentTarget);
            const text = String(fd.get("text") || "");
            if (text.trim()) ingestM.mutate(text);
          }}
        >
          <label className="block text-sm font-medium">
            Colar texto da cotação
            <textarea
              name="text"
              rows={8}
              className="mt-1 w-full rounded border border-slate-300 px-3 py-2 font-mono text-sm"
              placeholder={"Distribuidora Exemplo\nDiesel S10: 6,21\nPagamento 7 dias\nVálido até 16h"}
            />
          </label>
          <button
            type="submit"
            className="rounded bg-emerald-700 px-3 py-2 text-sm text-white disabled:opacity-50"
            disabled={ingestM.isPending}
          >
            Enviar para extração
          </button>
          {ingestM.isError ? (
            <p className="text-sm text-red-700">{(ingestM.error as Error).message}</p>
          ) : null}
          {ingestM.data ? (
            <p className="text-sm text-emerald-800">
              Documento {ingestM.data.document.id} · status {ingestM.data.document.status} ·{" "}
              <Link className="underline" to={`/quotes/ai/documents/${ingestM.data.document.id}`}>
                revisar
              </Link>
            </p>
          ) : null}
        </form>
      ) : null}

      <div>
        <h2 className="mb-2 font-medium">Documentos recentes</h2>
        {docsQ.isLoading ? <p className="text-sm">Carregando…</p> : null}
        <ul className="divide-y rounded border">
          {(docsQ.data?.items ?? []).map((d) => (
            <li key={d.id} className="flex items-center justify-between px-3 py-2 text-sm">
              <span>
                {d.original_filename || "texto"} · {d.status} · {d.document_type}
              </span>
              <Link className="underline" to={`/quotes/ai/documents/${d.id}`}>
                Abrir
              </Link>
            </li>
          ))}
          {!docsQ.isLoading && (docsQ.data?.items ?? []).length === 0 ? (
            <li className="px-3 py-4 text-sm text-slate-500">Nenhum documento ingerido.</li>
          ) : null}
        </ul>
      </div>
    </div>
  );
}
