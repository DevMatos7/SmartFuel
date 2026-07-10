import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";
import { fetchDistributors, fetchPaymentTerms, fetchProducts } from "../api/master-data";
import { addQuoteItem, createQuote, uploadQuoteEvidence } from "../api/quotes";
import { fetchStations } from "../api/stations";
import { useAuth } from "../auth/AuthProvider";

const headerSchema = z.object({
  station_id: z.string().min(1, "Selecione o posto"),
  distributor_id: z.string().min(1, "Selecione a distribuidora"),
  distribution_base_id: z.string().optional(),
  quoted_at: z.string().min(1),
  valid_until: z.string().min(1),
  source_channel: z.enum(["WHATSAPP", "PORTAL", "EMAIL", "PHONE", "OTHER"]),
  seller_name: z.string().optional(),
  seller_contact: z.string().optional(),
  external_reference: z.string().optional(),
  source_description: z.string().optional(),
  notes: z.string().optional(),
});

const itemSchema = z.object({
  product_id: z.string().min(1),
  payment_term_id: z.string().min(1),
  quoted_price_per_liter: z.string().min(1),
  minimum_volume_liters: z.string().min(1),
  freight_type: z.enum(["CIF", "FOB"]),
  freight_calculation_type: z.enum(["NONE", "TOTAL", "PER_LITER"]),
});

type HeaderForm = z.infer<typeof headerSchema>;
type ItemForm = z.infer<typeof itemSchema>;

const STEPS = ["Identificação", "Itens", "Evidências", "Revisão"];

