import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { QuoteDetailsPage } from "../pages/QuoteDetailsPage";

const { mockQuote } = vi.hoisted(() => ({
  mockQuote: {
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
  seller_name: "Vendedor",
  seller_contact: "65999990000",
  external_reference: null,
  source_description: null,
  notes: null,
  status: "ACTIVE",
  effective_status: "ACTIVE",
  version: 2,
  replaces_quote_id: null,
  duplicated_from_quote_id: null,
  activated_at: "2026-07-09T12:05:00Z",
  items: [
    {
      id: "i1",
      product_id: "p1",
      quoted_price_per_liter: "5.3200",
      payment_term_name_snapshot: "À vista",
      minimum_volume_liters: "5000.000",
      item_effective_status: "ACTIVE",
    },
  ],
  evidences: [],
  warnings: [],
  },
}));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: (p: string) =>
      ["quotes.read", "quotes.duplicate", "quotes.revise", "quotes.cancel"].includes(p),
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ quoteId: "q1" }),
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../api/quotes", () => ({
  fetchQuote: vi.fn().mockResolvedValue(mockQuote),
  fetchQuoteHistory: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  duplicateQuote: vi.fn(),
  reviseQuote: vi.fn(),
  activateQuote: vi.fn(),
  cancelQuote: vi.fn(),
}));

vi.mock("../api/stations", () => ({
  fetchStations: vi.fn().mockResolvedValue({ items: [{ id: "s1", trade_name: "Matriz" }] }),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <QuoteDetailsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("QuoteDetailsPage", () => {
  it("exibe ações de duplicar e revisar", async () => {
    renderPage();
    expect(await screen.findByText(/Cotação #000012/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /duplicar/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /criar revisão/i })).toBeInTheDocument();
  });

  it("abre diálogo de duplicação", async () => {
    renderPage();
    await screen.findByText(/Cotação #000012/);
    fireEvent.click(screen.getByRole("button", { name: /duplicar/i }));
    expect(await screen.findByText(/duplicar cotação/i)).toBeInTheDocument();
  });

  it("exibe status efetivo do item", async () => {
    renderPage();
    await screen.findByText(/Cotação #000012/);
    fireEvent.click(screen.getByRole("button", { name: /itens/i }));
    await waitFor(() => expect(screen.getByText("ACTIVE")).toBeInTheDocument());
  });
});
