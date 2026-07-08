from datetime import UTC, datetime

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DetailedHealthResponse(HealthResponse):
    database: str = "unknown"
    redis: str = "unknown"
    minio: str = "unknown"
    environment: str
