import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPaymentTerm, fetchPaymentTerms } from "../api/master-data";
import { PaymentTermsPage } from "../pages/PaymentTermsPage";

const hasPermissionMock = vi.fn();

vi.mock("../auth/AuthProvider", () => ({
  useAuth: () => ({
    hasPermission: hasPermissionMock,
  }),
}));

vi.mock("../api/master-data", () => ({
  fetchPaymentTerms: vi.fn(),
  createPaymentTerm: vi.fn(),
  updatePaymentTerm: vi.fn(),
  deactivatePaymentTerm: vi.fn(),
  reactivatePaymentTerm: vi.fn(),
  PAYMENT_TYPE_LABELS: {
    CASH: "À vista",
    TERM: "Prazo",
    ANTICIPATED: "Antecipado",
  },
}));

const mockTerms = [
  {
    id: "t1",
    organization_id: "org1",
    code: "AV",
    name: "À vista",
    normalized_name: "À VISTA",
    payment_type: "CASH",
    days: 0,
    description: null,
    active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "t2",
    organization_id: "org1",
    code: "P30",
    name: "30 dias",
    normalized_name: "30 DIAS",
    payment_type: "TERM",
    days: 30,
    description: "Prazo padrão",
    active: true,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  },
];

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <PaymentTermsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PaymentTermsPage", () => {
  beforeEach(() => {
    hasPermissionMock.mockReset();
    hasPermissionMock.mockReturnValue(true);
    vi.mocked(fetchPaymentTerms).mockReset();
    vi.mocked(createPaymentTerm).mockReset();
    vi.mocked(fetchPaymentTerms).mockResolvedValue({
      items: mockTerms,
      total: 2,
      page: 1,
      page_size: 20,
    });
  });

  it("exibe tipos à vista e a prazo na listagem", async () => {
    renderPage();
    expect(await screen.findByText("30 dias")).toBeInTheDocument();
    expect(screen.getAllByRole("cell", { name: "À vista" }).length).toBeGreaterThan(0);
    expect(screen.getByRole("cell", { name: "Prazo" })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: "30" })).toBeInTheDocument();
  });

  it("exibe opções de tipo à vista e a prazo no formulário", async () => {
    const user = userEvent.setup();
    renderPage();

    await screen.findByText("Prazos de pagamento");
    const typeSelects = screen.getAllByRole("combobox");
    const formTypeSelect = typeSelects[typeSelects.length - 1];
    expect(formTypeSelect).toHaveTextContent("À vista");
    expect(formTypeSelect).toHaveTextContent("Prazo");

    await user.selectOptions(formTypeSelect, "CASH");
    expect(formTypeSelect).toHaveValue("CASH");
  });
});
