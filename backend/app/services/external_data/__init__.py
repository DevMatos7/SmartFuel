"""__init__ pacote external_data services."""

from app.services.external_data.adapters import get_adapter
from app.services.external_data.freshness_service import ExternalFreshnessService
from app.services.external_data.observation_service import (
    ExternalObservationService,
    ObservationCandidate,
)

__all__ = [
    "ExternalFreshnessService",
    "ExternalObservationService",
    "ObservationCandidate",
    "get_adapter",
]
