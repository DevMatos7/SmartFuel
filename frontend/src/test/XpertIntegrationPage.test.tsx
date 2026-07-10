import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { XpertIntegrationPage } from "../pages/XpertIntegrationPage";

vi.mock("../api/xpert-integration", () => ({
  fetchXpertSummary: vi.fn().mockResolvedValue({
    status: "DISCONNECTED",
    sources_count: 1,
    datasets_enabled: 0,
    pending_products: 2,
    pending_suppliers: 1,
    error_runs: 0,
    last_success_at: null,
    odbc_available: true,
    worker_healthy: true,
    worker_last_heartbeat_at: "2026-07-09T12:00:00Z",
  }),
}));

vi.mock("../api/client", () => ({
  apiFetch: vi.fn().mockImplementation((path: string) => {
    if (path.includes("/sources")) return Promise.resolve([]);
    if (path.includes("/datasets")) return Promise.resolve([]);
    if (path.includes("/sync-runs")) return Promise.resolve({ items: [], total: 0 });
    return Promise.resolve({});
  }),
}));

describe("XpertIntegrationPage", () => {
  it("exibe status ODBC e worker", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <XpertIntegrationPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Integração XPERT")).toBeInTheDocument();
    expect(await screen.findByText("Disponível")).toBeInTheDocument();
    expect(await screen.findByText("Saudável")).toBeInTheDocument();
    expect(await screen.findByText("Checkpoints")).toBeInTheDocument();
  });

  it("exibe worker offline", async () => {
    const { fetchXpertSummary } = await import("../api/xpert-integration");
    vi.mocked(fetchXpertSummary).mockResolvedValueOnce({
      status: "DISCONNECTED",
      sources_count: 0,
      datasets_enabled: 0,
      pending_products: 0,
      pending_suppliers: 0,
      error_runs: 0,
      last_success_at: null,
      odbc_available: true,
      worker_healthy: false,
      worker_last_heartbeat_at: null,
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <XpertIntegrationPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Indisponível")).toBeInTheDocument();
  });

  it("exibe driver ausente", async () => {
    const { fetchXpertSummary } = await import("../api/xpert-integration");
    vi.mocked(fetchXpertSummary).mockResolvedValueOnce({
      status: "MISCONFIGURED",
      sources_count: 0,
      datasets_enabled: 0,
      pending_products: 0,
      pending_suppliers: 0,
      error_runs: 1,
      last_success_at: null,
      odbc_available: false,
      worker_healthy: false,
      worker_last_heartbeat_at: null,
    });
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <XpertIntegrationPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Ausente")).toBeInTheDocument();
  });
});
