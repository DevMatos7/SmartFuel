import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { reviseQuote, type Quote } from "../../api/quotes";

type QuoteRevisionDialogProps = {
  open: boolean;
  quote: Quote;
  onClose: () => void;
  onSuccess: (draft: Quote) => void;
};

export function QuoteRevisionDialog({ open, quote, onClose, onSuccess }: QuoteRevisionDialogProps) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => reviseQuote(quote.id, reason),
    onSuccess: (draft) => {
      setError(null);
      onSuccess(draft);
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/40"
        aria-label="Fechar diálogo"
        onClick={onClose}
      />
      <div className="relative z-10 w-full max-w-md rounded-lg border bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Criar revisão</h2>
        <p className="mt-2 text-sm text-slate-600">
          Você está criando uma nova versão da cotação #{String(quote.quote_number).padStart(6, "0")}.
          A cotação original permanecerá ativa até que a revisão seja ativada.
        </p>

        {error && (
          <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <div className="mt-4">
          <label className="text-sm font-medium" htmlFor="revise-reason">
            Motivo da revisão
          </label>
          <textarea
            id="revise-reason"
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="rounded border px-4 py-2 text-sm" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
            disabled={!reason.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Criando..." : "Confirmar revisão"}
          </button>
        </div>
      </div>
    </div>
  );
}
