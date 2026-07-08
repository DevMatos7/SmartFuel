import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { ForbiddenPage } from "../pages/ForbiddenPage";

describe("ForbiddenPage", () => {
  it("exibe mensagem de acesso negado", () => {
    render(
      <MemoryRouter>
        <ForbiddenPage />
      </MemoryRouter>,
    );
    expect(screen.getByText(/Você não possui permissão/i)).toBeInTheDocument();
  });
});
