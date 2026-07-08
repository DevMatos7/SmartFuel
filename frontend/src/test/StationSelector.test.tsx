import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { StationSelector } from "../components/StationSelector";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      stations: [
        { id: "s1", trade_name: "Matriz", station_type: "HEADQUARTERS", active: true },
        { id: "s2", trade_name: "Filial", station_type: "BRANCH", active: true },
      ],
    },
  }),
}));

describe("StationSelector", () => {
  it("lista postos autorizados e persiste seleção", () => {
    localStorage.clear();
    render(
      <MemoryRouter>
        <StationSelector />
      </MemoryRouter>,
    );

    const select = screen.getByLabelText("Selecionar posto ativo") as HTMLSelectElement;
    expect(select.options.length).toBeGreaterThan(1);
    expect(screen.getByText(/Matriz/)).toBeInTheDocument();
    expect(localStorage.getItem("active_station_id")).toBeTruthy();
  });
});
