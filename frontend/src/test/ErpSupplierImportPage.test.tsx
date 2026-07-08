import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  cancelImportJob,
  confirmImportJob,
  uploadErpSuppliersImport,
} from "../api/master-data";
import { ErpSupplierImportPage } from "../pages/ErpSupplierImportPage";

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      stations: [{ id: "s1", trade_name: "Posto Central", active: true }],
    },
  }),
}));

vi.mock("../api/master-data", () => ({
  uploadErpSuppliersImport: vi.fn(),
  confirmImportJob: vi.fn(),
  cancelImportJob: vi.fn(),
  IMPORT_STATUS_LABELS: {
    READY: "Pronto",
    SUCCESS: "Sucesso",
  },
}));

const mockJob = {
  id: "job-sup1",
  organization_id: "org1",
  station_id: "s1",
  import_type: "ERP_SUPPLIERS",
  source_file_name: "fornecedores.csv",
  source_file_hash: "def",
  status: "READY",
  records_total: 1,
  records_valid: 1,
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
      import_job_id: "job-sup1",
      row_number: 1,
      external_identifier: "FORN-1",
      action: "INSERT",
      status: "VALID",
      raw_data: { name: "Distribuidora X" },
      normalized_data: { name: "Distribuidora X" },
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
        <ErpSupplierImportPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ErpSupplierImportPage", () => {
  beforeEach(() => {
    localStorage.setItem("active_station_id", "s1");
    vi.mocked(uploadErpSuppliersImport).mockReset();
    vi.mocked(confirmImportJob).mockReset();
    vi.mocked(cancelImportJob).mockReset();
    vi.mocked(uploadErpSuppliersImport).mockResolvedValue(mockJob);
    vi.mocked(confirmImportJob).mockResolvedValue({ ...mockJob, status: "SUCCESS", records_inserted: 1 });
    vi.mocked(cancelImportJob).mockResolvedValue({ ...mockJob, status: "CANCELLED" });
  });

  it("exibe instruções de colunas do CSV", () => {
    renderPage();
    expect(screen.getByText(/erp_entity_id, erp_entity_code, erp_name, erp_cnpj/)).toBeInTheDocument();
  });

  it("executa fluxo completo de importação de fornecedores", async () => {
    const user = userEvent.setup();
    renderPage();

    const file = new File(["erp_entity_id,erp_name\n1,Fornecedor"], "fornecedores.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("Arquivo CSV"), file);
    await user.click(screen.getByRole("button", { name: "Continuar" }));
    await user.click(screen.getByRole("button", { name: "Enviar e validar" }));

    expect(await screen.findByText("FORN-1")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Confirmar importação" }));

    expect(await screen.findByText(/Importação concluída com status/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir para distribuidoras" })).toBeInTheDocument();

    await waitFor(() => {
      expect(confirmImportJob).toHaveBeenCalledWith("job-sup1");
    });
  });
});
