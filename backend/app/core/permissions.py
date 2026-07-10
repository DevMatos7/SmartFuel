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
        }
    ),
    "CONSULTA": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
            *_MASTER_DATA_READ,
            Permission.QUOTES_READ,
            Permission.QUOTE_EVIDENCES_READ,
            Permission.QUOTE_HISTORY_READ,
            Permission.QUOTE_COMPARISONS_READ,
            Permission.QUOTE_COMPARISONS_EXPORT,
            Permission.QUOTE_COMPARISONS_VIEW_CALCULATION,
            Permission.FUEL_SALES_ANALYTICS_READ,
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
