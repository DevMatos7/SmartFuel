import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchDistributors,
  fetchEffectiveSupplierRule,
  fetchProducts,
  fetchSupplierRules,
} from "../api/master-data";
import { fetchStations } from "../api/stations";
import { SupplierRulesPage } from "../pages/SupplierRulesPage";

const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: hasPermissionMock,
  }),
}));

vi.mock("../api/stations", () => ({
  fetchStations: vi.fn(),
}));

vi.mock("../api/master-data", () => ({
  fetchSupplierRules: vi.fn(),
  fetchDistributors: vi.fn(),
  fetchProducts: vi.fn(),
  fetchEffectiveSupplierRule: vi.fn(),
  createSupplierRule: vi.fn(),
  deactivateSupplierRule: vi.fn(),
  closeSupplierRuleValidity: vi.fn(),
  RULE_SOURCE_LABELS: {
    PRODUCT_SPECIFIC: "Produto específico",
    DISTRIBUTOR_GENERAL: "Distribuidor geral",
    ORGANIZATION_DEFAULT: "Padrão da organização",
    NO_RULE: "Sem regra",
  },
}));

const mockRule = {
  id: "rule1",
  organization_id: "org1",
  station_id: "s1",
  distributor_id: "d1",
  product_id: "p1",
  distribution_base_id: null,
  allowed: true,
  minimum_volume_liters: "5000",
  valid_from: "2026-01-01",
  valid_until: null,
  contract_reference: null,
  reason: null,
  notes: null,
  priority: 100,
  active: true,
  created_by: "u1",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <SupplierRulesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("SupplierRulesPage", () => {
  beforeEach(() => {
    localStorage.setItem("active_station_id", "s1");
    hasPermissionMock.mockReturnValue(false);

    vi.mocked(fetchStations).mockResolvedValue({
      items: [{ id: "s1", trade_name: "Posto Central", station_type: "BRANCH", active: true } as never],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(fetchDistributors).mockResolvedValue({
      items: [{ id: "d1", trade_name: "Alfa", internal_code: "A1", active: true } as never],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(fetchProducts).mockResolvedValue({
      items: [{ id: "p1", name: "Gasolina", code: "GAS", active: true } as never],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(fetchSupplierRules).mockResolvedValue({
      items: [mockRule],
      total: 1,
      page: 1,
      page_size: 20,
    });
    vi.mocked(fetchEffectiveSupplierRule).mockResolvedValue({
      allowed: true,
      minimum_volume_liters: "5000",
      rule_source: "PRODUCT_SPECIFIC",
      rule_id: "r1",
      distribution_base_id: null,
      valid_from: "2026-01-01",
      valid_until: null,
      reason: "Contrato vigente",
    });
  });

  it("exibe simulador de regra efetiva", () => {
    renderPage();
    expect(screen.getByText("Simulador de regra efetiva")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Simular" })).toBeInTheDocument();
  });

  it("exibe origem da regra após simulação", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Simulador de regra efetiva");
    await waitFor(() => {
      expect(screen.getByRole("option", { name: "Posto Central" })).toBeInTheDocument();
    });

    const selects = screen.getAllByRole("combobox");
    await user.selectOptions(selects[0], "s1");
    await user.selectOptions(selects[1], "d1");
    await user.selectOptions(selects[2], "p1");
    await user.click(screen.getByRole("button", { name: "Simular" }));

    expect(await screen.findByText("Produto específico")).toBeInTheDocument();
    expect(screen.getByText("Contrato vigente")).toBeInTheDocument();

    await waitFor(() => {
      expect(fetchEffectiveSupplierRule).toHaveBeenCalledWith(
        expect.objectContaining({
          station_id: "s1",
          distributor_id: "d1",
          product_id: "p1",
        }),
      );
    });
  });
});
