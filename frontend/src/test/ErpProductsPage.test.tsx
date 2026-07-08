import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchErpProductHistory, fetchErpProducts, fetchProducts } from "../api/master-data";
import { ErpProductsPage } from "../pages/ErpProductsPage";

const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: hasPermissionMock,
  }),
}));

vi.mock("../api/master-data", () => ({
  fetchErpProducts: vi.fn(),
  fetchProducts: vi.fn(),
  fetchErpProductHistory: vi.fn(),
  mapErpProduct: vi.fn(),
  ignoreErpProduct: vi.fn(),
  reopenErpProduct: vi.fn(),
  bulkMapErpProducts: vi.fn(),
  MAPPING_STATUS_LABELS: {
    PENDING: "Pendente",
    MAPPED: "Mapeado",
    IGNORED: "Ignorado",
    CONFLICT: "Conflito",
  },
}));

const mockErpProduct = {
  id: "erp1",
  organization_id: "org1",
  station_id: "s1",
  erp_product_id: "ERP-100",
  erp_product_code: "100",
  erp_description: "Gasolina ERP",
  erp_unit: "L",
  erp_group_id: null,
  erp_group_name: null,
  erp_subgroup_id: null,
  erp_subgroup_name: null,
  canonical_product_id: null,
  mapping_status: "PENDING",
  mapping_source: "MANUAL",
  ignore_reason: null,
  mapped_by: null,
  mapped_at: null,
  last_synced_at: null,
  active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ErpProductsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ErpProductsPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockReset();
    hasPermissionMock.mockReturnValue(true);
    localStorage.setItem("active_station_id", "s1");

    vi.mocked(fetchErpProducts).mockReset();
    vi.mocked(fetchProducts).mockReset();

    vi.mocked(fetchErpProducts).mockImplementation((params) => {
      if (params?.mapping_status) {
        const totals: Record<string, number> = {
          PENDING: 3,
          MAPPED: 5,
          IGNORED: 1,
          CONFLICT: 2,
        };
        return Promise.resolve({
          items: [],
          total: totals[params.mapping_status as string] ?? 0,
          page: 1,
          page_size: 1,
        });
      }
      return Promise.resolve({
        items: [mockErpProduct],
        total: 1,
        page: 1,
        page_size: 20,
      });
    });

    vi.mocked(fetchProducts).mockResolvedValue({
      items: [{ id: "p1", name: "Gasolina Canônica", code: "GAS", active: true } as never],
      total: 1,
      page: 1,
      page_size: 100,
    });
    vi.mocked(fetchErpProductHistory).mockResolvedValue({ items: [] });
  });

  it("exibe cards de status com totais", async () => {
    renderPage();

    expect(await screen.findByText("Produtos ERP")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByText("3")).toBeInTheDocument();
      expect(screen.getByText("5")).toBeInTheDocument();
    });
    expect(screen.getAllByText("Pendente").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Mapeado").length).toBeGreaterThan(0);
  });

  it("abre painel de mapeamento ao clicar em Detalhes", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Gasolina ERP");
    await user.click(screen.getByRole("button", { name: "Detalhes" }));

    expect(await screen.findByRole("heading", { name: "Mapear produto ERP" })).toBeInTheDocument();
  });

  it("permite seleção em lote e exibe ação de mapeamento", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Gasolina ERP");
    const checkbox = screen.getAllByRole("checkbox")[1];
    await user.click(checkbox);

    expect(screen.getByText("1 selecionado(s)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mapear em lote" })).toBeInTheDocument();
  });
});