export function QuoteFormPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { hasPermission } = useAuth();
  const [step, setStep] = useState(0);
  const [quoteId, setQuoteId] = useState<string | null>(null);
  const [version, setVersion] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);

  const headerForm = useForm<HeaderForm>({
    resolver: zodResolver(headerSchema),
    defaultValues: {
      quoted_at: new Date().toISOString().slice(0, 16),
      valid_until: new Date(Date.now() + 5 * 3600000).toISOString().slice(0, 16),
      source_channel: "WHATSAPP",
    },
  });

  const itemForm = useForm<ItemForm>({
    resolver: zodResolver(itemSchema),
    defaultValues: {
      freight_type: "CIF",
      freight_calculation_type: "NONE",
      minimum_volume_liters: "5000.000",
      quoted_price_per_liter: "5.0000",
    },
  });

  const { data: stations } = useQuery({
    queryKey: ["stations"],
    queryFn: () => fetchStations({ page: 1, page_size: 100, active: true }),
  });
  const { data: distributors } = useQuery({
    queryKey: ["distributors"],
    queryFn: () => fetchDistributors({ active: true, page: 1, page_size: 100 }),
  });
  const { data: products } = useQuery({
    queryKey: ["products"],
    queryFn: () => fetchProducts({ active: true, page: 1, page_size: 100 }),
  });
  const { data: paymentTerms } = useQuery({
    queryKey: ["payment-terms"],
    queryFn: () => fetchPaymentTerms({ active: true, page: 1, page_size: 100 }),
  });

  const createMutation = useMutation({
    mutationFn: createQuote,
    onSuccess: (quote) => {
      setQuoteId(quote.id);
      setVersion(quote.version);
      setStep(1);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  const addItemMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => addQuoteItem(quoteId!, payload),
    onSuccess: (item) => {
      setVersion((v) => v + 1);
      setStep(2);
      setError(null);
      void item;
    },
    onError: (err: Error) => setError(err.message),
  });

  const uploadMutation = useMutation({
    mutationFn: () =>
      uploadQuoteEvidence(quoteId!, evidenceFile!, "SCREENSHOT", version, false),
    onSuccess: (quote) => {
      setVersion(quote.version);
      setStep(3);
      setError(null);
    },
    onError: (err: Error) => setError(err.message),
  });

  if (!hasPermission("quotes.write")) {
    return <p className="text-sm text-rose-600">Você não possui permissão para criar cotações.</p>;
  }

  async function saveHeader(values: HeaderForm) {
    await createMutation.mutateAsync({
      ...values,
      distribution_base_id: values.distribution_base_id || null,
      entry_method: "MANUAL",
      quoted_at: new Date(values.quoted_at).toISOString(),
      valid_until: new Date(values.valid_until).toISOString(),
    });
  }

  async function saveItem(values: ItemForm) {
    if (!quoteId) return;
    await addItemMutation.mutateAsync({
      ...values,
      expected_version: version,
    });
  }

  async function saveEvidence() {
    if (!evidenceFile) {
      setError("Selecione um arquivo de evidência.");
      return;
    }
    await uploadMutation.mutateAsync();
    queryClient.invalidateQueries({ queryKey: ["quotes"] });
  }

  return (
    <div className="space-y-6">
      <div>
        <Link to="/quotes" className="text-sm text-slate-500 underline">
          Voltar para cotações
        </Link>
        <h1 className="mt-2 text-xl font-semibold">Nova cotação</h1>
      </div>

      <ol className="flex flex-wrap gap-2">
        {STEPS.map((label, index) => (
          <li
            key={label}
            className={`rounded-full px-3 py-1 text-xs ${
              index === step ? "bg-slate-900 text-white" : "bg-slate-200 text-slate-600"
            }`}
          >
            {index + 1}. {label}
          </li>
        ))}
      </ol>

      {error && <p className="rounded bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</p>}

      {step === 0 && (
        <form onSubmit={headerForm.handleSubmit(saveHeader)} className="space-y-4 rounded-lg border bg-white p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-xs text-slate-500">Posto</label>
              <select className="mt-1 w-full rounded border px-3 py-2 text-sm" {...headerForm.register("station_id")}>
                <option value="">Selecione...</option>
                {stations?.items.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.trade_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Distribuidora</label>
              <select
                className="mt-1 w-full rounded border px-3 py-2 text-sm"
                {...headerForm.register("distributor_id")}
              >
                <option value="">Selecione...</option>
                {distributors?.items.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.trade_name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Data da cotação</label>
              <input type="datetime-local" className="mt-1 w-full rounded border px-3 py-2 text-sm" {...headerForm.register("quoted_at")} />
            </div>
            <div>
              <label className="text-xs text-slate-500">Validade</label>
              <input type="datetime-local" className="mt-1 w-full rounded border px-3 py-2 text-sm" {...headerForm.register("valid_until")} />
            </div>
            <div>
              <label className="text-xs text-slate-500">Canal</label>
              <select className="mt-1 w-full rounded border px-3 py-2 text-sm" {...headerForm.register("source_channel")}>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="PORTAL">Portal</option>
                <option value="EMAIL">E-mail</option>
                <option value="PHONE">Telefone</option>
                <option value="OTHER">Outro</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Vendedor</label>
              <input className="mt-1 w-full rounded border px-3 py-2 text-sm" {...headerForm.register("seller_name")} />
            </div>
          </div>
          <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-sm text-white" disabled={createMutation.isPending}>
            Salvar rascunho e continuar
          </button>
        </form>
      )}

      {step === 1 && quoteId && (
        <form onSubmit={itemForm.handleSubmit(saveItem)} className="space-y-4 rounded-lg border bg-white p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className="text-xs text-slate-500">Produto</label>
              <select className="mt-1 w-full rounded border px-3 py-2 text-sm" {...itemForm.register("product_id")}>
                <option value="">Selecione...</option>
                {products?.items.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Condição de pagamento</label>
              <select className="mt-1 w-full rounded border px-3 py-2 text-sm" {...itemForm.register("payment_term_id")}>
                <option value="">Selecione...</option>
                {paymentTerms?.items.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500">Preço por litro</label>
              <input className="mt-1 w-full rounded border px-3 py-2 text-sm" {...itemForm.register("quoted_price_per_liter")} />
            </div>
            <div>
              <label className="text-xs text-slate-500">Volume mínimo (L)</label>
              <input className="mt-1 w-full rounded border px-3 py-2 text-sm" {...itemForm.register("minimum_volume_liters")} />
            </div>
          </div>
          <button type="submit" className="rounded bg-slate-900 px-4 py-2 text-sm text-white" disabled={addItemMutation.isPending}>
            Adicionar item e continuar
          </button>
        </form>
      )}

      {step === 2 && quoteId && (
        <div className="space-y-4 rounded-lg border bg-white p-6">
          <label className="text-xs text-slate-500">Evidência (print, PDF, planilha)</label>
          <input type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.xlsx,.csv" onChange={(e) => setEvidenceFile(e.target.files?.[0] ?? null)} />
          <div className="flex gap-2">
            <button type="button" className="rounded bg-slate-900 px-4 py-2 text-sm text-white" onClick={() => void saveEvidence()} disabled={uploadMutation.isPending}>
              Enviar evidência
            </button>
            <button type="button" className="rounded border px-4 py-2 text-sm" onClick={() => setStep(3)}>
              Pular (somente telefone)
            </button>
          </div>
        </div>
      )}

      {step === 3 && quoteId && (
        <div className="space-y-4 rounded-lg border bg-white p-6">
          <p className="text-sm text-slate-600">Rascunho salvo. Revise os dados e ative na tela de detalhe.</p>
          <button type="button" className="rounded bg-slate-900 px-4 py-2 text-sm text-white" onClick={() => navigate(`/quotes/${quoteId}`)}>
            Abrir cotação
          </button>
        </div>
      )}
    </div>
  );
}
