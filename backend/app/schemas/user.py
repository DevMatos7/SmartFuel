import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    name: str = Field(max_length=150)
    email: EmailStr
    temporary_password: str | None = None
    role_codes: list[str]
    station_ids: list[uuid.UUID] = Field(default_factory=list)
    has_all_stations_access: bool = False
    must_change_password: bool = True
    active: bool = True


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=150)
    email: EmailStr | None = None
    active: bool | None = None
    has_all_stations_access: bool | None = None


class UserRolesUpdate(BaseModel):
    role_codes: list[str]


class UserStationsUpdate(BaseModel):
    station_ids: list[uuid.UUID] = Field(default_factory=list)
    has_all_stations_access: bool = False


class ResetPasswordRequest(BaseModel):
    temporary_password: str | None = None
    must_change_password: bool = True


class ResetPasswordResponse(BaseModel):
    temporary_password: str
    message: str = "Senha temporária gerada com sucesso."


class UserResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    email: str
    active: bool
    must_change_password: bool
    has_all_stations_access: bool
    last_login_at: datetime | None
    role_codes: list[str] = Field(default_factory=list)
    station_ids: list[uuid.UUID] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    page: int
    page_size: int
