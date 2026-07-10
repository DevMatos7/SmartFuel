import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { QuoteComparisonPage } from "../pages/QuoteComparisonPage";

const { runQuoteComparison } = vi.hoisted(() => ({
  runQuoteComparison: vi.fn(),
}));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: (perm: string) =>
      ["quote_comparisons.run", "quote_comparisons.read"].includes(perm),
  }),
}));

vi.mock("../api/master-data", () => ({
  fetchProducts: async () => ({ items: [{ id: "prod-1", name: "Gasolina Comum" }], total: 1 }),
}));

vi.mock("../api/quote-comparisons", () => ({
  getComparisonMethodology: async () => ({ version: "QUOTE_COMPARISON_V1" }),
  runQuoteComparison,
}));

const comparisonResult = {
  id: "run-1",
  status: "COMPLETED",
  methodology_version: "QUOTE_COMPARISON_V1",
  scenario: {
    station_id: "station-1",
    product_id: "prod-1",
    requested_volume_liters: "30000.000",
    comparison_datetime: "2026-07-10T09:00:00Z",
    required_delivery_at: null,
    ranking_mode: "DELIVERED",
    ranking_scope: "BEST_PER_DISTRIBUTOR",
  },
  summary: {
    eligible_count: 1,
    warning_count: 1,
    ineligible_count: 1,
    distributor_count: 2,
    best_cost_per_liter: "5.20",
    highest_cost_per_liter: "5.30",
    average_cost_per_liter: "5.25",
    spread_absolute: "0.10",
    spread_percent: "1.92",
  },
  results: [
    {
      quote_id: "q1",
      quote_item_id: "qi1",
      quote_number: 10,
      distributor: { id: "d1", name: "Distribuidora A" },
      eligibility_status: "ELIGIBLE",
      eligibility_reasons: [],
      costs: {
        raw_price_per_liter: "5.20",
        discount_per_liter: "0",
        rebate_per_liter: "0",
        freight_per_liter: "0",
        other_cost_per_liter: "0",
        delivered_cost_per_liter: "5.20",
        delivered_total: "156000",
        financial_days: 0,
        annual_effective_rate: null,
        daily_rate: null,
        financial_equivalent_cost_per_liter: null,
        financial_equivalent_total: null,
      },
      rank_position: 1,
      difference_per_liter: "0",
      difference_total: "0",
      is_best_for_distributor: true,
      is_best_overall: true,
      payment_term_name: "À vista",
      delivery_expected_at: null,
      effective_valid_until: "2026-07-12T00:00:00Z",
      calculation_snapshot: {},
    },
    {
      quote_id: "q2",
      quote_item_id: "qi2",
      quote_number: 11,
      distributor: { id: "d2", name: "Distribuidora B" },
      eligibility_status: "INELIGIBLE",
      eligibility_reasons: [
        {
          code: "MINIMUM_VOLUME_NOT_REACHED",
          severity: "BLOCKING",
          message: "Volume mínimo não atingido",
          metadata: {},
        },
      ],
      costs: {
        raw_price_per_liter: "5.10",
        discount_per_liter: "0",
        rebate_per_liter: "0",
        freight_per_liter: "0",
        other_cost_per_liter: "0",
        delivered_cost_per_liter: "5.10",
        delivered_total: "153000",
        financial_days: 0,
        annual_effective_rate: null,
        daily_rate: null,
        financial_equivalent_cost_per_liter: null,
        financial_equivalent_total: null,
      },
      rank_position: null,
      difference_per_liter: null,
      difference_total: null,
      is_best_for_distributor: false,
      is_best_overall: false,
      payment_term_name: "À vista",
      delivery_expected_at: null,
      effective_valid_until: "2026-07-12T00:00:00Z",
      calculation_snapshot: {},
    },
  ],
  calculation_hash: "abc123",
  processing_duration_ms: 10,
  reprocessed_from_run_id: null,
  input_snapshot: {},
  created_at: "2026-07-10T09:00:00Z",
  created_by: "user-1",
};

describe("QuoteComparisonPage", () => {
  it("renderiza formulário de comparação", async () => {
    localStorage.setItem("active_station_id", "station-1");
    render(
      <MemoryRouter>
        <QuoteComparisonPage />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Comparar cotações")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Comparar propostas/i })).toBeInTheDocument();
  });

  it("exibe ranking e propostas inelegíveis após execução", async () => {
    runQuoteComparison.mockResolvedValueOnce(comparisonResult);
    localStorage.setItem("active_station_id", "station-1");
    render(
      <MemoryRouter>
        <QuoteComparisonPage />
      </MemoryRouter>,
    );
    fireEvent.change(await screen.findByLabelText(/Volume solicitado/i), {
      target: { value: "30000" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Comparar propostas/i }));
    expect(await screen.findByText("Distribuidora A")).toBeInTheDocument();
    expect(screen.getByText(/Propostas fora do ranking/i)).toBeInTheDocument();
    expect(screen.getByText(/Volume mínimo não atingido/i)).toBeInTheDocument();
  });

  it("exibe erro quando API falha", async () => {
    runQuoteComparison.mockRejectedValueOnce(new Error("Falha na comparação"));
    localStorage.setItem("active_station_id", "station-1");
    render(
      <MemoryRouter>
        <QuoteComparisonPage />
      </MemoryRouter>,
    );
    fireEvent.change(await screen.findByLabelText(/Volume solicitado/i), {
      target: { value: "30000" },
    });
    fireEvent.click(screen.getByRole("button", { name: /Comparar propostas/i }));
    await waitFor(() => expect(screen.getByText(/Falha na comparação/i)).toBeInTheDocument());
  });
});
