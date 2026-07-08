import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { RequireAuth } from "../auth/RequireAuth";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: { must_change_password: true },
    loading: false,
  }),
}));

describe("RequireAuth", () => {
  it("bloqueia rotas quando troca de senha é obrigatória", () => {
    render(
      <MemoryRouter initialEntries={["/users"]}>
        <Routes>
          <Route
            path="/users"
            element={
              <RequireAuth>
                <div>Área protegida</div>
              </RequireAuth>
            }
          />
          <Route path="/change-password" element={<div>Troca de senha</div>} />
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByText("Troca de senha")).toBeInTheDocument();
    expect(screen.queryByText("Área protegida")).not.toBeInTheDocument();
  });
});
