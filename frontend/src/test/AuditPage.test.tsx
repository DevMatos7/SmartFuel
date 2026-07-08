import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { AuditPage } from "../pages/AuditPage";

vi.mock("../api/audit", () => ({
  fetchAuditLogs: vi.fn().mockResolvedValue({
    items: [
      {
        id: "1",
        organization_id: "org",
        user_id: "u1",
        entity_type: "station",
        entity_id: "s1",
        action: "create",
        before_data: null,
        after_data: { trade_name: "Posto" },
        metadata: null,
        ip_address: "127.0.0.1",
        request_id: "req-1",
        created_at: "2026-01-01T12:00:00Z",
      },
    ],
    total: 1,
    page: 1,
    page_size: 20,
  }),
}));

describe("AuditPage", () => {
  it("renderiza registros e detalhes", async () => {
    const client = new QueryClient();
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <AuditPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );

    expect(await screen.findByText("station")).toBeInTheDocument();
    expect(screen.getByText("req-1")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Ver" })).toBeInTheDocument();
    });
  });
});
