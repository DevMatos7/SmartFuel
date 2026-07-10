from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator


@dataclass
class ConnectionTestResult:
    status: str
    latency_ms: int | None = None
    server_version: str | None = None
    database_name: str | None = None
    source_utc_time: datetime | None = None
    encryption: bool = True
    privileges: dict[str, bool] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None


@dataclass
class ContractProbeResult:
    columns: list[str]
    sample_rows: list[dict[str, Any]]
    row_count: int


class XpertDataSource(ABC):
    @abstractmethod
    def test_connection(self) -> ConnectionTestResult: ...

    @abstractmethod
    def get_source_utc_time(self) -> datetime: ...

    @abstractmethod
    def probe_contract(self, sql: str, parameters: dict[str, Any], limit: int = 5) -> ContractProbeResult: ...

    @abstractmethod
    def stream_rows(
        self,
        sql: str,
        parameters: dict[str, Any],
        *,
        batch_size: int = 1000,
    ) -> Iterator[list[dict[str, Any]]]: ...

    @abstractmethod
    def close(self) -> None: ...
