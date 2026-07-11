import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { StationSelector } from "../components/StationSelector";

const analyticsItems = [
  { to: "/analytics/fuel-sales", label: "Vendas de combustíveis", permission: "fuel_sales_analytics.read" },
  { to: "/analytics/fuel-sales/margins", label: "Margens combustíveis", permission: "fuel_sales_analytics.view_margin" },
  { to: "/analytics/fuel-sales/prices", label: "Preços combustíveis", permission: "fuel_sales_analytics.read" },
  { to: "/analytics/fuel-sales/quality", label: "Qualidade vendas", permission: "fuel_sales_data_quality.read" },
  { to: "/analytics/fuel-purchases", label: "Compras", permission: "fuel_purchases.read" },
  { to: "/analytics/purchase-benchmarks", label: "Compra × cotação", permission: "purchase_benchmarks.read" },
  { to: "/analytics/purchase-benchmarks/opportunities", label: "Oportunidades de compra", permission: "purchase_benchmarks.view_opportunity" },
  { to: "/analytics/accounts-payable", label: "Contas a pagar", permission: "accounts_payable.read" },
  { to: "/analytics/fuel-purchases/quality", label: "Qualidade compras", permission: "purchase_data_quality.read" },
  { to: "/analytics/purchase-benchmarks/quality", label: "Qualidade benchmark", permission: "purchase_benchmarks.read" },
  { to: "/analytics/nfe-documents", label: "NF-e", permission: "nfe_documents.read" },
  { to: "/analytics/external-indices", label: "Índices externos", permission: "external_data.read" },
  { to: "/analytics/external-indices/quality", label: "Qualidade índices", permission: "external_data.read" },
  { to: "/analytics/market-correlation", label: "Correlação e defasagem", permission: "market_analysis.read" },
  { to: "/analytics/market-correlation/quality", label: "Qualidade estatística", permission: "market_analysis.read" },
  { to: "/pricing", label: "Precificação", permission: "pricing.read" },
  { to: "/pricing/approvals", label: "Aprovações de preço", permission: "pricing.read" },
  { to: "/pricing/quality", label: "Qualidade precificação", permission: "pricing.read" },
  { to: "/executive", label: "Visão executiva", permission: "executive_dashboard.read" },
  { to: "/executive/alerts", label: "Central de alertas", permission: "alerts.read" },
  { to: "/executive/readiness", label: "Prontidão", permission: "operations.view_readiness" },
];

const navItems = [
  { to: "/", label: "Início", permission: "dashboard.read" },
  { to: "/quotes", label: "Cotações", permission: "quotes.read" },
  { to: "/quotes/ai", label: "Importar com IA", permission: "quote_ingestion.read" },
  { to: "/quote-comparisons", label: "Comparar cotações", permission: "quote_comparisons.run" },
  { to: "/quote-comparisons/history", label: "Histórico comparações", permission: "quote_comparisons.read" },
  { to: "/organization", label: "Organização", permission: "organizations.read" },
  { to: "/stations", label: "Postos", permission: "stations.read" },
  { to: "/users", label: "Usuários", permission: "users.read" },
  { to: "/audit", label: "Auditoria", permission: "audit.read" },
  { to: "/integrations/xpert", label: "Integração XPERT", permission: "erp_integration.read" },
  { to: "/profile", label: "Perfil", permission: "dashboard.read" },
];

const cadastrosItems = [
  { to: "/products", label: "Produtos", permission: "products.read" },
  { to: "/erp-products", label: "Produtos ERP", permission: "erp_products.read" },
  { to: "/erp-products/import", label: "Importar produtos ERP", permission: "erp_products.import" },
  { to: "/erp-suppliers/import", label: "Importar fornecedores ERP", permission: "master_data_imports.execute" },
  { to: "/distributors", label: "Distribuidores", permission: "distributors.read" },
  { to: "/payment-terms", label: "Prazos de pagamento", permission: "payment_terms.read" },
  { to: "/supplier-rules", label: "Regras de fornecimento", permission: "supplier_rules.read" },
  { to: "/financial-parameters", label: "Parâmetros financeiros", permission: "financial_parameters.read" },
];

