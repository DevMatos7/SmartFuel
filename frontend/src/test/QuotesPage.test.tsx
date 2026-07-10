import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { QuotesPage } from "../pages/QuotesPage";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: (p: string) => ["quotes.read", "quotes.write"].includes(p),
  }),
}));

vi.mock("../api/quotes", () => ({
  fetchQuotes: vi.fn().mockResolvedValue({
    items: [
      {
        id: "q1",
        quote_number: 12,
        station_id: "s1",
        distributor_id: "d1",
        quoted_at: "2026-07-08T09:00:00Z",
        valid_until: "2026-07-08T14:00:00Z",
        source_channel: "WHATSAPP",
        status: "ACTIVE",
        effective_status: "ACTIVE",
        version: 3,
        item_count: 2,
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
    summary: { ACTIVE: 1, DRAFT: 0 },
  }),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <QuotesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("QuotesPage", () => {
  it("renderiza listagem e cards", async () => {
    renderPage();
    expect(await screen.findByText("Cotações")).toBeInTheDocument();
    expect(await screen.findByText("Nova cotação")).toBeInTheDocument();
    expect(await screen.findByText("#000012")).toBeInTheDocument();
    expect(await screen.findByText("WHATSAPP")).toBeInTheDocument();
  });
});
