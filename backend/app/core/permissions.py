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


ROLE_PERMISSIONS: dict[str, frozenset[Permission]] = {
    "ADMIN": frozenset(Permission),
    "GESTOR": frozenset(
        {
            Permission.ORGANIZATIONS_READ,
            Permission.STATIONS_READ,
            Permission.USERS_READ,
            Permission.AUDIT_READ,
            Permission.DASHBOARD_READ,
        }
    ),
    "COMPRADOR": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
        }
    ),
    "FINANCEIRO": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
        }
    ),
    "CONSULTA": frozenset(
        {
            Permission.STATIONS_READ,
            Permission.DASHBOARD_READ,
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
