import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { UserFormPage } from "../pages/UserFormPage";

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useParams: () => ({ userId: "new" }),
    useNavigate: () => vi.fn(),
  };
});

vi.mock("../api/stations", () => ({
  fetchStations: vi.fn().mockResolvedValue({
    items: [
      { id: "s1", trade_name: "Matriz", station_type: "HEADQUARTERS", active: true },
      { id: "s2", trade_name: "Filial", station_type: "BRANCH", active: true },
    ],
  }),
}));

vi.mock("../api/users", () => ({
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
  updateUserRoles: vi.fn(),
  updateUserStations: vi.fn(),
  resetUserPassword: vi.fn(),
}));

describe("UserFormPage", () => {
  it("exige posto quando acesso total está desativado", async () => {
    const user = userEvent.setup();
    const client = new QueryClient();

    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <UserFormPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    await user.type(screen.getByLabelText("Nome"), "Teste");
    await user.type(screen.getByLabelText("E-mail"), "teste@test.com");
    await user.click(screen.getByRole("button", { name: "Salvar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Selecione ao menos um posto");
  });

  it("desabilita acesso total para não ADMIN", () => {
    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <UserFormPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    const checkbox = screen.getByRole("checkbox", { name: /Acesso total aos postos/i });
    expect(checkbox).toBeDisabled();
  });
});
