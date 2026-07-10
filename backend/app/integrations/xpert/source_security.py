"""Classificação de segurança da fonte XPERT."""

from __future__ import annotations

from app.core.xpert_sync_enums import ErpSecurityStatus


_UNSAFE_ROLE_KEYS = ("sysadmin", "db_owner", "db_datawriter")
_UNSAFE_PERM_KEYS = ("db_insert", "db_update", "db_delete", "db_alter", "db_control", "db_execute")


def privileges_are_unsafe(privileges: dict[str, bool] | None) -> bool:
    if not privileges:
        return False
    if any(privileges.get(k) for k in _UNSAFE_ROLE_KEYS):
        return True
    return any(privileges.get(k) for k in _UNSAFE_PERM_KEYS)


def security_status_from_test(
    *,
    connection_status: str,
    privileges: dict[str, bool] | None,
    allow_unsafe_override: bool,
) -> str:
    if connection_status in ("DISCONNECTED", "DISABLED", "UNKNOWN"):
        return ErpSecurityStatus.UNKNOWN
    if privileges_are_unsafe(privileges):
        return ErpSecurityStatus.UNSAFE
    if connection_status == "UNSAFE" and allow_unsafe_override:
        return ErpSecurityStatus.UNSAFE
    if connection_status in ("CONNECTED", "DEGRADED"):
        return ErpSecurityStatus.SAFE
    return ErpSecurityStatus.UNKNOWN


def is_unsafe_security_status(status: str | None) -> bool:
    return status == ErpSecurityStatus.UNSAFE
