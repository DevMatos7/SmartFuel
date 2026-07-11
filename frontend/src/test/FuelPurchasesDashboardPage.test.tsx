import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { FuelPurchasesDashboardPage } from "../pages/FuelPurchasesDashboardPage";

const fetchSummaryMock = vi.fn();
const fetchTrendMock = vi.fn();
const fetchByProductMock = vi.fn();
const fetchByDistributorMock = vi.fn();
const fetchFreshnessMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("../api/fuel-purchases-analytics", () => ({
  fetchFuelPurchasesSummary: (...args: unknown[]) => fetchSummaryMock(...args),
  fetchFuelPurchasesTrend: (...args: unknown[]) => fetchTrendMock(...args),
  fetchFuelPurchasesByProduct: (...args: unknown[]) => fetchByProductMock(...args),
  fetchFuelPurchasesByDistributor: (...args: unknown[]) => fetchByDistributorMock(...args),
  fetchFuelPurchasesFreshness: (...args: unknown[]) => fetchFreshnessMock(...args),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <FuelPurchasesDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("FuelPurchasesDashboardPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockImplementation((p: string) =>
      ["fuel_purchases.read", "fuel_purchases.view_cost", "purchase_invoices.read"].includes(p),
    );
    fetchSummaryMock.mockResolvedValue({
      purchased_volume_liters: "0",
      gross_purchase_amount: "0",
      commercial_delivered_cost: "0",
      average_delivered_cost_per_liter: null,
      total_freight_amount: "0",
      total_discount_amount: "0",
      invoice_count: 0,
      weighted_term_days: null,
      open_payable_amount: "0",
    });
    fetchTrendMock.mockResolvedValue([]);
    fetchByProductMock.mockResolvedValue([]);
    fetchByDistributorMock.mockResolvedValue([]);
    fetchFreshnessMock.mockResolvedValue({ status: "UNAVAILABLE", security_status: null });
  });

  it("shows loading placeholders while summary is loading", () => {
    fetchSummaryMock.mockReturnValue(new Promise(() => undefined));
    renderPage();
    expect(screen.getAllByText("...").length).toBeGreaterThan(0);
    expect(screen.getByText("Compras de combustíveis")).toBeInTheDocument();
  });

  it("shows empty state when there is no trend data", async () => {
    renderPage();
    await waitFor(() => {
      expect(
        screen.getByText("Sem dados no período. Execute a sincronização FUEL_PURCHASE_INVOICES."),
      ).toBeInTheDocument();
    });
    expect(screen.getByText("Sem compras elegíveis no período.")).toBeInTheDocument();
    expect(screen.getByText("Sem compras por distribuidora no período.")).toBeInTheDocument();
  });
});
