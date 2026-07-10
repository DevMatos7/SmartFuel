import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QuoteDuplicateDialog } from "../components/quotes/QuoteDuplicateDialog";
import { QuoteRevisionDialog } from "../components/quotes/QuoteRevisionDialog";

const baseQuote = {
  id: "q1",
  organization_id: "org1",
  station_id: "s1",
  distributor_id: "d1",
  distribution_base_id: null,
  quote_number: 12,
  quoted_at: "2026-07-09T12:00:00Z",
  valid_until: "2026-07-09T18:00:00Z",
  source_channel: "WHATSAPP",
  entry_method: "MANUAL",
  seller_name: null,
  seller_contact: null,
  external_reference: null,
  source_description: null,
  notes: null,
  status: "ACTIVE",
  effective_status: "ACTIVE",
  version: 2,
  replaces_quote_id: null,
  duplicated_from_quote_id: null,
  activated_at: null,
  items: [{ id: "i1" } as never],
  evidences: [{ id: "e1" } as never],
  warnings: [],
};

vi.mock("../api/stations", () => ({
  fetchStations: vi.fn().mockResolvedValue({
    items: [
      { id: "s1", trade_name: "Matriz" },
      { id: "s2", trade_name: "Filial" },
    ],
  }),
}));

vi.mock("../api/quotes", () => ({
  duplicateQuote: vi.fn().mockResolvedValue({ id: "q2", status: "DRAFT" }),
  reviseQuote: vi.fn().mockResolvedValue({ id: "q3", status: "DRAFT" }),
}));

describe("QuoteDuplicateDialog", () => {
  it("confirma duplicação com cópia de evidências", async () => {
    const onSuccess = vi.fn();
    const { duplicateQuote } = await import("../api/quotes");
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <QuoteDuplicateDialog open quote={baseQuote} onClose={() => undefined} onSuccess={onSuccess} />
      </QueryClientProvider>,
    );

    fireEvent.click(screen.getByLabelText(/copiar evidências/i));
    fireEvent.click(screen.getByRole("button", { name: /confirmar duplicação/i }));

    await waitFor(() => expect(duplicateQuote).toHaveBeenCalled());
    expect(onSuccess).toHaveBeenCalledWith({ id: "q2", status: "DRAFT" });
  });
});

describe("QuoteRevisionDialog", () => {
  it("exige motivo para revisão", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <QuoteRevisionDialog open quote={baseQuote} onClose={() => undefined} onSuccess={() => undefined} />
      </QueryClientProvider>,
    );

    expect(screen.getByText(/permanecerá ativa/i)).toBeInTheDocument();
    const confirm = screen.getByRole("button", { name: /confirmar revisão/i });
    expect(confirm).toBeDisabled();
    fireEvent.change(screen.getByLabelText(/motivo da revisão/i), {
      target: { value: "Preço corrigido" },
    });
    expect(confirm).not.toBeDisabled();
  });
});
