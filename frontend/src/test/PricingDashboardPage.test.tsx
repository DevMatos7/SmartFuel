import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { PricingDashboardPage } from "../pages/PricingDashboardPage";

const fetchSummaryMock = vi.fn();
const fetchItemsMock = vi.fn();
const fetchBelowMock = vi.fn();
const fetchRunsMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("../api/pricing", () => ({
  fetchPricingSummary: (...args: unknown[]) => fetchSummaryMock(...args),
  fetchPricingRecommendations: (...args: unknown[]) => fetchItemsMock(...args),
  fetchBelowFloor: (...args: unknown[]) => fetchBelowMock(...args),
  fetchPricingRuns: (...args: unknown[]) => fetchRunsMock(...args),
  runSyntheticPricingHomologation: vi.fn(),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PricingDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PricingDashboardPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockReturnValue(true);
    fetchSummaryMock.mockResolvedValue({
      monitored_products: 0,
      below_floor: 0,
      average_margin_per_liter: null,
      increase_recommendations: 0,
      decrease_recommendations: 0,
      pending_approval: 0,
      approved_not_implemented: 0,
      divergent_implementations: 0,
      disclaimer: "Margem bruta comercial estimada. Não é lucro líquido.",
      xpert_write_enabled: false,
    });
    fetchItemsMock.mockResolvedValue([]);
    fetchBelowMock.mockResolvedValue([]);
    fetchRunsMock.mockResolvedValue([]);
  });

  it("renders empty dashboard with disclaimer", async () => {
    renderPage();
    expect(screen.getByText("Precificação")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("Produtos monitorados")).toBeInTheDocument();
      expect(screen.getByText("Homologação sintética")).toBeInTheDocument();
    });
    expect(screen.getByText(/recomendação ≠ aprovado ≠ implantado/)).toBeInTheDocument();
  });

  it("shows below-floor and recommendation rows", async () => {
    fetchSummaryMock.mockResolvedValue({
      monitored_products: 1,
      below_floor: 1,
      average_margin_per_liter: "0.10",
      increase_recommendations: 1,
      decrease_recommendations: 0,
      pending_approval: 0,
      approved_not_implemented: 0,
      divergent_implementations: 0,
      disclaimer: "Margem bruta comercial estimada.",
      xpert_write_enabled: false,
    });
    fetchBelowMock.mockResolvedValue([
      {
        id: "item-1",
        station_id: "st",
        current_price: "5.10",
        commercial_floor_price: "5.30",
        gap: "0.20",
      },
    ]);
    fetchItemsMock.mockResolvedValue([
      {
        id: "item-1",
        recommendation_run_id: "run-1",
        station_id: "st",
        canonical_product_id: "pr",
        price_type: "POSTED_PRICE",
        current_price: "5.10",
        cost_per_liter: "5.00",
        cost_confidence: "HIGH",
        current_margin_per_liter: "0.10",
        commercial_floor_price: "5.30",
        target_price: "5.50",
        recommended_price: "5.50",
        recommendation_status: "INCREASE",
        quality_status: "READY",
        guardrail_applied: false,
        reasons: ["BELOW_COMMERCIAL_FLOOR"],
        warnings: null,
        snapshot_hash: "abc",
      },
    ]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByText("gap 0.20")).toBeInTheDocument();
    });
    expect(screen.getByText("INCREASE")).toBeInTheDocument();
  });
});
