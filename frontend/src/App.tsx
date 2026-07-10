import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./auth/AuthProvider";
import { RequireAuth } from "./auth/RequireAuth";
import { RequirePermission } from "./auth/RequirePermission";
import { AuthenticatedLayout } from "./layouts/AuthenticatedLayout";
import { AuditPage } from "./pages/AuditPage";
import { ChangePasswordPage } from "./pages/ChangePasswordPage";
import { ForbiddenPage } from "./pages/ForbiddenPage";
import { HealthBoard } from "./pages/HealthBoard";
import { HomePage } from "./pages/HomePage";
import { LoginPage } from "./pages/LoginPage";
import { OrganizationPage } from "./pages/OrganizationPage";
import { ProfilePage } from "./pages/ProfilePage";
import { DistributorDetailsPage } from "./pages/DistributorDetailsPage";
import { DistributorsPage } from "./pages/DistributorsPage";
import { ErpProductImportPage } from "./pages/ErpProductImportPage";
import { ErpProductsPage } from "./pages/ErpProductsPage";
import { ErpSupplierImportPage } from "./pages/ErpSupplierImportPage";
import { PaymentTermsPage } from "./pages/PaymentTermsPage";
import { ProductFormPage } from "./pages/ProductFormPage";
import { ProductsPage } from "./pages/ProductsPage";
import { QuoteComparisonDetailsPage } from "./pages/QuoteComparisonDetailsPage";
import { QuoteComparisonHistoryPage } from "./pages/QuoteComparisonHistoryPage";
import { QuoteComparisonPage } from "./pages/QuoteComparisonPage";
import { FinancialParametersPage } from "./pages/FinancialParametersPage";
import { QuoteDetailsPage } from "./pages/QuoteDetailsPage";
import { QuoteFormPage } from "./pages/QuoteFormPage";
import { QuotesPage } from "./pages/QuotesPage";
import { SupplierRulesPage } from "./pages/SupplierRulesPage";
import { StationFormPage } from "./pages/StationFormPage";
import { StationsPage } from "./pages/StationsPage";
import { UserFormPage } from "./pages/UserFormPage";
import { UsersPage } from "./pages/UsersPage";
import { XpertIntegrationPage } from "./pages/XpertIntegrationPage";
import { XpertDatasetsPage, XpertSourcePage } from "./pages/XpertAdminPages";
import { XpertManualSyncPage } from "./pages/XpertManualSyncPage";
import { XpertCheckpointsPage } from "./pages/XpertCheckpointsPage";
import { XpertSyncRunsPage } from "./pages/XpertSyncRunsPage";
import { XpertSyncRunDetailsPage } from "./pages/XpertSyncRunDetailsPage";
import { FuelSalesDashboardPage } from "./pages/FuelSalesDashboardPage";
import { FuelSalesDataQualityPage } from "./pages/FuelSalesDataQualityPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/change-password"
            element={
              <RequireAuth>
                <div className="min-h-screen bg-slate-50 px-4 py-8">
                  <ChangePasswordPage />
                </div>
              </RequireAuth>
            }
          />
          <Route
            element={
              <RequireAuth>
                <AuthenticatedLayout />
              </RequireAuth>
            }
          >
            <Route index element={<HomePage />} />
            <Route
              path="organization"
              element={
                <RequirePermission permission="organizations.read">
                  <OrganizationPage />
                </RequirePermission>
              }
            />
            <Route
              path="stations"
              element={
                <RequirePermission permission="stations.read">
                  <StationsPage />
                </RequirePermission>
              }
            />
            <Route
              path="stations/new"
              element={
                <RequirePermission permission="stations.write">
                  <StationFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="stations/:stationId"
              element={
                <RequirePermission permission="stations.write">
                  <StationFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="users"
              element={
                <RequirePermission permission="users.read">
                  <UsersPage />
                </RequirePermission>
              }
            />
            <Route
              path="users/new"
              element={
                <RequirePermission permission="users.write">
                  <UserFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="users/:userId"
              element={
                <RequirePermission permission="users.write">
                  <UserFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="audit"
              element={
                <RequirePermission permission="audit.read">
                  <AuditPage />
                </RequirePermission>
              }
            />
            <Route
              path="products"
              element={
                <RequirePermission permission="products.read">
                  <ProductsPage />
                </RequirePermission>
              }
            />
            <Route
              path="products/new"
              element={
                <RequirePermission permission="products.write">
                  <ProductFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="products/:productId"
              element={
                <RequirePermission permission="products.write">
                  <ProductFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="erp-products"
              element={
                <RequirePermission permission="erp_products.read">
                  <ErpProductsPage />
                </RequirePermission>
              }
            />
            <Route
              path="erp-products/import"
              element={
                <RequirePermission permission="erp_products.import">
                  <ErpProductImportPage />
                </RequirePermission>
              }
            />
            <Route
              path="erp-suppliers/import"
              element={
                <RequirePermission permission="master_data_imports.execute">
                  <ErpSupplierImportPage />
                </RequirePermission>
              }
            />
            <Route
              path="distributors"
              element={
                <RequirePermission permission="distributors.read">
                  <DistributorsPage />
                </RequirePermission>
              }
            />
            <Route
              path="distributors/new"
              element={
                <RequirePermission permission="distributors.write">
                  <DistributorDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="distributors/:distributorId"
              element={
                <RequirePermission permission="distributors.read">
                  <DistributorDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="payment-terms"
              element={
                <RequirePermission permission="payment_terms.read">
                  <PaymentTermsPage />
                </RequirePermission>
              }
            />
            <Route
              path="supplier-rules"
              element={
                <RequirePermission permission="supplier_rules.read">
                  <SupplierRulesPage />
                </RequirePermission>
              }
            />
            <Route
              path="quotes"
              element={
                <RequirePermission permission="quotes.read">
                  <QuotesPage />
                </RequirePermission>
              }
            />
            <Route
              path="quote-comparisons"
              element={
                <RequirePermission permission="quote_comparisons.run">
                  <QuoteComparisonPage />
                </RequirePermission>
              }
            />
            <Route
              path="quote-comparisons/history"
              element={
                <RequirePermission permission="quote_comparisons.read">
                  <QuoteComparisonHistoryPage />
                </RequirePermission>
              }
            />
            <Route
              path="quote-comparisons/:runId"
              element={
                <RequirePermission permission="quote_comparisons.read">
                  <QuoteComparisonDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="financial-parameters"
              element={
                <RequirePermission permission="financial_parameters.read">
                  <FinancialParametersPage />
                </RequirePermission>
              }
            />
            <Route
              path="quotes/new"
              element={
                <RequirePermission permission="quotes.write">
                  <QuoteFormPage />
                </RequirePermission>
              }
            />
            <Route
              path="quotes/:quoteId"
              element={
                <RequirePermission permission="quotes.read">
                  <QuoteDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="integrations/xpert"
              element={
                <RequirePermission permission="erp_integration.read">
                  <XpertIntegrationPage />
                </RequirePermission>
              }
            />
            <Route
              path="integrations/xpert/source"
              element={
                <RequirePermission permission="erp_integration.read">
                  <XpertSourcePage />
                </RequirePermission>
              }
            />
            <Route
              path="integrations/xpert/datasets"
              element={
                <RequirePermission permission="erp_integration.read">
                  <XpertDatasetsPage />
                </RequirePermission>
              }
            />
            <Route
              path="integrations/xpert/checkpoints"
              element={
                <RequirePermission permission="erp_sync.read">
                  <XpertCheckpointsPage />
                </RequirePermission>
              }
            />
            <Route
              path="integrations/xpert/sync"
              element={
                <RequirePermission permission="erp_sync.run">
                  <XpertManualSyncPage />
                </RequirePermission>
              }
            />
            <Route
              path="integrations/xpert/runs"
              element={
                <RequirePermission permission="erp_sync.read">
                  <XpertSyncRunsPage />
                </RequirePermission>
              }
            />
            <Route
              path="integrations/xpert/runs/:runId"
              element={
                <RequirePermission permission="erp_sync.read">
                  <XpertSyncRunDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-sales"
              element={
                <RequirePermission permission="fuel_sales_analytics.read">
                  <FuelSalesDashboardPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-sales/quality"
              element={
                <RequirePermission permission="fuel_sales_data_quality.read">
                  <FuelSalesDataQualityPage />
                </RequirePermission>
              }
            />
            <Route path="profile" element={<ProfilePage />} />
            <Route path="health" element={<HealthBoard />} />
            <Route path="forbidden" element={<ForbiddenPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
