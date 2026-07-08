import uuid
from decimal import Decimal

from pydantic import BaseModel, Field


class OrganizationBusinessSettingsResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    default_supplier_allowed: bool
    default_minimum_volume_liters: Decimal
    updated_by: uuid.UUID | None

    model_config = {"from_attributes": True}


class OrganizationBusinessSettingsUpdate(BaseModel):
    default_supplier_allowed: bool | None = None
    default_minimum_volume_liters: Decimal | None = Field(default=None, gt=0)
