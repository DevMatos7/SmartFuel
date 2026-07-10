import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { FinancialParametersPage } from "../pages/FinancialParametersPage";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: (perm: string) =>
      ["financial_parameters.read", "financial_parameters.write"].includes(perm),
  }),
}));

vi.mock("../api/quote-comparisons", () => ({
  listFinancialParameters: async () => ({
    items: [
      {
        id: "fp-1",
        annual_effective_rate: "0.15000000",
        day_count_basis: 365,
        valid_from: "2026-01-01T00:00:00Z",
        valid_until: null,
        active: true,
        notes: "Taxa padrão",
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  }),
  createFinancialParameter: vi.fn(),
}));

describe("FinancialParametersPage", () => {
  it("lista parâmetros financeiros com taxa em percentual", async () => {
    render(
      <MemoryRouter>
        <FinancialParametersPage />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/Parâmetros financeiros/i)).toBeInTheDocument();
    expect(screen.getByText(/15/)).toBeInTheDocument();
  });
});
