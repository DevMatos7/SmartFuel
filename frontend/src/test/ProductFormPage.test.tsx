import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createProduct, fetchProduct, updateProduct } from "../api/master-data";
import { ProductFormPage } from "../pages/ProductFormPage";

const navigateMock = vi.fn();
const hasPermissionMock = vi.fn();
const useParamsMock = vi.fn(() => ({ productId: "new" }));

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: hasPermissionMock,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useParams: () => useParamsMock(),
    useNavigate: () => navigateMock,
  };
});

vi.mock("../api/master-data", () => ({
  fetchProduct: vi.fn(),
  createProduct: vi.fn(),
  updateProduct: vi.fn(),
  deactivateProduct: vi.fn(),
  reactivateProduct: vi.fn(),
}));

const mockProduct = {
  id: "p1",
  organization_id: "org1",
  code: "ET-001",
  name: "Etanol Hidratado",
  fuel_family: "ETHANOL",
  commercial_variant: "COMMON",
  unit: "LITER",
  regulatory_code: null,
  purchasable: true,
  sellable: false,
  display_order: 1,
  active: true,
  code_locked: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ProductFormPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ProductFormPage", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    useParamsMock.mockReturnValue({ productId: "new" });
    hasPermissionMock.mockReturnValue(true);
    vi.mocked(createProduct).mockReset();
    vi.mocked(fetchProduct).mockReset();
    vi.mocked(updateProduct).mockReset();
    vi.mocked(createProduct).mockResolvedValue(mockProduct);
    vi.mocked(updateProduct).mockResolvedValue(mockProduct);
  });

  it("exibe validação ao criar sem campos obrigatórios", async () => {
    const user = userEvent.setup();
    useParamsMock.mockReturnValue({ productId: "new" });

    renderPage();
    await user.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByText("Código obrigatório")).toBeInTheDocument();
    expect(screen.getByText("Nome obrigatório")).toBeInTheDocument();
  });

  it("carrega dados ao editar produto existente", async () => {
    useParamsMock.mockReturnValue({ productId: "p1" });
    vi.mocked(fetchProduct).mockResolvedValue(mockProduct);

    renderPage();

    expect(await screen.findByText("Editar produto")).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByLabelText("Código")).toHaveValue("ET-001");
      expect(screen.getByLabelText("Nome")).toHaveValue("Etanol Hidratado");
    });
    expect(screen.getByLabelText("Código")).toBeDisabled();
  });
});
