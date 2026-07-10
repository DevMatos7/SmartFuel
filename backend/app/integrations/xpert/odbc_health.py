from __future__ import annotations

from app.core.config import settings


def list_odbc_drivers() -> list[str]:
    try:
        import pyodbc

        return list(pyodbc.drivers())
    except Exception:
        return []


def driver_available(driver_name: str | None = None) -> tuple[bool, str | None]:
    expected = driver_name or settings.xpert_odbc_driver
    drivers = list_odbc_drivers()
    if expected in drivers:
        return True, None
    installed = ", ".join(drivers) if drivers else "nenhum"
    return False, f"Driver ODBC não encontrado: {expected}. Instalados: {installed}"


def assert_driver_available(driver_name: str | None = None) -> None:
    ok, message = driver_available(driver_name)
    if not ok:
        raise RuntimeError(message or "ODBC driver indisponível.")
