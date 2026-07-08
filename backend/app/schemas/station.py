import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StationCreate(BaseModel):
    organization_id: uuid.UUID
    station_type: str
    erp_branch_id: str | None = None
    corporate_name: str = Field(max_length=200)
    trade_name: str = Field(max_length=200)
    cnpj: str
    anp_code: str | None = None
    brand_type: str
    brand_name: str | None = None
    timezone: str = "America/Cuiaba"
    active: bool = True


class StationUpdate(BaseModel):
    station_type: str | None = None
    erp_branch_id: str | None = None
    corporate_name: str | None = Field(default=None, max_length=200)
    trade_name: str | None = Field(default=None, max_length=200)
    cnpj: str | None = None
    anp_code: str | None = None
    brand_type: str | None = None
    brand_name: str | None = None
    timezone: str | None = None
    active: bool | None = None


class StationResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    station_type: str
    erp_branch_id: str | None
    corporate_name: str
    trade_name: str
    cnpj: str
    anp_code: str | None
    brand_type: str
    brand_name: str | None
    timezone: str
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StationListResponse(BaseModel):
    items: list[StationResponse]
    total: int
    page: int
    page_size: int


class DeactivateRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