export function AuthenticatedLayout() {
  const { user, logout, hasPermission } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [cadastrosOpen, setCadastrosOpen] = useState(false);

  const visibleCadastros = useMemo(
    () => cadastrosItems.filter((item) => hasPermission(item.permission)),
    [hasPermission],
  );

  const visibleAnalytics = useMemo(
    () => analyticsItems.filter((item) => hasPermission(item.permission)),
    [hasPermission],
  );

  const isCadastrosActive = useMemo(
    () => visibleCadastros.some((item) => location.pathname.startsWith(item.to.split("/import")[0])),
    [location.pathname, visibleCadastros],
  );

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (isCadastrosActive) setCadastrosOpen(true);
  }, [isCadastrosActive]);

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3">
          <div className="flex items-center gap-3">
            <button
              type="button"
              className="rounded border border-slate-300 px-2 py-1 text-sm md:hidden"
              onClick={() => setMenuOpen((v) => !v)}
              aria-label="Abrir menu"
            >
              Menu
            </button>
            <div>
              <p className="font-semibold">Inteligência Auto Postos</p>
              <p className="text-xs text-slate-500">{user?.organization.name}</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <StationSelector />
            <div className="hidden text-right text-sm sm:block">
              <p className="font-medium">{user?.name}</p>
              <p className="text-xs text-slate-500">{user?.roles.join(", ")}</p>
            </div>
            <button
              type="button"
              className="rounded bg-slate-900 px-3 py-2 text-sm text-white"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Sair
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto flex max-w-7xl gap-6 px-4 py-6">
        <aside
          className={`${menuOpen ? "block" : "hidden"} w-full shrink-0 md:block md:w-56`}
          aria-label="Menu principal"
        >
          <nav className="space-y-1 rounded-lg border border-slate-200 bg-white p-2">
            {navItems
              .filter((item) => hasPermission(item.permission))
              .map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === "/"}
                  className={({ isActive }) =>
                    `block rounded px-3 py-2 text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"}`
                  }
                >
                  {item.label}
                </NavLink>
              ))}

            {visibleAnalytics.length > 0 && (
              <div className="pt-2">
                <p className="px-3 py-1 text-xs font-semibold uppercase tracking-wide text-slate-400">Análises</p>
                {visibleAnalytics.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `block rounded px-3 py-2 text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"}`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
              </div>
            )}

            {visibleCadastros.length > 0 && (
              <div className="pt-1">
                <button
                  type="button"
                  className={`flex w-full items-center justify-between rounded px-3 py-2 text-sm ${
                    isCadastrosActive ? "bg-slate-100 font-medium text-slate-900" : "text-slate-700 hover:bg-slate-100"
                  }`}
                  onClick={() => setCadastrosOpen((v) => !v)}
                  aria-expanded={cadastrosOpen}
                >
                  Cadastros
                  <span className="text-xs">{cadastrosOpen ? "▾" : "▸"}</span>
                </button>
                {cadastrosOpen && (
                  <div className="ml-2 mt-1 space-y-1 border-l border-slate-200 pl-2">
                    {visibleCadastros.map((item) => (
                      <NavLink
                        key={item.to}
                        to={item.to}
                        className={({ isActive }) =>
                          `block rounded px-3 py-1.5 text-sm ${isActive ? "bg-slate-900 text-white" : "text-slate-700 hover:bg-slate-100"}`
                        }
                      >
                        {item.label}
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            )}

            <Link to="/health" className="block rounded px-3 py-2 text-sm text-slate-700 hover:bg-slate-100">
              Saúde do sistema
            </Link>
          </nav>
        </aside>

        <main className="min-w-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
