import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { cancelQuote, type Quote } from "../../api/quotes";

type QuoteCancelDialogProps = {
  open: boolean;
  quote: Quote;
  onClose: () => void;
  onSuccess: () => void;
};

export function QuoteCancelDialog({ open, quote, onClose, onSuccess }: QuoteCancelDialogProps) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => cancelQuote(quote.id, quote.version, reason),
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
        <h2 className="text-lg font-semibold">Cancelar cotação</h2>
        <p className="mt-2 text-sm text-slate-600">Informe o motivo do cancelamento.</p>
        {error && (
          <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}
        <div className="mt-4">
          <label className="text-sm font-medium" htmlFor="cancel-reason">
            Motivo
          </label>
          <textarea
            id="cancel-reason"
            className="mt-1 w-full rounded border px-3 py-2 text-sm"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="rounded border px-4 py-2 text-sm" onClick={onClose}>
            Voltar
          </button>
          <button
            type="button"
            className="rounded border border-rose-300 px-4 py-2 text-sm text-rose-700 disabled:opacity-60"
            disabled={!reason.trim() || mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Cancelando..." : "Confirmar cancelamento"}
          </button>
        </div>
      </div>
    </div>
  );
}
