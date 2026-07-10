from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FinancialParameterCreate(BaseModel):
    annual_effective_rate: Decimal = Field(..., ge=0)
    day_count_basis: int = Field(default=365, gt=0)
    valid_from: datetime
    valid_until: datetime | None = None
    methodology_version: str | None = None
    notes: str | None = None


class FinancialParameterCloseValidity(BaseModel):
    valid_until: datetime
    reason: str | None = None


class FinancialParameterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    annual_effective_rate: Decimal
    day_count_basis: int
    methodology_version: str
    valid_from: datetime
    valid_until: datetime | None
    notes: str | None
    active: bool
    created_by: uuid.UUID
    created_at: datetime
    updated_by: uuid.UUID | None
    updated_at: datetime


class FinancialParameterListResponse(BaseModel):
    items: list[FinancialParameterResponse]
    total: int
    page: int
    page_size: int
