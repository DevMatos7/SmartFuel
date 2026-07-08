import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  cancelImportJob,
  confirmImportJob,
  uploadErpProductsImport,
} from "../api/master-data";
import { ErpProductImportPage } from "../pages/ErpProductImportPage";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      stations: [
        { id: "s1", trade_name: "Posto Central", active: true },
        { id: "s2", trade_name: "Posto Norte", active: false },
      ],
    },
  }),
}));

vi.mock("../api/master-data", () => ({
  uploadErpProductsImport: vi.fn(),
  confirmImportJob: vi.fn(),
  cancelImportJob: vi.fn(),
  IMPORT_STATUS_LABELS: {
    READY: "Pronto",
    SUCCESS: "Sucesso",
  },
}));

const mockJob = {
  id: "job1",
  organization_id: "org1",
  station_id: "s1",
  import_type: "ERP_PRODUCTS",
  source_file_name: "produtos.csv",
  source_file_hash: "abc",
  status: "READY",
  records_total: 2,
  records_valid: 2,
  records_inserted: 0,
  records_updated: 0,
  records_unchanged: 0,
  records_failed: 0,
  error_summary: null,
  created_by: "u1",
  created_at: "2026-01-01T00:00:00Z",
  started_at: null,
  finished_at: null,
  rows: [
    {
      id: "r1",
      import_job_id: "job1",
      row_number: 1,
      external_identifier: "ERP-1",
      action: "INSERT",
      status: "VALID",
      raw_data: { code: "1" },
      normalized_data: { code: "1" },
      validation_errors: null,
      processed_at: null,
    },
  ],
};

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <ErpProductImportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ErpProductImportPage", () => {
  beforeEach(() => {
    localStorage.setItem("active_station_id", "s1");
    vi.mocked(uploadErpProductsImport).mockReset();
    vi.mocked(confirmImportJob).mockReset();
    vi.mocked(cancelImportJob).mockReset();
    vi.mocked(uploadErpProductsImport).mockResolvedValue(mockJob);
    vi.mocked(confirmImportJob).mockResolvedValue({ ...mockJob, status: "SUCCESS", records_inserted: 2 });
    vi.mocked(cancelImportJob).mockResolvedValue({ ...mockJob, status: "CANCELLED" });
  });

  it("exibe etapas do fluxo de importação", () => {
    renderPage();
    expect(screen.getByText("1. Posto e arquivo")).toBeInTheDocument();
    expect(screen.getByText("2. Validação")).toBeInTheDocument();
    expect(screen.getByText("3. Pré-visualização")).toBeInTheDocument();
    expect(screen.getByText("4. Conclusão")).toBeInTheDocument();
  });

  it("avança para pré-visualização após upload", async () => {
    const user = userEvent.setup();
    renderPage();

    const file = new File(["code,name\n1,Gasolina"], "produtos.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("Arquivo CSV"), file);
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(screen.getByRole("button", { name: "Enviar e validar" }));

    expect(await screen.findByText("Pronto")).toBeInTheDocument();
    expect(screen.getByText("Total de linhas")).toBeInTheDocument();
    expect(screen.getByText("ERP-1")).toBeInTheDocument();
  });

  it("confirma importação e exibe conclusão", async () => {
    const user = userEvent.setup();
    renderPage();

    const file = new File(["code,name\n1,Gasolina"], "produtos.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("Arquivo CSV"), file);
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(screen.getByRole("button", { name: "Enviar e validar" }));

    await screen.findByText("Confirmar importação");
    await user.click(screen.getByRole("button", { name: "Confirmar importação" }));

    expect(await screen.findByText(/Importação concluída com status/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para produtos ERP" })).toBeInTheDocument();
  });

  it("cancela importação e retorna ao passo inicial", async () => {
    const user = userEvent.setup();
    renderPage();

    const file = new File(["code,name\n1,Gasolina"], "produtos.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("Arquivo CSV"), file);
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(screen.getByRole("button", { name: "Enviar e validar" }));

    await screen.findByText("Confirmar importação");
    await user.click(screen.getByRole("button", { name: "Cancelar" }));

    await waitFor(() => {
      expect(cancelImportJob).toHaveBeenCalledWith("job1");
      expect(screen.getByRole("button", { name: "Continuar" })).toBeInTheDocument();
    });
  });
});
