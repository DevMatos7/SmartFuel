import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { activateQuote, type Quote } from "../../api/quotes";

type QuoteActivationDialogProps = {
  open: boolean;
  quote: Quote;
  onClose: () => void;
  onSuccess: () => void;
};

export function QuoteActivationDialog({ open, quote, onClose, onSuccess }: QuoteActivationDialogProps) {
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => activateQuote(quote.id, quote.version),
    onSuccess: () => {
      setError(null);
      onSuccess();
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
        <h2 className="text-lg font-semibold">Ativar cotação</h2>
        <p className="mt-2 text-sm text-slate-600">
          Após a ativação, os campos comerciais ficarão bloqueados. Correções exigirão uma revisão.
        </p>
        {quote.replaces_quote_id && (
          <p className="mt-2 text-sm text-amber-800">
            Ao ativar, a cotação original será marcada como substituída.
          </p>
        )}
        {error && (
          <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="rounded border px-4 py-2 text-sm" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="rounded bg-emerald-700 px-4 py-2 text-sm text-white disabled:opacity-60"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Ativando..." : "Confirmar ativação"}
          </button>
        </div>
      </div>
    </div>
  );
}
