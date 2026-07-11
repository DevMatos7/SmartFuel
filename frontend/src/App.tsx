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
import { FuelMarginsPage } from "./pages/FuelMarginsPage";
import { FuelPricesPage } from "./pages/FuelPricesPage";
import { FuelPurchasesDashboardPage } from "./pages/FuelPurchasesDashboardPage";
import { FuelPurchaseInvoicesPage } from "./pages/FuelPurchaseInvoicesPage";
import { FuelPurchaseInvoiceDetailsPage } from "./pages/FuelPurchaseInvoiceDetailsPage";
import { FuelPurchaseCostsPage } from "./pages/FuelPurchaseCostsPage";
import { AccountsPayablePage } from "./pages/AccountsPayablePage";
import { PurchaseDataQualityPage } from "./pages/PurchaseDataQualityPage";
import { PurchaseBenchmarkDashboardPage } from "./pages/PurchaseBenchmarkDashboardPage";
import { PurchaseBenchmarkDataQualityPage } from "./pages/PurchaseBenchmarkDataQualityPage";
import { PurchaseBenchmarkOpportunitiesPage } from "./pages/PurchaseBenchmarkOpportunitiesPage";
import { PurchaseBenchmarkRunDetailsPage } from "./pages/PurchaseBenchmarkRunDetailsPage";
import { NfeDocumentsPage } from "./pages/NfeDocumentsPage";
import { ExternalIndicesDashboardPage } from "./pages/ExternalIndicesDashboardPage";
import { ExternalSeriesPage } from "./pages/ExternalSeriesPage";
import { ExternalSeriesDetailsPage } from "./pages/ExternalSeriesDetailsPage";
import { ExternalDataSourcesPage } from "./pages/ExternalDataSourcesPage";
import { ExternalImportsPage } from "./pages/ExternalImportsPage";
import { ExternalIngestionRunsPage } from "./pages/ExternalIngestionRunsPage";
import { ExternalDataQualityPage } from "./pages/ExternalDataQualityPage";
import { MarketCorrelationDashboardPage } from "./pages/MarketCorrelationDashboardPage";
import { MarketAnalysisRunDetailsPage } from "./pages/MarketAnalysisRunDetailsPage";
import { MarketAnalysisQualityPage } from "./pages/MarketAnalysisQualityPage";
import { MarketAnalysisParametersPage } from "./pages/MarketAnalysisParametersPage";
import { PricingDashboardPage } from "./pages/PricingDashboardPage";
import { CurrentMarginsPage } from "./pages/CurrentMarginsPage";
import { PricingRecommendationsPage } from "./pages/PricingRecommendationsPage";
import { PricingRecommendationDetailsPage } from "./pages/PricingRecommendationDetailsPage";
import { PricingApprovalQueuePage } from "./pages/PricingApprovalQueuePage";
import { PricingDecisionDetailsPage } from "./pages/PricingDecisionDetailsPage";
import { PricingImplementationsPage } from "./pages/PricingImplementationsPage";
import { PricingPoliciesPage } from "./pages/PricingPoliciesPage";
import { PricingDataQualityPage } from "./pages/PricingDataQualityPage";
import { ExecutiveDashboardPage } from "./pages/ExecutiveDashboardPage";
import { ExecutiveStationDetailsPage } from "./pages/ExecutiveStationDetailsPage";
import { AlertsCenterPage } from "./pages/AlertsCenterPage";
import { AlertDetailsPage } from "./pages/AlertDetailsPage";
import { AlertRulesPage } from "./pages/AlertRulesPage";
import { NotificationPoliciesPage } from "./pages/NotificationPoliciesPage";
import { OperationsHealthPage } from "./pages/OperationsHealthPage";
import { OperationalJobsPage } from "./pages/OperationalJobsPage";
import { OperationalSloPage } from "./pages/OperationalSloPage";
import { OperationalIncidentsPage } from "./pages/OperationalIncidentsPage";
import { DataQualityOverviewPage } from "./pages/DataQualityOverviewPage";
import { ProductionReadinessPage } from "./pages/ProductionReadinessPage";
import { QuoteAiImportPage } from "./pages/QuoteAiImportPage";
import { QuoteIngestionReviewPage } from "./pages/QuoteIngestionReviewPage";
import { QuoteIngestionBatchesPage } from "./pages/QuoteIngestionBatchesPage";
import { QuoteIngestionQualityPage } from "./pages/QuoteIngestionQualityPage";
import { QuoteAiProviderSettingsPage } from "./pages/QuoteAiProviderSettingsPage";

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
              path="quotes/ai"
              element={
                <RequirePermission permission="quote_ingestion.read">
                  <QuoteAiImportPage />
                </RequirePermission>
              }
            />
            <Route
              path="quotes/ai/batches"
              element={
                <RequirePermission permission="quote_ingestion.read">
                  <QuoteIngestionBatchesPage />
                </RequirePermission>
              }
            />
            <Route
              path="quotes/ai/quality"
              element={
                <RequirePermission permission="quote_ingestion.read">
                  <QuoteIngestionQualityPage />
                </RequirePermission>
              }
            />
            <Route
              path="quotes/ai/settings"
              element={
                <RequirePermission permission="quote_ingestion.manage_provider">
                  <QuoteAiProviderSettingsPage />
                </RequirePermission>
              }
            />
            <Route
              path="quotes/ai/documents/:documentId"
              element={
                <RequirePermission permission="quote_ingestion.read">
                  <QuoteIngestionReviewPage />
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
            <Route
              path="analytics/fuel-sales/margins"
              element={
                <RequirePermission permission="fuel_sales_analytics.view_margin">
                  <FuelMarginsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-sales/prices"
              element={
                <RequirePermission permission="fuel_sales_analytics.read">
                  <FuelPricesPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-purchases"
              element={
                <RequirePermission permission="fuel_purchases.read">
                  <FuelPurchasesDashboardPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/purchase-benchmarks"
              element={
                <RequirePermission permission="purchase_benchmarks.read">
                  <PurchaseBenchmarkDashboardPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/purchase-benchmarks/opportunities"
              element={
                <RequirePermission permission="purchase_benchmarks.view_opportunity">
                  <PurchaseBenchmarkOpportunitiesPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/purchase-benchmarks/quality"
              element={
                <RequirePermission permission="purchase_benchmarks.read">
                  <PurchaseBenchmarkDataQualityPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/purchase-benchmarks/runs/:id"
              element={
                <RequirePermission permission="purchase_benchmarks.read">
                  <PurchaseBenchmarkRunDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-purchases/invoices"
              element={
                <RequirePermission permission="purchase_invoices.read">
                  <FuelPurchaseInvoicesPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-purchases/invoices/:id"
              element={
                <RequirePermission permission="purchase_invoices.read">
                  <FuelPurchaseInvoiceDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-purchases/costs"
              element={
                <RequirePermission permission="fuel_purchases.view_cost">
                  <FuelPurchaseCostsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/fuel-purchases/quality"
              element={
                <RequirePermission permission="purchase_data_quality.read">
                  <PurchaseDataQualityPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/accounts-payable"
              element={
                <RequirePermission permission="accounts_payable.read">
                  <AccountsPayablePage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/nfe-documents"
              element={
                <RequirePermission permission="nfe_documents.read">
                  <NfeDocumentsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/external-indices"
              element={
                <RequirePermission permission="external_data.read">
                  <ExternalIndicesDashboardPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/external-indices/series"
              element={
                <RequirePermission permission="external_data.read">
                  <ExternalSeriesPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/external-indices/series/:id"
              element={
                <RequirePermission permission="external_data.read">
                  <ExternalSeriesDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/external-indices/sources"
              element={
                <RequirePermission permission="external_data.read">
                  <ExternalDataSourcesPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/external-indices/imports"
              element={
                <RequirePermission permission="external_data.import">
                  <ExternalImportsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/external-indices/runs"
              element={
                <RequirePermission permission="external_data.read">
                  <ExternalIngestionRunsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/external-indices/quality"
              element={
                <RequirePermission permission="external_data.read">
                  <ExternalDataQualityPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/market-correlation"
              element={
                <RequirePermission permission="market_analysis.read">
                  <MarketCorrelationDashboardPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/market-correlation/runs/:id"
              element={
                <RequirePermission permission="market_analysis.read">
                  <MarketAnalysisRunDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/market-correlation/quality"
              element={
                <RequirePermission permission="market_analysis.read">
                  <MarketAnalysisQualityPage />
                </RequirePermission>
              }
            />
            <Route
              path="analytics/market-correlation/parameters"
              element={
                <RequirePermission permission="market_analysis.read">
                  <MarketAnalysisParametersPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingDashboardPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/margins"
              element={
                <RequirePermission permission="pricing.view_margin">
                  <CurrentMarginsPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/recommendations"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingRecommendationsPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/recommendations/:id"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingRecommendationDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/approvals"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingApprovalQueuePage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/decisions/:id"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingDecisionDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/implementations"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingImplementationsPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/policies"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingPoliciesPage />
                </RequirePermission>
              }
            />
            <Route
              path="pricing/quality"
              element={
                <RequirePermission permission="pricing.read">
                  <PricingDataQualityPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive"
              element={
                <RequirePermission permission="executive_dashboard.read">
                  <ExecutiveDashboardPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/stations"
              element={
                <RequirePermission permission="executive_dashboard.read">
                  <ExecutiveStationDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/alerts"
              element={
                <RequirePermission permission="alerts.read">
                  <AlertsCenterPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/alerts/:id"
              element={
                <RequirePermission permission="alerts.read">
                  <AlertDetailsPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/alert-rules"
              element={
                <RequirePermission permission="alerts.read">
                  <AlertRulesPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/notifications"
              element={
                <RequirePermission permission="alerts.read">
                  <NotificationPoliciesPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/health"
              element={
                <RequirePermission permission="operations.read_health">
                  <OperationsHealthPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/jobs"
              element={
                <RequirePermission permission="operations.read_jobs">
                  <OperationalJobsPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/slo"
              element={
                <RequirePermission permission="operations.read_slo">
                  <OperationalSloPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/incidents"
              element={
                <RequirePermission permission="operations.manage_incidents">
                  <OperationalIncidentsPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/quality"
              element={
                <RequirePermission permission="executive_dashboard.read">
                  <DataQualityOverviewPage />
                </RequirePermission>
              }
            />
            <Route
              path="executive/readiness"
              element={
                <RequirePermission permission="operations.view_readiness">
                  <ProductionReadinessPage />
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
