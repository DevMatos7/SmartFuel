import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationCreate(BaseModel):
    name: str = Field(max_length=150)
    corporate_name: str = Field(max_length=200)
    cnpj: str
    timezone: str = "America/Cuiaba"
    active: bool = True


class OrganizationUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    corporate_name: str | None = Field(default=None, max_length=200)
    cnpj: str | None = None
    timezone: str | None = None
    active: bool | None = None


class OrganizationResponse(BaseModel):
    id: uuid.UUID
    name: str
    corporate_name: str
    cnpj: str
    timezone: str
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
