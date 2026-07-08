import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID | None
    user_id: uuid.UUID | None
    entity_type: str
    entity_id: uuid.UUID | None
    action: str
    before_data: dict | None
    after_data: dict | None
    metadata: dict | None = Field(alias="metadata_")
    ip_address: str | None
    request_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
