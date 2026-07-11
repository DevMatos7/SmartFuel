import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ExecutiveDashboardPage } from "../pages/ExecutiveDashboardPage";

const fetchSummaryMock = vi.fn();
const fetchAlertsSummaryMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("../api/executive", () => ({
  fetchExecutiveSummary: (...args: unknown[]) => fetchSummaryMock(...args),
  fetchAlertsSummary: (...args: unknown[]) => fetchAlertsSummaryMock(...args),
  runExecutiveSynthetic: vi.fn(),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ExecutiveDashboardPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ExecutiveDashboardPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockReturnValue(true);
    fetchAlertsSummaryMock.mockResolvedValue({ critical: 1, high: 0, unacknowledged: 1 });
    fetchSummaryMock.mockResolvedValue({
      empty: false,
      disclaimer: "Ausência de dados não é zero.",
      cards: [
        {
          metric_code: "PURCHASE_VOLUME_LITERS",
          label: "Volume comprado",
          value: null,
          unit: "L",
          quality_status: "NOT_SYNCED",
          freshness_status: "NOT_SYNCED",
          coverage_percentage: null,
          updated_at: null,
          deep_link: "/analytics/fuel-purchases",
          source_modules: ["fuel_purchases"],
          empty_reason: "NOT_SYNCED",
        },
      ],
    });
  });

  it("shows empty metric as NOT_SYNCED not zero", async () => {
    renderPage();
    expect(screen.getByText("Visão executiva")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("NOT_SYNCED")).toBeInTheDocument();
    });
    expect(screen.queryByText(/^0$/)).not.toBeInTheDocument();
  });
});
