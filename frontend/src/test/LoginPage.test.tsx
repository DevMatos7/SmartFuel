import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "../pages/LoginPage";

const loginMock = vi.fn();
const navigateMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    login: loginMock,
  }),
}));

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return {
    ...actual,
    useNavigate: () => navigateMock,
    useLocation: () => ({ state: null }),
  };
});

describe("LoginPage", () => {
  beforeEach(() => {
    loginMock.mockReset();
    navigateMock.mockReset();
  });

  it("envia credenciais válidas", async () => {
    loginMock.mockResolvedValue({ must_change_password: false });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("E-mail"), "admin@test.com");
    await user.type(screen.getByLabelText("Senha"), "SenhaSegura123");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(loginMock).toHaveBeenCalledWith("admin@test.com", "SenhaSegura123");
      expect(navigateMock).toHaveBeenCalledWith("/", { replace: true });
    });
  });

  it("exibe erro de credenciais inválidas", async () => {
    loginMock.mockRejectedValue(new Error("E-mail ou senha inválidos."));
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("E-mail"), "a@b.com");
    await user.type(screen.getByLabelText("Senha"), "errada");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha inválidos.");
  });

  it("redireciona para troca obrigatória de senha", async () => {
    loginMock.mockResolvedValue({ must_change_password: true });
    const user = userEvent.setup();

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>,
    );

    await user.type(screen.getByLabelText("E-mail"), "troca@test.com");
    await user.type(screen.getByLabelText("Senha"), "SenhaSegura123");
    await user.click(screen.getByRole("button", { name: "Entrar" }));

    await waitFor(() => {
      expect(navigateMock).toHaveBeenCalledWith("/change-password");
    });
  });
});
