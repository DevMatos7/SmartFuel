from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

ServiceStatus = Literal["healthy", "unhealthy"]
OverallStatus = Literal["healthy", "degraded", "unhealthy"]

API_SERVICE_NAME = "inteligencia-auto-postos-api"


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = API_SERVICE_NAME
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ServiceHealth(BaseModel):
    status: ServiceStatus
    response_time_ms: int | None = None
    message: str | None = None


class ServicesHealthMap(BaseModel):
    api: ServiceHealth
    database: ServiceHealth
    redis: ServiceHealth
    object_storage: ServiceHealth


class DetailedHealthResponse(BaseModel):
    status: OverallStatus
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    version: str
    services: ServicesHealthMap
