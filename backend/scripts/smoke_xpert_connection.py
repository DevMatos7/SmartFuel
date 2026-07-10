"""Smoke test de conexão XPERT — lê credenciais apenas de variáveis de ambiente."""

from __future__ import annotations

import os
import sys

HOST = os.environ.get("XPERT_SQLSERVER_HOST", "")
PORT = os.environ.get("XPERT_SQLSERVER_PORT", "1433")
DATABASE = os.environ.get("XPERT_SQLSERVER_DATABASE", "atxdados")
USER = os.environ.get("XPERT_SQLSERVER_USER", "")
PASSWORD = os.environ.get("XPERT_SQLSERVER_PASSWORD", "")
DRIVER = os.environ.get("XPERT_ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
ENCRYPT = os.environ.get("XPERT_SQLSERVER_ENCRYPT", "true").lower() in ("1", "true", "yes")
TRUST = os.environ.get("XPERT_SQLSERVER_TRUST_CERTIFICATE", "true").lower() in ("1", "true", "yes")
TIMEOUT = int(os.environ.get("XPERT_CONNECTION_TIMEOUT_SECONDS", "15"))


def main() -> int:
    if not HOST or not USER or not PASSWORD:
        print("Defina XPERT_SQLSERVER_HOST, XPERT_SQLSERVER_USER e XPERT_SQLSERVER_PASSWORD")
        return 2

    import pyodbc

    drivers = pyodbc.drivers()
    print(f"ODBC drivers: {drivers}")
    if DRIVER not in drivers:
        print(f"Driver ausente: {DRIVER}")
        return 3

    conn_str = (
        f"DRIVER={{{DRIVER}}};"
        f"SERVER={HOST},{PORT};"
        f"DATABASE={DATABASE};"
        f"UID={USER};"
        f"PWD={PASSWORD};"
        f"Encrypt={'yes' if ENCRYPT else 'no'};"
        f"TrustServerCertificate={'yes' if TRUST else 'no'};"
        "ApplicationIntent=ReadOnly;"
        f"Connection Timeout={TIMEOUT};"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=TIMEOUT)
        cur = conn.cursor()
        cur.execute("SELECT @@VERSION")
        version = str(cur.fetchone()[0]).split("\n")[0][:120]
        cur.execute("SELECT DB_NAME()")
        db_name = cur.fetchone()[0]
        cur.execute("SELECT SYSUTCDATETIME()")
        source_utc = cur.fetchone()[0]
        cur.execute(
            "SELECT IS_SRVROLEMEMBER('sysadmin'), IS_MEMBER('db_owner'), IS_MEMBER('db_datawriter')"
        )
        sysadmin, db_owner, db_writer = cur.fetchone()
        print("OK: conexão estabelecida")
        print(f"  database={db_name}")
        print(f"  version={version}")
        print(f"  source_utc={source_utc}")
        print(f"  sysadmin={bool(sysadmin)} db_owner={bool(db_owner)} db_datawriter={bool(db_writer)}")
        if sysadmin or db_owner or db_writer:
            print("  AVISO: conta com privilégios elevados — não usar em produção")
        conn.close()
        return 0
    except Exception as exc:
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
