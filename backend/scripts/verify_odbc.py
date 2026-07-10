"""Verifica presença do Microsoft ODBC Driver 18 no container."""

from __future__ import annotations

import sys

from app.core.config import settings
from app.integrations.xpert.odbc_health import driver_available, list_odbc_drivers


def main() -> int:
    drivers = list_odbc_drivers()
    ok, message = driver_available(settings.xpert_odbc_driver)
    print(f"ODBC drivers: {drivers}")
    if not ok:
        print(message, file=sys.stderr)
        return 1
    print(f"OK: {settings.xpert_odbc_driver}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
