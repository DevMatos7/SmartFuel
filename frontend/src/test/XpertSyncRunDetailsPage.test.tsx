import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { XpertSyncRunDetailsPage } from "../pages/XpertSyncRunDetailsPage";

const cancelMock = vi.fn();
const retryMock = vi.fn();
const fetchRunMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: (p: string) =>
      ["erp_sync.read", "erp_sync.cancel", "erp_sync.retry", "erp_sync.view_errors", "erp_sync.view_staging"].includes(p),
  }),
}));

vi.mock("../api/xpert-integration", () => ({
  fetchXpertRun: (...args: unknown[]) => fetchRunMock(...args),
  fetchXpertRunErrors: vi.fn().mockResolvedValue([]),
  fetchXpertRunStaging: vi.fn().mockResolvedValue([]),
  cancelXpertRun: (...args: unknown[]) => cancelMock(...args),
  retryXpertRun: (...args: unknown[]) => retryMock(...args),
}));

function renderPage(runId = "run-1") {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[`/integrations/xpert/runs/${runId}`]}>
        <Routes>
          <Route path="/integrations/xpert/runs/:runId" element={<XpertSyncRunDetailsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("XpertSyncRunDetailsPage", () => {
  beforeEach(() => {
    cancelMock.mockReset();
    retryMock.mockReset();
    fetchRunMock.mockResolvedValue({
      id: "run-1",
      status: "FAILED",
      sync_mode: "FULL_SNAPSHOT_HASH",
      trigger_type: "MANUAL",
      rows_read: 1,
      rows_applied: 0,
      rows_error: 1,
      rows_quarantined: 0,
      error_code: "FAILED_WORKER_LOST",
      error_message: "Worker perdido",
      started_at: null,
      finished_at: "2026-07-09T12:00:00Z",
      created_at: "2026-07-09T12:00:00Z",
      checkpoint_before: null,
      checkpoint_after: null,
    });
    retryMock.mockResolvedValue({ runs: [{ id: "run-2" }] });
  });

  it("exibe run abandonada", async () => {
    renderPage();
    expect(await screen.findByText(/abandonada pelo worker/i)).toBeInTheDocument();
  });

  it("permite cancelamento em run ativa", async () => {
    fetchRunMock.mockResolvedValue({
      id: "run-1",
      status: "EXTRACTING",
      sync_mode: "FULL_SNAPSHOT_HASH",
      trigger_type: "MANUAL",
      rows_read: 5,
      rows_applied: 0,
      rows_error: 0,
      rows_quarantined: 0,
      error_code: null,
      error_message: null,
      started_at: "2026-07-09T12:00:00Z",
      finished_at: null,
      created_at: "2026-07-09T12:00:00Z",
      checkpoint_before: null,
      checkpoint_after: null,
    });
    renderPage();
    const cancelBtn = await screen.findByRole("button", { name: /Cancelar/i });
    await userEvent.click(cancelBtn);
    expect(cancelMock).toHaveBeenCalledWith("run-1");
  });

  it("permite retry em run falha", async () => {
    renderPage();
    const retryBtn = await screen.findByRole("button", { name: /Repetir/i });
    await userEvent.click(retryBtn);
    expect(retryMock).toHaveBeenCalledWith("run-1");
  });
});
