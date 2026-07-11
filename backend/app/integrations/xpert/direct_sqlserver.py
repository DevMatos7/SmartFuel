from __future__ import annotations

import re
import time
import uuid
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.integrations.xpert.datasource import ConnectionTestResult, XpertDataSource
from app.integrations.xpert.odbc_health import assert_driver_available
from app.integrations.xpert.secret_resolver import resolve_secret
from app.models.erp_integration import ErpSource


def build_connection_string(source: ErpSource, credentials: dict[str, str]) -> str:
    encrypt = "yes" if source.encrypt_connection else "no"
    trust = "yes" if source.trust_server_certificate else "no"
    return (
        f"DRIVER={{{source.driver_name}}};"
        f"SERVER={source.host},{source.port};"
        f"DATABASE={source.database_name};"
        f"UID={credentials['user']};"
        f"PWD={credentials['password']};"
        f"Encrypt={encrypt};"
        f"TrustServerCertificate={trust};"
        f"ApplicationIntent=ReadOnly;"
    )


class DirectSqlServerDataSource(XpertDataSource):
    def __init__(self, source: ErpSource) -> None:
        self.source = source
        self._conn = None

    def _connect(self):
        if self._conn is not None:
            return self._conn
        assert_driver_available(self.source.driver_name)
        import pyodbc

        credentials = resolve_secret(self.source.secret_ref)
        conn_str = build_connection_string(self.source, credentials)
        self._conn = pyodbc.connect(
            conn_str,
            timeout=settings.xpert_connection_timeout_seconds,
            autocommit=True,
        )
        return self._conn

    def test_connection(self) -> ConnectionTestResult:
        started = time.perf_counter()
        try:
            conn = self._connect()
            cursor = conn.cursor()
            cursor.execute("SELECT @@VERSION")
            version = str(cursor.fetchone()[0])
            cursor.execute("SELECT DB_NAME()")
            db_name = str(cursor.fetchone()[0])
            cursor.execute("SELECT SYSUTCDATETIME()")
            source_time = cursor.fetchone()[0]
            if isinstance(source_time, datetime) and source_time.tzinfo is None:
                source_time = source_time.replace(tzinfo=UTC)
            privileges = self._check_privileges(cursor)
            unsafe = self._is_unsafe(privileges)
            if unsafe and not settings.xpert_allow_unsafe_privileges:
                status = "UNSAFE"
            else:
                status = "CONNECTED"
            latency = int((time.perf_counter() - started) * 1000)
            warnings: list[str] = []
            if self.source.trust_server_certificate:
                warnings.append("TrustServerCertificate está habilitado.")
            if unsafe:
                warnings.append("Usuário possui privilégios incompatíveis com somente leitura.")
            return ConnectionTestResult(
                status=status,
                latency_ms=latency,
                server_version=version.split("\n")[0][:120],
                database_name="***",
                source_utc_time=source_time,
                encryption=self.source.encrypt_connection,
                privileges=privileges,
                warnings=warnings,
            )
        except Exception as exc:
            return ConnectionTestResult(
                status="DISCONNECTED",
                error=str(exc)[:500],
            )

    def _is_unsafe(self, privileges: dict[str, bool]) -> bool:
        role_flags = ("sysadmin", "db_owner", "db_datawriter")
        if any(privileges.get(k) for k in role_flags):
            return True
        permission_flags = (
            "db_insert",
            "db_update",
            "db_delete",
            "db_alter",
            "db_control",
            "db_execute",
        )
        return any(privileges.get(k) for k in permission_flags)

    def _check_privileges(self, cursor) -> dict[str, bool]:
        privileges = {
            "sysadmin": False,
            "db_owner": False,
            "db_datawriter": False,
            "db_insert": False,
            "db_update": False,
            "db_delete": False,
            "db_alter": False,
            "db_control": False,
            "db_execute": False,
        }
        try:
            cursor.execute(
                "SELECT IS_SRVROLEMEMBER('sysadmin'), IS_MEMBER('db_owner'), IS_MEMBER('db_datawriter')"
            )
            row = cursor.fetchone()
            if row:
                privileges["sysadmin"] = bool(row[0])
                privileges["db_owner"] = bool(row[1])
                privileges["db_datawriter"] = bool(row[2])
        except Exception:
            pass
        try:
            cursor.execute(
                """
                SELECT
                    HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'INSERT'),
                    HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'UPDATE'),
                    HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'DELETE'),
                    HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER'),
                    HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CONTROL'),
                    HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'EXECUTE')
                """
            )
            row = cursor.fetchone()
            if row:
                privileges["db_insert"] = bool(row[0])
                privileges["db_update"] = bool(row[1])
                privileges["db_delete"] = bool(row[2])
                privileges["db_alter"] = bool(row[3])
                privileges["db_control"] = bool(row[4])
                privileges["db_execute"] = bool(row[5])
        except Exception:
            pass
        return privileges

    def get_source_utc_time(self) -> datetime:
        conn = self._connect()
        cursor = conn.cursor()
        cursor.execute("SELECT SYSUTCDATETIME()")
        value = cursor.fetchone()[0]
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return datetime.now(UTC)

    def probe_contract(self, sql: str, parameters: dict[str, Any], limit: int = 5) -> Any:
        from app.integrations.xpert.datasource import ContractProbeResult

        conn = self._connect()
        cursor = conn.cursor()
        prepared_sql, param_values = _prepare_sql(sql, parameters)
        cursor.execute(prepared_sql, param_values)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        rows: list[dict[str, Any]] = []
        while len(rows) < limit:
            batch = cursor.fetchmany(limit - len(rows))
            if not batch:
                break
            for row in batch:
                rows.append(dict(zip(columns, row, strict=False)))
        return ContractProbeResult(columns=columns, sample_rows=rows, row_count=len(rows))

    def stream_rows(self, sql: str, parameters: dict[str, Any], *, batch_size: int = 1000):
        conn = self._connect()
        cursor = conn.cursor()
        prepared_sql, param_values = _prepare_sql(sql, parameters)
        cursor.execute(prepared_sql, param_values)
        columns = [col[0] for col in cursor.description] if cursor.description else []
        while True:
            batch = cursor.fetchmany(batch_size)
            if not batch:
                break
            yield [dict(zip(columns, row, strict=False)) for row in batch]

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def _strip_sql_comments(sql: str) -> str:
    without_blocks = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    lines: list[str] = []
    for line in without_blocks.splitlines():
        if "--" in line:
            line = line[: line.index("--")]
        lines.append(line)
    return "\n".join(lines)


def _prepare_sql(sql: str, parameters: dict[str, Any]) -> tuple[str, list[Any]]:
    values: list[Any] = []
    executable = _strip_sql_comments(sql)

    def repl(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in parameters:
            raise KeyError(f"Missing parameter: @{name}")
        values.append(parameters[name])
        return "?"

    prepared = re.sub(r"@([a-zA-Z_][a-zA-Z0-9_]*)", repl, executable)
    return prepared, values


def create_datasource(source: ErpSource, *, fake: XpertDataSource | None = None) -> XpertDataSource:
    if fake is not None:
        return fake
    return DirectSqlServerDataSource(source)
