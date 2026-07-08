import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  fetchOrganizationBusinessSettings,
  updateOrganizationBusinessSettings,
} from "../api/organization-settings";
import { OrganizationPurchaseSettings } from "../components/organization/OrganizationPurchaseSettings";

const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: hasPermissionMock,
  }),
}));

vi.mock("../api/organization-settings", () => ({
  fetchOrganizationBusinessSettings: vi.fn(),
  updateOrganizationBusinessSettings: vi.fn(),
}));

const mockSettings = {
  id: "obs1",
  organization_id: "org1",
  default_supplier_allowed: false,
  default_minimum_volume_liters: "5000",
  updated_by: null,
};

function renderSection() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <OrganizationPurchaseSettings />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("OrganizationPurchaseSettings", () => {
  beforeEach(() => {
    hasPermissionMock.mockReset();
    hasPermissionMock.mockReturnValue(true);
    vi.mocked(fetchOrganizationBusinessSettings).mockReset();
    vi.mocked(updateOrganizationBusinessSettings).mockReset();
    vi.mocked(fetchOrganizationBusinessSettings).mockResolvedValue(mockSettings);
    vi.mocked(updateOrganizationBusinessSettings).mockResolvedValue({
      ...mockSettings,
      default_supplier_allowed: true,
      default_minimum_volume_liters: "8000",
    });
  });

  it("exibe seção de política de compra com valores carregados", async () => {
    renderSection();
    expect(await screen.findByText("Política de compra")).toBeInTheDocument();
    expect(screen.getByText(/Regras padrão de fornecimento/)).toBeInTheDocument();
    expect(screen.getByLabelText("Volume mínimo padrão (L)")).toHaveValue(5000);
    expect(screen.getByRole("checkbox", { name: /Fornecimento permitido por padrão/i })).not.toBeChecked();
  });

  it("salva política de compra com permissão de escrita", async () => {
    const user = userEvent.setup();
    renderSection();

    await screen.findByText("Política de compra");
    await user.click(screen.getByRole("checkbox", { name: /Fornecimento permitido por padrão/i }));
    await user.clear(screen.getByLabelText("Volume mínimo padrão (L)"));
    await user.type(screen.getByLabelText("Volume mínimo padrão (L)"), "8000");
    await user.click(screen.getByRole("button", { name: "Salvar política" }));

    await waitFor(() => {
      expect(updateOrganizationBusinessSettings).toHaveBeenCalledWith({
        default_supplier_allowed: true,
        default_minimum_volume_liters: 8000,
      });
    });
    expect(await screen.findByText("Política de compra salva com sucesso.")).toBeInTheDocument();
  });

  it("desabilita edição sem permissão organizations.write", async () => {
    hasPermissionMock.mockImplementation((perm: string) => perm !== "organizations.write");
    renderSection();

    await screen.findByText("Política de compra");
    expect(screen.getByLabelText("Volume mínimo padrão (L)")).toBeDisabled();
    expect(screen.queryByRole("button", { name: "Salvar política" })).not.toBeInTheDocument();
  });
});
