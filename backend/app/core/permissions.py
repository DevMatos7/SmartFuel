from enum import StrEnum


class Permission(StrEnum):
    ORGANIZATIONS_READ = "organizations.read"
    ORGANIZATIONS_WRITE = "organizations.write"
    STATIONS_READ = "stations.read"
    STATIONS_WRITE = "stations.write"
    USERS_READ = "users.read"
    USERS_WRITE = "users.write"
    USERS_MANAGE_ROLES = "users.manage_roles"
    USERS_MANAGE_STATIONS = "users.manage_stations"
    USERS_RESET_PASSWORD = "users.reset_password"
    AUDIT_READ = "audit.read"
    DASHBOARD_READ = "dashboard.read"
    PRODUCTS_READ = "products.read"
    PRODUCTS_WRITE = "products.write"
    PRODUCTS_DEACTIVATE = "products.deactivate"
    ERP_PRODUCTS_READ = "erp_products.read"
    ERP_PRODUCTS_MAP = "erp_products.map"
    ERP_PRODUCTS_IGNORE = "erp_products.ignore"
    ERP_PRODUCTS_IMPORT = "erp_products.import"
    DISTRIBUTORS_READ = "distributors.read"
    DISTRIBUTORS_WRITE = "distributors.write"
    DISTRIBUTORS_DEACTIVATE = "distributors.deactivate"
    DISTRIBUTION_BASES_READ = "distribution_bases.read"
    DISTRIBUTION_BASES_WRITE = "distribution_bases.write"
    PAYMENT_TERMS_READ = "payment_terms.read"
    PAYMENT_TERMS_WRITE = "payment_terms.write"
    SUPPLIER_RULES_READ = "supplier_rules.read"
    SUPPLIER_RULES_WRITE = "supplier_rules.write"
    MASTER_DATA_IMPORTS_READ = "master_data_imports.read"
    MASTER_DATA_IMPORTS_EXECUTE = "master_data_imports.execute"
    QUOTES_READ = "quotes.read"
    QUOTES_WRITE = "quotes.write"
    QUOTES_ACTIVATE = "quotes.activate"
    QUOTES_CANCEL = "quotes.cancel"
    QUOTES_REVISE = "quotes.revise"
    QUOTES_DUPLICATE = "quotes.duplicate"
    QUOTE_ITEMS_WRITE = "quote_items.write"
    QUOTE_EVIDENCES_READ = "quote_evidences.read"
    QUOTE_EVIDENCES_WRITE = "quote_evidences.write"
    QUOTE_EVIDENCES_DEACTIVATE = "quote_evidences.deactivate"
    QUOTE_HISTORY_READ = "quote_history.read"
    QUOTE_EXPIRATION_EXECUTE = "quote_expiration.execute"
    QUOTE_COMPARISONS_READ = "quote_comparisons.read"
    QUOTE_COMPARISONS_RUN = "quote_comparisons.run"
    QUOTE_COMPARISONS_EXPORT = "quote_comparisons.export"
    QUOTE_COMPARISONS_REPROCESS = "quote_comparisons.reprocess"
    QUOTE_COMPARISONS_VIEW_CALCULATION = "quote_comparisons.view_calculation"
    FINANCIAL_PARAMETERS_READ = "financial_parameters.read"
    FINANCIAL_PARAMETERS_WRITE = "financial_parameters.write"
    FINANCIAL_PARAMETERS_DEACTIVATE = "financial_parameters.deactivate"
    ERP_INTEGRATION_READ = "erp_integration.read"
    ERP_INTEGRATION_MANAGE = "erp_integration.manage"
    ERP_INTEGRATION_TEST = "erp_integration.test"
    ERP_SYNC_READ = "erp_sync.read"
    ERP_SYNC_RUN = "erp_sync.run"
    ERP_SYNC_CANCEL = "erp_sync.cancel"
    ERP_SYNC_RETRY = "erp_sync.retry"
    ERP_SYNC_MANAGE_SCHEDULE = "erp_sync.manage_schedule"
    ERP_SYNC_RESET_CHECKPOINT = "erp_sync.reset_checkpoint"
    ERP_SYNC_VIEW_STAGING = "erp_sync.view_staging"
    ERP_SYNC_VIEW_ERRORS = "erp_sync.view_errors"
    FUEL_SALES_ANALYTICS_READ = "fuel_sales_analytics.read"
    FUEL_SALES_ANALYTICS_EXPORT = "fuel_sales_analytics.export"
    FUEL_SALES_ANALYTICS_VIEW_MARGIN = "fuel_sales_analytics.view_margin"
    FUEL_SALES_DATA_QUALITY_READ = "fuel_sales_data_quality.read"
    FUEL_SALES_DATA_QUALITY_RECONCILE = "fuel_sales_data_quality.reconcile"
    ERP_PAYMENT_METHODS_READ = "erp_payment_methods.read"
    ERP_PAYMENT_METHODS_MAP = "erp_payment_methods.map"
    FUEL_PURCHASES_READ = "fuel_purchases.read"
    FUEL_PURCHASES_VIEW_COST = "fuel_purchases.view_cost"
    FUEL_PURCHASES_EXPORT = "fuel_purchases.export"
    PURCHASE_INVOICES_READ = "purchase_invoices.read"
    PURCHASE_INVOICES_VIEW_XML = "purchase_invoices.view_xml"
    NFE_DOCUMENTS_READ = "nfe_documents.read"
    NFE_DOCUMENTS_DOWNLOAD = "nfe_documents.download"
    NFE_DOCUMENTS_IMPORT = "nfe_documents.import"
    NFE_DOCUMENTS_RECONCILE = "nfe_documents.reconcile"
    ACCOUNTS_PAYABLE_READ = "accounts_payable.read"
    ACCOUNTS_PAYABLE_VIEW_VALUES = "accounts_payable.view_values"
    ACCOUNTS_PAYABLE_EXPORT = "accounts_payable.export"
    PURCHASE_DATA_QUALITY_READ = "purchase_data_quality.read"
    PURCHASE_DATA_QUALITY_RECONCILE = "purchase_data_quality.reconcile"
    PURCHASE_BENCHMARKS_READ = "purchase_benchmarks.read"
    PURCHASE_BENCHMARKS_RUN = "purchase_benchmarks.run"
    PURCHASE_BENCHMARKS_REPROCESS = "purchase_benchmarks.reprocess"
    PURCHASE_BENCHMARKS_OVERRIDE_REFERENCE = "purchase_benchmarks.override_reference"
    PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY = "purchase_benchmarks.view_opportunity"
    PURCHASE_BENCHMARKS_EXPORT = "purchase_benchmarks.export"
    PURCHASE_BENCHMARKS_MANAGE_PARAMETERS = "purchase_benchmarks.manage_parameters"
    EXTERNAL_DATA_READ = "external_data.read"
    EXTERNAL_DATA_VIEW_RAW = "external_data.view_raw"
    EXTERNAL_DATA_IMPORT = "external_data.import"
    EXTERNAL_DATA_SYNC = "external_data.sync"
    EXTERNAL_DATA_MANAGE_SOURCES = "external_data.manage_sources"
    EXTERNAL_DATA_MANAGE_SERIES = "external_data.manage_series"
    EXTERNAL_DATA_MANAGE_SCHEDULE = "external_data.manage_schedule"
    EXTERNAL_DATA_RESOLVE_QUALITY = "external_data.resolve_quality"
    EXTERNAL_DATA_EXPORT = "external_data.export"
    MARKET_ANALYSIS_READ = "market_analysis.read"
    MARKET_ANALYSIS_RUN = "market_analysis.run"
    MARKET_ANALYSIS_REPROCESS = "market_analysis.reprocess"
    MARKET_ANALYSIS_VIEW_RAW_PAIRS = "market_analysis.view_raw_pairs"
    MARKET_ANALYSIS_VIEW_STATISTICS = "market_analysis.view_statistics"
    MARKET_ANALYSIS_EXPORT = "market_analysis.export"
    MARKET_ANALYSIS_MANAGE_PARAMETERS = "market_analysis.manage_parameters"
    PRICING_READ = "pricing.read"
    PRICING_VIEW_COST = "pricing.view_cost"
    PRICING_VIEW_MARGIN = "pricing.view_margin"
    PRICING_GENERATE_RECOMMENDATION = "pricing.generate_recommendation"
    PRICING_REVIEW = "pricing.review"
    PRICING_APPROVE = "pricing.approve"
    PRICING_REJECT = "pricing.reject"
    PRICING_MANAGE_POLICIES = "pricing.manage_policies"
    PRICING_ADD_EVIDENCE = "pricing.add_evidence"
    PRICING_CONFIRM_IMPLEMENTATION = "pricing.confirm_implementation"
    PRICING_VIEW_AUDIT = "pricing.view_audit"
    PRICING_EXPORT = "pricing.export"
    EXECUTIVE_DASHBOARD_READ = "executive_dashboard.read"
    EXECUTIVE_DASHBOARD_VIEW_FINANCIALS = "executive_dashboard.view_financials"
    EXECUTIVE_DASHBOARD_EXPORT = "executive_dashboard.export"
    ALERTS_READ = "alerts.read"
    ALERTS_ACKNOWLEDGE = "alerts.acknowledge"
    ALERTS_ASSIGN = "alerts.assign"
    ALERTS_RESOLVE = "alerts.resolve"
    ALERTS_MANAGE_RULES = "alerts.manage_rules"
    ALERTS_MANAGE_NOTIFICATIONS = "alerts.manage_notifications"
    ALERTS_EXPORT = "alerts.export"
    OPERATIONS_READ_HEALTH = "operations.read_health"
    OPERATIONS_READ_JOBS = "operations.read_jobs"
    OPERATIONS_MANAGE_JOBS = "operations.manage_jobs"
    OPERATIONS_READ_SLO = "operations.read_slo"
    OPERATIONS_MANAGE_INCIDENTS = "operations.manage_incidents"
    OPERATIONS_VIEW_AUDIT = "operations.view_audit"
    OPERATIONS_MANAGE_FEATURE_FLAGS = "operations.manage_feature_flags"
    OPERATIONS_VIEW_READINESS = "operations.view_readiness"
    QUOTE_INGESTION_READ = "quote_ingestion.read"
    QUOTE_INGESTION_UPLOAD = "quote_ingestion.upload"
    QUOTE_INGESTION_REVIEW = "quote_ingestion.review"
    QUOTE_INGESTION_APPROVE = "quote_ingestion.approve"
    QUOTE_INGESTION_CREATE_DRAFT = "quote_ingestion.create_draft"
    QUOTE_INGESTION_RETRY = "quote_ingestion.retry"
    QUOTE_INGESTION_ARCHIVE = "quote_ingestion.archive"
    QUOTE_INGESTION_VIEW_RAW_TEXT = "quote_ingestion.view_raw_text"
    QUOTE_INGESTION_DOWNLOAD_DOCUMENT = "quote_ingestion.download_document"
    QUOTE_INGESTION_VIEW_AI_PAYLOAD = "quote_ingestion.view_ai_payload"
    QUOTE_INGESTION_MANAGE_PROVIDER = "quote_ingestion.manage_provider"
    QUOTE_INGESTION_MANAGE_PROMPTS = "quote_ingestion.manage_prompts"
    QUOTE_INGESTION_RUN_EVALUATION = "quote_ingestion.run_evaluation"
    QUOTE_INGESTION_VIEW_COSTS = "quote_ingestion.view_costs"


