import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";
import { XpertCheckpointsPage } from "../pages/XpertCheckpointsPage";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: (p: string) => p === "erp_sync.reset_checkpoint" || p === "erp_integration.read",
  }),
}));

vi.mock("../api/xpert-integration", () => ({
  fetchXpertCheckpoints: vi.fn().mockResolvedValue([
    {
      id: "cp-1",
      erp_source_id: "src-1",
      erp_dataset_id: "ds-1",
      station_id: null,
      checkpoint_type: "TIMESTAMP",
      watermark_value: "2026-07-09T10:00:00+00:00",
      source_upper_bound: "2026-07-09T12:00:00+00:00",
      last_success_at: "2026-07-09T12:00:00+00:00",
    },
  ]),
  fetchXpertSources: vi.fn().mockResolvedValue([{ id: "src-1", name: "ATX Matriz" }]),
  fetchXpertDatasets: vi.fn().mockResolvedValue([{ id: "ds-1", code: "PRODUCTS" }]),
  resetXpertCheckpoint: vi.fn().mockResolvedValue({}),
}));

describe("XpertCheckpointsPage", () => {
  it("lista checkpoints e exibe diálogo de reset", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <XpertCheckpointsPage />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(await screen.findByText("Checkpoints XPERT")).toBeInTheDocument();
    expect(await screen.findByText("Global")).toBeInTheDocument();
    await userEvent.click(screen.getByText("Reset"));
    expect(await screen.findByText("Reset de checkpoint")).toBeInTheDocument();
  });
});
