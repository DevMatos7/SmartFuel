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
        }
    ),
    "CONSULTA": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
            *_MASTER_DATA_READ,
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
