"""Adaptadores de fontes externas — Sprint 9."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.external_data_enums import ExternalSourceStatus, ExternalSourceType
from app.services.external_data.observation_service import ObservationCandidate


@dataclass
class AdapterCapabilities:
    supports_historical_backfill: bool = False
    supports_incremental: bool = False
    supports_revisions: bool = True
    supports_intraday: bool = False
    supports_scheduling: bool = False
    requires_credentials: bool = False


@dataclass
class AdapterFetchResult:
    candidates: list[ObservationCandidate] = field(default_factory=list)
    raw_payload: dict[str, Any] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)


class ExternalSourceAdapter(ABC):
    source_type: ExternalSourceType

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    @abstractmethod
    def capabilities(self) -> AdapterCapabilities: ...

    @abstractmethod
    def validate_config(self) -> list[str]:
        """Retorna lista de erros; vazia se OK."""

    def connector_status(self) -> str:
        errors = self.validate_config()
        if errors:
            return ExternalSourceStatus.MISCONFIGURED.value
        return ExternalSourceStatus.READY_FOR_MANUAL.value

    @abstractmethod
    async def fetch(self, **kwargs: Any) -> AdapterFetchResult: ...


class ManualExternalSourceAdapter(ExternalSourceAdapter):
    source_type = ExternalSourceType.MANUAL

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(supports_revisions=True, supports_scheduling=False)

    def validate_config(self) -> list[str]:
        return []

    async def fetch(self, **kwargs: Any) -> AdapterFetchResult:
        candidates = kwargs.get("candidates") or []
        return AdapterFetchResult(candidates=list(candidates))


class CsvExternalSourceAdapter(ExternalSourceAdapter):
    source_type = ExternalSourceType.CSV

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            supports_historical_backfill=True,
            supports_incremental=False,
            supports_revisions=True,
            supports_scheduling=False,
        )

    def validate_config(self) -> list[str]:
        return []

    async def fetch(self, **kwargs: Any) -> AdapterFetchResult:
        # Parsing é feito pelo ExternalImportService; adapter apenas declara capacidade.
        return AdapterFetchResult(candidates=list(kwargs.get("candidates") or []))


class XlsxExternalSourceAdapter(ExternalSourceAdapter):
    source_type = ExternalSourceType.XLSX

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            supports_historical_backfill=True,
            supports_revisions=True,
        )

    def validate_config(self) -> list[str]:
        return []

    async def fetch(self, **kwargs: Any) -> AdapterFetchResult:
        return AdapterFetchResult(candidates=list(kwargs.get("candidates") or []))


class ApiExternalSourceAdapter(ExternalSourceAdapter):
    source_type = ExternalSourceType.API

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            supports_historical_backfill=True,
            supports_incremental=True,
            supports_revisions=True,
            supports_intraday=bool(self.config.get("supports_intraday")),
            supports_scheduling=True,
            requires_credentials=bool(self.config.get("requires_credentials", True)),
        )

    def validate_config(self) -> list[str]:
        errors: list[str] = []
        if not self.config.get("base_url"):
            errors.append("base_url obrigatório para adapter API")
        if self.capabilities().requires_credentials and not self.config.get("secret_ref"):
            errors.append("secret_ref obrigatório quando requires_credentials=true")
        # Sem endpoint concreto homologado → permanece misconfigured se não houver contract_validated
        if not self.config.get("contract_validated"):
            errors.append("contrato da API ainda não validado (contract_validated=false)")
        return errors

    async def fetch(self, **kwargs: Any) -> AdapterFetchResult:
        # Não inventar endpoints. Sync real só após contract_validated.
        return AdapterFetchResult(
            errors=[{"code": "CONTRACT_NOT_VALIDATED", "message": "API não homologada; use importação manual"}]
        )


class AuthorizedWebSourceAdapter(ExternalSourceAdapter):
    """Portal autenticado — nunca scraping genérico / CAPTCHA bypass."""

    source_type = ExternalSourceType.AUTHORIZED_WEB

    def capabilities(self) -> AdapterCapabilities:
        return AdapterCapabilities(
            supports_scheduling=False,
            requires_credentials=True,
        )

    def validate_config(self) -> list[str]:
        errors = [
            "mecanismo CSOnline/web ainda não confirmado",
            "scheduler_enabled deve permanecer false",
        ]
        if not self.config.get("authorized_mechanism"):
            errors.append("authorized_mechanism ausente (API|FILE|EMAIL|MANUAL_DOWNLOAD)")
        return errors

    def connector_status(self) -> str:
        return ExternalSourceStatus.MISCONFIGURED.value

    async def fetch(self, **kwargs: Any) -> AdapterFetchResult:
        return AdapterFetchResult(
            errors=[
                {
                    "code": "MISCONFIGURED",
                    "message": "CSOnline/web: confirme mecanismo autorizado antes da automação",
                }
            ]
        )


def get_adapter(source_type: str, config: dict[str, Any] | None = None) -> ExternalSourceAdapter:
    mapping: dict[str, type[ExternalSourceAdapter]] = {
        ExternalSourceType.MANUAL.value: ManualExternalSourceAdapter,
        ExternalSourceType.CSV.value: CsvExternalSourceAdapter,
        ExternalSourceType.XLSX.value: XlsxExternalSourceAdapter,
        ExternalSourceType.API.value: ApiExternalSourceAdapter,
        ExternalSourceType.AUTHORIZED_WEB.value: AuthorizedWebSourceAdapter,
    }
    cls = mapping.get(source_type)
    if cls is None:
        raise ValueError(f"source_type desconhecido: {source_type}")
    return cls(config)
