import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { duplicateQuote, type Quote } from "../../api/quotes";
import { fetchStations } from "../../api/stations";

type QuoteDuplicateDialogProps = {
  open: boolean;
  quote: Quote;
  onClose: () => void;
  onSuccess: (draft: Quote) => void;
};

export function QuoteDuplicateDialog({ open, quote, onClose, onSuccess }: QuoteDuplicateDialogProps) {
  const [targetStationId, setTargetStationId] = useState(quote.station_id);
  const [quotedAt, setQuotedAt] = useState(quote.quoted_at.slice(0, 16));
  const [validUntil, setValidUntil] = useState(quote.valid_until.slice(0, 16));
  const [copyEvidences, setCopyEvidences] = useState(false);
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  const { data: stations } = useQuery({
    queryKey: ["stations", { active: true }],
    queryFn: () => fetchStations({ active: true, page: 1, page_size: 100 }),
    enabled: open,
  });

  const mutation = useMutation({
    mutationFn: () =>
      duplicateQuote(quote.id, {
        target_station_id: targetStationId,
        quoted_at: new Date(quotedAt).toISOString(),
        valid_until: new Date(validUntil).toISOString(),
        copy_evidences: copyEvidences,
        notes: notes || undefined,
      }),
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
      <div className="relative z-10 w-full max-w-lg rounded-lg border bg-white p-6 shadow-xl">
        <h2 className="text-lg font-semibold">Duplicar cotação</h2>
        <p className="mt-1 text-sm text-slate-500">
          Será criado um novo rascunho com {quote.items.length} item(ns) e {quote.evidences.length}{" "}
          evidência(s) na origem.
        </p>

        {error && (
          <p className="mt-4 rounded bg-red-50 px-3 py-2 text-sm text-red-700" role="alert">
            {error}
          </p>
        )}

        <div className="mt-4 space-y-3 text-sm">
          <div>
            <label className="font-medium" htmlFor="dup-station">
              Posto de destino
            </label>
            <select
              id="dup-station"
              className="mt-1 w-full rounded border px-3 py-2"
              value={targetStationId}
              onChange={(e) => setTargetStationId(e.target.value)}
            >
              {stations?.items.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.trade_name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className="font-medium" htmlFor="dup-quoted-at">
                Data da cotação
              </label>
              <input
                id="dup-quoted-at"
                type="datetime-local"
                className="mt-1 w-full rounded border px-3 py-2"
                value={quotedAt}
                onChange={(e) => setQuotedAt(e.target.value)}
              />
            </div>
            <div>
              <label className="font-medium" htmlFor="dup-valid-until">
                Validade
              </label>
              <input
                id="dup-valid-until"
                type="datetime-local"
                className="mt-1 w-full rounded border px-3 py-2"
                value={validUntil}
                onChange={(e) => setValidUntil(e.target.value)}
              />
            </div>
          </div>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={copyEvidences}
              onChange={(e) => setCopyEvidences(e.target.checked)}
            />
            Copiar evidências para o novo rascunho
          </label>
          <div>
            <label className="font-medium" htmlFor="dup-notes">
              Observação (opcional)
            </label>
            <input
              id="dup-notes"
              className="mt-1 w-full rounded border px-3 py-2"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </div>
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button type="button" className="rounded border px-4 py-2 text-sm" onClick={onClose}>
            Cancelar
          </button>
          <button
            type="button"
            className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-60"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate()}
          >
            {mutation.isPending ? "Duplicando..." : "Confirmar duplicação"}
          </button>
        </div>
      </div>
    </div>
  );
}
