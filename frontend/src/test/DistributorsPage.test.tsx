import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createDistributor, fetchDistributors } from "../api/master-data";
import { DistributorDetailsPage } from "../pages/DistributorDetailsPage";
import { DistributorsPage } from "../pages/DistributorsPage";

const hasPermissionMock = vi.fn();
const navigateMock = vi.fn();
const useParamsMock = vi.fn(() => ({ distributorId: "new" }));

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
  fetchDistributors: vi.fn(),
  createDistributor: vi.fn(),
  updateDistributor: vi.fn(),
  fetchDistributor: vi.fn(),
  deactivateDistributor: vi.fn(),
  reactivateDistributor: vi.fn(),
  fetchDistributorBases: vi.fn(),
  createDistributionBase: vi.fn(),
  updateDistributionBase: vi.fn(),
  deactivateDistributionBase: vi.fn(),
  fetchErpSuppliers: vi.fn(),
  mapErpSupplier: vi.fn(),
  ignoreErpSupplier: vi.fn(),
  MAPPING_STATUS_LABELS: {},
}));

const mockDistributor = {
  id: "d1",
  organization_id: "org1",
  internal_code: "DIST-01",
  corporate_name: "Distribuidora Alfa LTDA",
  trade_name: "Alfa Combustíveis",
  cnpj: "12345678000199",
  normalized_name: "ALFA COMBUSTIVEIS",
  registration_status: "COMPLETE",
  notes: null,
  active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

function renderWithProviders(ui: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DistributorsPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockReset();
    hasPermissionMock.mockReturnValue(true);
    vi.mocked(fetchDistributors).mockReset();
    vi.mocked(fetchDistributors).mockResolvedValue({
      items: [mockDistributor],
      total: 1,
      page: 1,
      page_size: 20,
    });
  });

  it("lista distribuidores", async () => {
    renderWithProviders(<DistributorsPage />);
    expect(await screen.findByText("Alfa Combustíveis")).toBeInTheDocument();
    expect(screen.getByText("DIST-01")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Completo" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "Ativo" })).toBeInTheDocument();
  });

  it("exibe erro ao falhar criação de distribuidor", async () => {
    hasPermissionMock.mockImplementation((perm: string) => perm === "distributors.write");
    vi.mocked(createDistributor).mockRejectedValue(new Error("Código interno já cadastrado."));

    renderWithProviders(<DistributorDetailsPage />);

    const user = userEvent.setup();
    const inputs = screen.getAllByRole("textbox");
    await user.type(inputs[0], "DIST-02");
    await user.type(inputs[2], "Beta LTDA");
    await user.type(inputs[3], "Beta");
    await user.click(screen.getByRole("button", { name: "Salvar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Código interno já cadastrado.");
  });
});
