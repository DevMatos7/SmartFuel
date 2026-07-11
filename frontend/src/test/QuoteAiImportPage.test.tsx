import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QuoteAiImportPage } from "../pages/QuoteAiImportPage";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: (p: string) =>
      ["quote_ingestion.read", "quote_ingestion.upload", "operations.manage_feature_flags"].includes(p),
  }),
}));

vi.mock("../api/quote-ingestion", () => ({
  listIngestionDocuments: vi.fn(async () => ({ items: [] })),
  enableQuoteAiPilot: vi.fn(),
  ingestQuoteText: vi.fn(),
}));

describe("QuoteAiImportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows mandatory human review disclaimer", () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter>
          <QuoteAiImportPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByText(/Revisão humana é obrigatória/i)).toBeInTheDocument();
    expect(screen.getByText(/Ativação automática é proibida/i)).toBeInTheDocument();
  });
});
