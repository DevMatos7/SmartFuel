from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Iterator

from app.integrations.xpert.datasource import ConnectionTestResult, ContractProbeResult, XpertDataSource


class FakeXpertDataSource(XpertDataSource):
    """In-memory datasource for tests — no SQL Server required."""

    def __init__(
        self,
        *,
        rows_by_query: dict[str, list[dict[str, Any]]] | None = None,
        privileges: dict[str, bool] | None = None,
        source_time: datetime | None = None,
        should_fail: bool = False,
    ) -> None:
        self.rows_by_query = rows_by_query or {}
        self.privileges = privileges or {
            "sysadmin": False,
            "db_owner": False,
            "db_datawriter": False,
        }
        self.source_time = source_time or datetime.now(UTC)
        self.should_fail = should_fail
        self.closed = False

    def test_connection(self) -> ConnectionTestResult:
        if self.should_fail:
            return ConnectionTestResult(status="DISCONNECTED", error="Connection refused")
        unsafe = any(self.privileges.get(k) for k in ("sysadmin", "db_owner", "db_datawriter"))
        return ConnectionTestResult(
            status="UNSAFE" if unsafe else "CONNECTED",
            latency_ms=12,
            server_version="Microsoft SQL Server 2022 (Fake)",
            database_name="***",
            source_utc_time=self.source_time,
            encryption=True,
            privileges=self.privileges,
            warnings=["Fake datasource"] if not unsafe else ["Unsafe privileges detected"],
        )

    def get_source_utc_time(self) -> datetime:
        return self.source_time

    def probe_contract(self, sql: str, parameters: dict[str, Any], limit: int = 5) -> ContractProbeResult:
        rows = self._rows_for_sql(sql)[:limit]
        columns = list(rows[0].keys()) if rows else []
        return ContractProbeResult(columns=columns, sample_rows=rows, row_count=len(rows))

    def stream_rows(
        self,
        sql: str,
        parameters: dict[str, Any],
        *,
        batch_size: int = 1000,
    ) -> Iterator[list[dict[str, Any]]]:
        if self.should_fail:
            raise RuntimeError("Simulated extraction failure")
        rows = self._rows_for_sql(sql)
        for i in range(0, len(rows), batch_size):
            yield rows[i : i + batch_size]

    def _rows_for_sql(self, sql: str) -> list[dict[str, Any]]:
        for key, rows in self.rows_by_query.items():
            if key in sql or sql.strip().startswith(key):
                return rows
        return self.rows_by_query.get("default", [])

    def close(self) -> None:
        self.closed = True