_MASTER_DATA_READ = frozenset(
    {
        Permission.PRODUCTS_READ,
        Permission.ERP_PRODUCTS_READ,
        Permission.DISTRIBUTORS_READ,
        Permission.DISTRIBUTION_BASES_READ,
        Permission.PAYMENT_TERMS_READ,
        Permission.SUPPLIER_RULES_READ,
        Permission.MASTER_DATA_IMPORTS_READ,
    }
)

ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "ADMIN": frozenset(Permission),
    "GESTOR": frozenset(
        {
            Permission.ORGANIZATIONS_READ,
            Permission.STATIONS_READ,
            Permission.USERS_READ,
            Permission.AUDIT_READ,
            Permission.DASHBOARD_READ,
            Permission.PRODUCTS_READ,
            Permission.ERP_PRODUCTS_READ,
            Permission.ERP_PRODUCTS_MAP,
            Permission.ERP_PRODUCTS_IGNORE,
            Permission.DISTRIBUTORS_READ,
            Permission.DISTRIBUTION_BASES_READ,
            Permission.PAYMENT_TERMS_READ,
            Permission.SUPPLIER_RULES_READ,
            Permission.SUPPLIER_RULES_WRITE,
            Permission.MASTER_DATA_IMPORTS_READ,
            Permission.QUOTES_READ,
            Permission.QUOTES_WRITE,
            Permission.QUOTES_ACTIVATE,
            Permission.QUOTES_CANCEL,
            Permission.QUOTES_REVISE,
            Permission.QUOTE_ITEMS_WRITE,
            Permission.QUOTE_EVIDENCES_READ,
            Permission.QUOTE_EVIDENCES_WRITE,
            Permission.QUOTE_HISTORY_READ,
            Permission.QUOTE_COMPARISONS_READ,
            Permission.QUOTE_COMPARISONS_RUN,
            Permission.QUOTE_COMPARISONS_EXPORT,
            Permission.QUOTE_COMPARISONS_REPROCESS,
            Permission.QUOTE_COMPARISONS_VIEW_CALCULATION,
            Permission.FINANCIAL_PARAMETERS_READ,
            Permission.ERP_INTEGRATION_READ,
            Permission.ERP_SYNC_READ,
            Permission.ERP_SYNC_VIEW_ERRORS,
            Permission.FUEL_SALES_ANALYTICS_READ,
            Permission.FUEL_SALES_ANALYTICS_EXPORT,
            Permission.FUEL_SALES_ANALYTICS_VIEW_MARGIN,
            Permission.FUEL_SALES_DATA_QUALITY_READ,
            Permission.ERP_PAYMENT_METHODS_READ,
            Permission.FUEL_PURCHASES_READ,
            Permission.FUEL_PURCHASES_VIEW_COST,
            Permission.FUEL_PURCHASES_EXPORT,
            Permission.PURCHASE_INVOICES_READ,
            Permission.PURCHASE_INVOICES_VIEW_XML,
            Permission.NFE_DOCUMENTS_READ,
            Permission.NFE_DOCUMENTS_DOWNLOAD,
            Permission.NFE_DOCUMENTS_RECONCILE,
            Permission.ACCOUNTS_PAYABLE_READ,
            Permission.ACCOUNTS_PAYABLE_VIEW_VALUES,
            Permission.ACCOUNTS_PAYABLE_EXPORT,
            Permission.PURCHASE_DATA_QUALITY_READ,
            Permission.PURCHASE_DATA_QUALITY_RECONCILE,
            Permission.PURCHASE_BENCHMARKS_READ,
            Permission.PURCHASE_BENCHMARKS_RUN,
            Permission.PURCHASE_BENCHMARKS_REPROCESS,
            Permission.PURCHASE_BENCHMARKS_OVERRIDE_REFERENCE,
            Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY,
            Permission.PURCHASE_BENCHMARKS_EXPORT,
            Permission.EXTERNAL_DATA_READ,
            Permission.EXTERNAL_DATA_IMPORT,
            Permission.EXTERNAL_DATA_SYNC,
            Permission.EXTERNAL_DATA_RESOLVE_QUALITY,
            Permission.EXTERNAL_DATA_EXPORT,
            Permission.EXTERNAL_DATA_VIEW_RAW,
            Permission.MARKET_ANALYSIS_READ,
            Permission.MARKET_ANALYSIS_RUN,
            Permission.MARKET_ANALYSIS_REPROCESS,
            Permission.MARKET_ANALYSIS_VIEW_RAW_PAIRS,
            Permission.MARKET_ANALYSIS_VIEW_STATISTICS,
            Permission.MARKET_ANALYSIS_EXPORT,
            Permission.PRICING_READ,
            Permission.PRICING_VIEW_COST,
            Permission.PRICING_VIEW_MARGIN,
            Permission.PRICING_GENERATE_RECOMMENDATION,
            Permission.PRICING_REVIEW,
            Permission.PRICING_APPROVE,
            Permission.PRICING_REJECT,
            Permission.PRICING_ADD_EVIDENCE,
            Permission.PRICING_CONFIRM_IMPLEMENTATION,
            Permission.PRICING_VIEW_AUDIT,
            Permission.PRICING_EXPORT,
            Permission.EXECUTIVE_DASHBOARD_READ,
            Permission.EXECUTIVE_DASHBOARD_VIEW_FINANCIALS,
            Permission.EXECUTIVE_DASHBOARD_EXPORT,
            Permission.ALERTS_READ,
            Permission.ALERTS_ACKNOWLEDGE,
            Permission.ALERTS_ASSIGN,
            Permission.ALERTS_RESOLVE,
            Permission.ALERTS_EXPORT,
            Permission.OPERATIONS_READ_HEALTH,
            Permission.OPERATIONS_READ_JOBS,
            Permission.OPERATIONS_READ_SLO,
            Permission.OPERATIONS_MANAGE_INCIDENTS,
            Permission.OPERATIONS_VIEW_READINESS,
            Permission.QUOTE_INGESTION_READ,
            Permission.QUOTE_INGESTION_UPLOAD,
            Permission.QUOTE_INGESTION_REVIEW,
            Permission.QUOTE_INGESTION_APPROVE,
            Permission.QUOTE_INGESTION_CREATE_DRAFT,
            Permission.QUOTE_INGESTION_RETRY,
            Permission.QUOTE_INGESTION_ARCHIVE,
            Permission.QUOTE_INGESTION_VIEW_RAW_TEXT,
            Permission.QUOTE_INGESTION_DOWNLOAD_DOCUMENT,
            Permission.QUOTE_INGESTION_VIEW_AI_PAYLOAD,
            Permission.QUOTE_INGESTION_VIEW_COSTS,
        }
    ),
    "COMPRADOR": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
            Permission.PRODUCTS_READ,
            Permission.ERP_PRODUCTS_READ,
            Permission.ERP_PRODUCTS_MAP,
            Permission.DISTRIBUTORS_READ,
            Permission.DISTRIBUTORS_WRITE,
            Permission.DISTRIBUTION_BASES_READ,
            Permission.DISTRIBUTION_BASES_WRITE,
            Permission.PAYMENT_TERMS_READ,
            Permission.SUPPLIER_RULES_READ,
            Permission.QUOTES_READ,
            Permission.QUOTES_WRITE,
            Permission.QUOTES_ACTIVATE,
            Permission.QUOTES_CANCEL,
            Permission.QUOTES_REVISE,
            Permission.QUOTES_DUPLICATE,
            Permission.QUOTE_ITEMS_WRITE,
            Permission.QUOTE_EVIDENCES_READ,
            Permission.QUOTE_EVIDENCES_WRITE,
            Permission.QUOTE_HISTORY_READ,
            Permission.QUOTE_COMPARISONS_READ,
            Permission.QUOTE_COMPARISONS_RUN,
            Permission.QUOTE_COMPARISONS_EXPORT,
            Permission.QUOTE_COMPARISONS_REPROCESS,
            Permission.QUOTE_COMPARISONS_VIEW_CALCULATION,
            Permission.ERP_SYNC_READ,
            Permission.FUEL_SALES_ANALYTICS_READ,
            Permission.FUEL_SALES_DATA_QUALITY_READ,
            Permission.FUEL_SALES_DATA_QUALITY_RECONCILE,
            Permission.ERP_PAYMENT_METHODS_READ,
            Permission.ERP_PAYMENT_METHODS_MAP,
            Permission.FUEL_PURCHASES_READ,
            Permission.FUEL_PURCHASES_VIEW_COST,
            Permission.FUEL_PURCHASES_EXPORT,
            Permission.PURCHASE_INVOICES_READ,
            Permission.PURCHASE_INVOICES_VIEW_XML,
            Permission.NFE_DOCUMENTS_READ,
            Permission.NFE_DOCUMENTS_DOWNLOAD,
            Permission.NFE_DOCUMENTS_IMPORT,
            Permission.NFE_DOCUMENTS_RECONCILE,
            Permission.ACCOUNTS_PAYABLE_READ,
            Permission.PURCHASE_DATA_QUALITY_READ,
            Permission.PURCHASE_DATA_QUALITY_RECONCILE,
            Permission.PURCHASE_BENCHMARKS_READ,
            Permission.PURCHASE_BENCHMARKS_RUN,
            Permission.PURCHASE_BENCHMARKS_REPROCESS,
            Permission.PURCHASE_BENCHMARKS_OVERRIDE_REFERENCE,
            Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY,
            Permission.PURCHASE_BENCHMARKS_EXPORT,
            Permission.EXTERNAL_DATA_READ,
            Permission.EXTERNAL_DATA_IMPORT,
            Permission.EXTERNAL_DATA_SYNC,
            Permission.EXTERNAL_DATA_RESOLVE_QUALITY,
            Permission.EXTERNAL_DATA_EXPORT,
            Permission.MARKET_ANALYSIS_READ,
            Permission.MARKET_ANALYSIS_RUN,
            Permission.MARKET_ANALYSIS_REPROCESS,
            Permission.MARKET_ANALYSIS_VIEW_RAW_PAIRS,
            Permission.MARKET_ANALYSIS_VIEW_STATISTICS,
            Permission.MARKET_ANALYSIS_EXPORT,
            Permission.PRICING_READ,
            Permission.PRICING_VIEW_COST,
            Permission.PRICING_VIEW_MARGIN,
            Permission.PRICING_GENERATE_RECOMMENDATION,
            Permission.PRICING_REVIEW,
            Permission.PRICING_ADD_EVIDENCE,
            Permission.PRICING_CONFIRM_IMPLEMENTATION,
            Permission.PRICING_EXPORT,
            Permission.EXECUTIVE_DASHBOARD_READ,
            Permission.EXECUTIVE_DASHBOARD_VIEW_FINANCIALS,
            Permission.ALERTS_READ,
            Permission.ALERTS_ACKNOWLEDGE,
            Permission.ALERTS_ASSIGN,
            Permission.ALERTS_RESOLVE,
            Permission.ALERTS_EXPORT,
            Permission.QUOTE_INGESTION_READ,
            Permission.QUOTE_INGESTION_UPLOAD,
            Permission.QUOTE_INGESTION_REVIEW,
            Permission.QUOTE_INGESTION_APPROVE,
            Permission.QUOTE_INGESTION_CREATE_DRAFT,
            Permission.QUOTE_INGESTION_RETRY,
            Permission.QUOTE_INGESTION_ARCHIVE,
            Permission.QUOTE_INGESTION_VIEW_RAW_TEXT,
            Permission.QUOTE_INGESTION_DOWNLOAD_DOCUMENT,
            Permission.QUOTE_INGESTION_VIEW_AI_PAYLOAD,
        }
    ),
    "FINANCEIRO": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
            Permission.PRODUCTS_READ,
            Permission.ERP_PRODUCTS_READ,
            Permission.DISTRIBUTORS_READ,
            Permission.DISTRIBUTION_BASES_READ,
            Permission.PAYMENT_TERMS_READ,
            Permission.PAYMENT_TERMS_WRITE,
            Permission.SUPPLIER_RULES_READ,
            Permission.QUOTES_READ,
            Permission.QUOTE_EVIDENCES_READ,
            Permission.QUOTE_HISTORY_READ,
            Permission.QUOTE_COMPARISONS_READ,
            Permission.QUOTE_COMPARISONS_RUN,
            Permission.QUOTE_COMPARISONS_EXPORT,
            Permission.QUOTE_COMPARISONS_REPROCESS,
            Permission.QUOTE_COMPARISONS_VIEW_CALCULATION,
            Permission.FINANCIAL_PARAMETERS_READ,
            Permission.FINANCIAL_PARAMETERS_WRITE,
            Permission.FINANCIAL_PARAMETERS_DEACTIVATE,
            Permission.ERP_INTEGRATION_READ,
            Permission.ERP_SYNC_READ,
            Permission.FUEL_SALES_ANALYTICS_READ,
            Permission.FUEL_SALES_ANALYTICS_VIEW_MARGIN,
            Permission.ERP_PAYMENT_METHODS_READ,
            Permission.ERP_PAYMENT_METHODS_MAP,
            Permission.FUEL_PURCHASES_READ,
            Permission.FUEL_PURCHASES_VIEW_COST,
            Permission.FUEL_PURCHASES_EXPORT,
            Permission.PURCHASE_INVOICES_READ,
            Permission.PURCHASE_INVOICES_VIEW_XML,
            Permission.NFE_DOCUMENTS_READ,
            Permission.NFE_DOCUMENTS_DOWNLOAD,
            Permission.NFE_DOCUMENTS_IMPORT,
            Permission.NFE_DOCUMENTS_RECONCILE,
            Permission.ACCOUNTS_PAYABLE_READ,
            Permission.ACCOUNTS_PAYABLE_VIEW_VALUES,
            Permission.ACCOUNTS_PAYABLE_EXPORT,
            Permission.PURCHASE_DATA_QUALITY_READ,
            Permission.PURCHASE_DATA_QUALITY_RECONCILE,
            Permission.PURCHASE_BENCHMARKS_READ,
            Permission.PURCHASE_BENCHMARKS_VIEW_OPPORTUNITY,
            Permission.PURCHASE_BENCHMARKS_EXPORT,
            Permission.EXTERNAL_DATA_READ,
            Permission.EXTERNAL_DATA_EXPORT,
            Permission.MARKET_ANALYSIS_READ,
            Permission.MARKET_ANALYSIS_VIEW_STATISTICS,
            Permission.MARKET_ANALYSIS_EXPORT,
            Permission.PRICING_READ,
            Permission.PRICING_VIEW_COST,
            Permission.PRICING_VIEW_MARGIN,
            Permission.PRICING_ADD_EVIDENCE,
            Permission.PRICING_EXPORT,
            Permission.EXECUTIVE_DASHBOARD_READ,
            Permission.EXECUTIVE_DASHBOARD_VIEW_FINANCIALS,
            Permission.EXECUTIVE_DASHBOARD_EXPORT,
            Permission.QUOTE_INGESTION_READ,
            Permission.QUOTE_INGESTION_DOWNLOAD_DOCUMENT,
        }
    ),
    "CONSULTA": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
            Permission.PRODUCTS_READ,
            Permission.ERP_PRODUCTS_READ,
            Permission.DISTRIBUTORS_READ,
            Permission.DISTRIBUTION_BASES_READ,
            Permission.PAYMENT_TERMS_READ,
            Permission.SUPPLIER_RULES_READ,
            Permission.QUOTES_READ,
            Permission.QUOTE_EVIDENCES_READ,
            Permission.QUOTE_HISTORY_READ,
            Permission.QUOTE_COMPARISONS_READ,
            Permission.QUOTE_COMPARISONS_VIEW_CALCULATION,
            Permission.FINANCIAL_PARAMETERS_READ,
            Permission.ERP_SYNC_READ,
            Permission.FUEL_SALES_ANALYTICS_READ,
            Permission.FUEL_PURCHASES_READ,
            Permission.PURCHASE_INVOICES_READ,
            Permission.NFE_DOCUMENTS_READ,
            Permission.ACCOUNTS_PAYABLE_READ,
            Permission.PURCHASE_DATA_QUALITY_READ,
            Permission.PURCHASE_BENCHMARKS_READ,
            Permission.EXTERNAL_DATA_READ,
            Permission.MARKET_ANALYSIS_READ,
            Permission.PRICING_READ,
            Permission.EXECUTIVE_DASHBOARD_READ,
            Permission.ALERTS_READ,
        }
    ),
}


def permissions_for_roles(role_codes: list[str]) -> list[str]:
    effective: set[Permission] = set()
    for code in role_codes:
        effective.update(ROLE_PERMISSIONS.get(code, frozenset()))
    return sorted(p.value for p in effective)


def has_permission(role_codes: list[str], permission: Permission | str) -> bool:
    perm = Permission(permission) if isinstance(permission, str) else permission
    return perm in {p for code in role_codes for p in ROLE_PERMISSIONS.get(code, frozenset())}
