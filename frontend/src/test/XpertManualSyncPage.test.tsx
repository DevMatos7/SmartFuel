import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { XpertManualSyncPage } from "../pages/XpertManualSyncPage";

const navigateMock = vi.fn();
const createXpertSyncRunsMock = vi.fn();
const hasPermissionMock = vi.fn();

vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual<typeof import("react-router-dom")>("react-router-dom");
  return { ...actual, useNavigate: () => navigateMock };
});

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({ hasPermission: hasPermissionMock }),
}));

vi.mock("../api/xpert-integration", () => ({
  fetchXpertSources: vi.fn().mockResolvedValue([
    { id: "src-1", name: "ATX Matriz", connection_status: "CONNECTED" },
  ]),
  fetchXpertDatasets: vi.fn().mockResolvedValue([
    {
      id: "ds-products",
      code: "PRODUCTS",
      name: "Produtos",
      contract_status: "VALID",
      sync_mode: "FULL_SNAPSHOT_HASH",
    },
    {
      id: "ds-suppliers",
      code: "SUPPLIERS",
      name: "Fornecedores",
      contract_status: "PENDING",
      sync_mode: "FULL_SNAPSHOT_HASH",
    },
    {
      id: "ds-stations",
      code: "STATIONS",
      name: "Filiais",
      contract_status: "MISCONFIGURED",
      sync_mode: "FULL_SNAPSHOT_HASH",
    },
  ]),
  fetchXpertCheckpoints: vi.fn().mockResolvedValue([
    { id: "cp-1", watermark_value: "2026-07-01T00:00:00+00:00" },
  ]),
  fetchXpertRuns: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  createXpertSyncRuns: (...args: unknown[]) => createXpertSyncRunsMock(...args),
}));

vi.mock("../api/stations", () => ({
  fetchStations: vi.fn().mockResolvedValue({
    items: [
      { id: "st-1", trade_name: "Matriz", erp_branch_id: "2443", active: true },
      { id: "st-2", trade_name: "Filial", erp_branch_id: "3001", active: true },
    ],
    total: 2,
  }),
}));

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <XpertManualSyncPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function selectSource() {
  await waitFor(() => expect(screen.getByLabelText("Fonte")).toContainHTML("src-1"));
  await userEvent.selectOptions(screen.getByLabelText("Fonte"), "src-1");
  await waitFor(() => expect(screen.getByLabelText("Dataset")).not.toBeDisabled());
}

describe("XpertManualSyncPage", () => {
  beforeEach(() => {
    navigateMock.mockReset();
    createXpertSyncRunsMock.mockReset();
    createXpertSyncRunsMock.mockResolvedValue({ runs: [{ id: "run-1" }] });
    hasPermissionMock.mockReturnValue(true);
  });

  it("nega acesso sem permissão", () => {
    hasPermissionMock.mockReturnValue(false);
    renderPage();
    expect(screen.getByText(/não possui permissão/i)).toBeInTheDocument();
  });

  it("abre diálogo de confirmação para full", async () => {
    renderPage();
    await selectSource();
    await userEvent.selectOptions(screen.getByLabelText("Dataset"), "PRODUCTS");
    await userEvent.click(screen.getByLabelText(/Matriz/));
    await userEvent.click(screen.getByRole("button", { name: /Iniciar sincronização/i }));
    expect(await screen.findByText(/Confirmar sincronização completa/i)).toBeInTheDocument();
  });

  it("bloqueia dataset sem contrato válido", async () => {
    renderPage();
    await selectSource();
    await userEvent.selectOptions(screen.getByLabelText("Dataset"), "SUPPLIERS");
    await userEvent.click(screen.getByLabelText(/Matriz/));
    expect(screen.getByRole("button", { name: /Iniciar sincronização/i })).toBeDisabled();
    expect(screen.getByText(/Contrato inválido/i)).toBeInTheDocument();
  });

  it("bloqueia STATIONS", async () => {
    renderPage();
    await selectSource();
    const datasetSelect = screen.getByLabelText("Dataset");
    const stationsOption = Array.from(datasetSelect.querySelectorAll("option")).find(
      (o) => o.value === "STATIONS",
    );
    expect(stationsOption).toBeDisabled();
  });

  it("bloqueia incremental sem full anterior", async () => {
    const { fetchXpertRuns } = await import("../api/xpert-integration");
    vi.mocked(fetchXpertRuns).mockResolvedValue({ items: [], total: 0, page: 1, page_size: 1 });
    renderPage();
    await selectSource();
    await userEvent.selectOptions(screen.getByLabelText("Dataset"), "PRODUCTS");
    await userEvent.selectOptions(screen.getByLabelText("Modo de sincronização"), "INCREMENTAL_TIMESTAMP");
    await userEvent.click(screen.getByLabelText(/Matriz/));
    expect(screen.getByRole("button", { name: /Iniciar sincronização/i })).toBeDisabled();
    expect(screen.getByText(/Incremental bloqueado/i)).toBeInTheDocument();
  });

  it("cria runs para vários postos após confirmação", async () => {
    renderPage();
    await selectSource();
    await userEvent.selectOptions(screen.getByLabelText("Dataset"), "PRODUCTS");
    await userEvent.click(screen.getByLabelText(/Matriz/));
    await userEvent.click(screen.getByLabelText(/Filial/));
    await userEvent.click(screen.getByRole("button", { name: /Iniciar sincronização/i }));
    await userEvent.click(await screen.findByRole("button", { name: /^Confirmar$/i }));
    await waitFor(() => expect(createXpertSyncRunsMock).toHaveBeenCalled());
    expect(createXpertSyncRunsMock.mock.calls[0][0].station_ids).toEqual(["st-1", "st-2"]);
    expect(navigateMock).toHaveBeenCalledWith("/integrations/xpert/runs");
  });

  it("exibe erro na criação", async () => {
    createXpertSyncRunsMock.mockRejectedValueOnce(new Error("Falha ao enfileirar"));
    renderPage();
    await selectSource();
    await userEvent.selectOptions(screen.getByLabelText("Dataset"), "PRODUCTS");
    await userEvent.click(screen.getByLabelText(/Matriz/));
    await userEvent.click(screen.getByRole("button", { name: /Iniciar sincronização/i }));
    await userEvent.click(await screen.findByRole("button", { name: /^Confirmar$/i }));
    expect(await screen.findByText("Falha ao enfileirar")).toBeInTheDocument();
  });
});
