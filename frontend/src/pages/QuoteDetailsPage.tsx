import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { fetchQuote, fetchQuoteHistory } from "../api/quotes";
import { useAuth } from "../auth/AuthProvider";
import { QuoteActivationDialog } from "../components/quotes/QuoteActivationDialog";
import { QuoteCancelDialog } from "../components/quotes/QuoteCancelDialog";
import { QuoteDuplicateDialog } from "../components/quotes/QuoteDuplicateDialog";
import { QuoteRevisionDialog } from "../components/quotes/QuoteRevisionDialog";
import { QuoteStatusBadge } from "../components/quotes/QuoteStatusBadge";

export function QuoteDetailsPage() {
  const { quoteId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const [tab, setTab] = useState<"summary" | "items" | "evidences" | "history">("summary");
  const [showActivate, setShowActivate] = useState(false);
  const [showCancel, setShowCancel] = useState(false);
  const [showRevise, setShowRevise] = useState(false);
  const [showDuplicate, setShowDuplicate] = useState(false);

  const { data: quote, isLoading, isError } = useQuery({
    queryKey: ["quote", quoteId],
    queryFn: () => fetchQuote(quoteId),
    enabled: Boolean(quoteId),
  });

  const { data: history } = useQuery({
    queryKey: ["quote-history", quoteId],
    queryFn: () => fetchQuoteHistory(quoteId),
    enabled: Boolean(quoteId) && tab === "history",
  });

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["quote", quoteId] });

  if (isLoading) return <p className="text-sm text-slate-500">Carregando cotação...</p>;
  if (isError || !quote) return <p className="text-sm text-rose-600">Cotação não encontrada.</p>;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link to="/quotes" className="text-sm text-slate-500 underline">
            Voltar
          </Link>
          <h1 className="mt-2 text-xl font-semibold">
            Cotação #{String(quote.quote_number).padStart(6, "0")}
          </h1>
          <div className="mt-2">
            <QuoteStatusBadge status={quote.status} effectiveStatus={quote.effective_status} />
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {quote.status === "DRAFT" && hasPermission("quotes.activate") && (
            <button
              type="button"
              className="rounded bg-emerald-700 px-4 py-2 text-sm text-white"
              onClick={() => setShowActivate(true)}
            >
              Ativar cotação
            </button>
          )}
          {quote.status === "DRAFT" && hasPermission("quotes.write") && (
            <Link to={`/quotes/${quote.id}/edit`} className="rounded border px-4 py-2 text-sm">
              Editar rascunho
            </Link>
          )}
          {hasPermission("quotes.revise") && quote.status === "ACTIVE" && (
            <button type="button" className="rounded border px-4 py-2 text-sm" onClick={() => setShowRevise(true)}>
              Criar revisão
            </button>
          )}
          {hasPermission("quotes.duplicate") && (
            <button type="button" className="rounded border px-4 py-2 text-sm" onClick={() => setShowDuplicate(true)}>
              Duplicar
            </button>
          )}
          {["DRAFT", "ACTIVE"].includes(quote.status) && hasPermission("quotes.cancel") && (
            <button
              type="button"
              className="rounded border border-rose-300 px-4 py-2 text-sm text-rose-700"
              onClick={() => setShowCancel(true)}
            >
              Cancelar
            </button>
          )}
        </div>
      </div>

      {quote.warnings?.length > 0 && (
        <div className="rounded border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          {quote.warnings.map((w) => (
            <p key={w}>{w}</p>
          ))}
        </div>
      )}

      <div className="flex flex-wrap gap-2 border-b">
        {(["summary", "items", "evidences", "history"] as const).map((key) => (
          <button
            key={key}
            type="button"
            className={`px-3 py-2 text-sm ${tab === key ? "border-b-2 border-slate-900 font-medium" : "text-slate-500"}`}
            onClick={() => setTab(key)}
          >
            {key === "summary" && "Resumo"}
            {key === "items" && "Itens"}
            {key === "evidences" && "Evidências"}
            {key === "history" && "Histórico"}
          </button>
        ))}
      </div>

      {tab === "summary" && (
        <div className="grid gap-4 rounded-lg border bg-white p-6 md:grid-cols-2 text-sm">
          <p>
            <span className="text-slate-500">Validade:</span> {new Date(quote.valid_until).toLocaleString("pt-BR")}
          </p>
          <p>
            <span className="text-slate-500">Canal:</span> {quote.source_channel}
          </p>
          <p>
            <span className="text-slate-500">Vendedor:</span> {quote.seller_name || "—"}
          </p>
          <p>
            <span className="text-slate-500">Versão:</span> {quote.version}
          </p>
        </div>
      )}

      {tab === "items" && (
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="border-b text-left text-slate-500">
                <th className="p-3">Produto</th>
                <th className="p-3">Preço/L</th>
                <th className="p-3">Condição</th>
                <th className="p-3">Status item</th>
                <th className="p-3">Mínimo</th>
              </tr>
            </thead>
            <tbody>
              {quote.items.map((item) => (
                <tr key={item.id} className="border-b">
                  <td className="p-3">{item.product_id}</td>
                  <td className="p-3">R$ {item.quoted_price_per_liter}</td>
                  <td className="p-3">{item.payment_term_name_snapshot}</td>
                  <td className="p-3">{item.item_effective_status || "—"}</td>
                  <td className="p-3">{item.minimum_volume_liters} L</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {tab === "evidences" && (
        <ul className="space-y-2 rounded-lg border bg-white p-6 text-sm">
          {quote.evidences.length === 0 && <li className="text-slate-500">Nenhuma evidência anexada.</li>}
          {quote.evidences.map((ev) => (
            <li key={ev.id} className="flex justify-between gap-4 border-b py-2">
              <span>
                {ev.original_file_name}
                {ev.is_supplemental && <span className="ml-2 text-xs text-slate-500">(suplementar)</span>}
              </span>
              <span className="text-slate-500">{ev.category}</span>
            </li>
          ))}
        </ul>
      )}

      {tab === "history" && (
        <ul className="space-y-3 rounded-lg border bg-white p-6 text-sm">
          {history?.items.map((entry) => (
            <li key={entry.id} className="border-b pb-2">
              <div className="font-medium">{entry.action}</div>
              <div className="text-slate-500">{new Date(entry.created_at).toLocaleString("pt-BR")}</div>
              {entry.reason && <div className="text-slate-600">{entry.reason}</div>}
            </li>
          ))}
        </ul>
      )}

      <QuoteActivationDialog
        open={showActivate}
        quote={quote}
        onClose={() => setShowActivate(false)}
        onSuccess={refresh}
      />
      <QuoteCancelDialog open={showCancel} quote={quote} onClose={() => setShowCancel(false)} onSuccess={refresh} />
      <QuoteRevisionDialog
        open={showRevise}
        quote={quote}
        onClose={() => setShowRevise(false)}
        onSuccess={(draft) => navigate(`/quotes/${draft.id}`)}
      />
      <QuoteDuplicateDialog
        open={showDuplicate}
        quote={quote}
        onClose={() => setShowDuplicate(false)}
        onSuccess={(draft) => navigate(`/quotes/${draft.id}`)}
      />
    </div>
  );
}
