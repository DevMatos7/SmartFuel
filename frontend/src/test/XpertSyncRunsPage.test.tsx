import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { XpertSyncRunsPage } from "../pages/XpertSyncRunsPage";

const fetchXpertRunsMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("../api/xpert-integration", () => ({
  fetchXpertSources: vi.fn().mockResolvedValue([{ id: "src-1", name: "ATX" }]),
  fetchXpertDatasets: vi.fn().mockResolvedValue([{ id: "ds-1", code: "PRODUCTS" }]),
  fetchXpertRuns: (...args: unknown[]) => fetchXpertRunsMock(...args),
  cancelXpertRun: vi.fn(),
  retryXpertRun: vi.fn(),
}));

vi.mock("../api/stations", () => ({
  fetchStations: vi.fn().mockResolvedValue({
    items: [{ id: "st-1", trade_name: "Matriz" }],
    total: 1,
  }),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <XpertSyncRunsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("XpertSyncRunsPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockImplementation((p: string) =>
      ["erp_sync.read", "erp_sync.run", "erp_sync.cancel", "erp_sync.retry"].includes(p),
    );
    fetchXpertRunsMock.mockResolvedValue({
      items: [
        {
          id: "run-active",
          erp_source_id: "src-1",
          erp_dataset_id: "ds-1",
          station_id: "st-1",
          status: "EXTRACTING",
          sync_mode: "FULL_SNAPSHOT_HASH",
          trigger_type: "MANUAL",
          rows_read: 10,
          rows_applied: 0,
          rows_error: 0,
          rows_quarantined: 0,
          started_at: "2026-07-09T12:00:00Z",
          finished_at: null,
          created_at: "2026-07-09T12:00:00Z",
          checkpoint_before: null,
          checkpoint_after: null,
          error_code: null,
          error_message: null,
        },
        {
          id: "run-partial",
          erp_source_id: "src-1",
          erp_dataset_id: "ds-1",
          station_id: "st-1",
          status: "PARTIAL",
          sync_mode: "FULL_SNAPSHOT_HASH",
          trigger_type: "MANUAL",
          rows_read: 100,
          rows_applied: 90,
          rows_error: 2,
          rows_quarantined: 8,
          started_at: "2026-07-08T12:00:00Z",
          finished_at: "2026-07-08T12:30:00Z",
          created_at: "2026-07-08T12:00:00Z",
          checkpoint_before: null,
          checkpoint_after: null,
          error_code: null,
          error_message: null,
        },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    });
  });

  it("renderiza lista paginada", async () => {
    renderPage();
    expect(await screen.findByText("EXTRACTING")).toBeInTheDocument();
    expect(await screen.findByText(/2 execuções/)).toBeInTheDocument();
  });

  it("aplica filtro de status", async () => {
    renderPage();
    await screen.findByText("EXTRACTING");
    await userEvent.selectOptions(screen.getByDisplayValue("Todos os status"), "PARTIAL");
    await waitFor(() =>
      expect(fetchXpertRunsMock).toHaveBeenCalledWith(
        expect.objectContaining({ status: "PARTIAL", page: "1" }),
      ),
    );
  });

  it("marca run ativa na lista", async () => {
    renderPage();
    expect(await screen.findByText(/EXTRACTING ●/)).toBeInTheDocument();
  });

  it("exibe run parcial", async () => {
    renderPage();
    expect(await screen.findByText("PARTIAL")).toBeInTheDocument();
  });

  it("oculta botão de nova sync sem permissão", async () => {
    hasPermissionMock.mockImplementation((p: string) => p === "erp_sync.read");
    renderPage();
    await screen.findByText("Execuções XPERT");
    expect(screen.queryByText("Nova sincronização")).not.toBeInTheDocument();
  });
});
