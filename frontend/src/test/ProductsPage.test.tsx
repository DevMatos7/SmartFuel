import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fetchProducts } from "../api/master-data";
import { ProductsPage } from "../pages/ProductsPage";

const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: hasPermissionMock,
  }),
}));

vi.mock("../api/master-data", () => ({
  fetchProducts: vi.fn(),
}));

const mockProduct = {
  id: "p1",
  organization_id: "org1",
  code: "GAS-C",
  name: "Gasolina Comum",
  fuel_family: "GASOLINE_C",
  commercial_variant: "COMMON",
  unit: "LITER",
  regulatory_code: null,
  purchasable: true,
  sellable: true,
  display_order: 0,
  active: true,
  code_locked: false,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderPage(initialEntries = ["/products"]) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <ProductsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProductsPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockReset();
    hasPermissionMock.mockReturnValue(true);
    vi.mocked(fetchProducts).mockReset();
    vi.mocked(fetchProducts).mockResolvedValue({
      items: [mockProduct],
      total: 1,
      page: 1,
      page_size: 20,
    });
  });

  it("exibe estado de carregamento", () => {
    vi.mocked(fetchProducts).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByText("Carregando...")).toBeInTheDocument();
  });

  it("lista produtos", async () => {
    renderPage();
    expect(await screen.findByText("Gasolina Comum")).toBeInTheDocument();
    expect(screen.getByText("GAS-C")).toBeInTheDocument();
    expect(screen.getByText("Ativo")).toBeInTheDocument();
  });

  it("exibe mensagem quando lista está vazia", async () => {
    vi.mocked(fetchProducts).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 });
    renderPage();
    expect(await screen.findByText("Nenhum produto encontrado.")).toBeInTheDocument();
  });

  it("aplica filtro de família", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Gasolina Comum");
    const familySelect = screen.getAllByRole("combobox")[0];
    await user.selectOptions(familySelect, "ETHANOL");

    await waitFor(() => {
      expect(fetchProducts).toHaveBeenCalledWith(
        expect.objectContaining({ fuel_family: "ETHANOL", page: 1 }),
      );
    });
  });

  it("oculta ações de escrita sem permissão", async () => {
    hasPermissionMock.mockImplementation((perm: string) => perm !== "products.write");
    renderPage();

    await screen.findByText("Gasolina Comum");
    expect(screen.queryByRole("link", { name: "Novo produto" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Editar" })).not.toBeInTheDocument();
  });
});
