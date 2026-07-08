import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginUserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    must_change_password: bool


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: LoginUserResponse | None = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    new_password_confirmation: str


class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str


class StationSummary(BaseModel):
    id: uuid.UUID
    trade_name: str
    station_type: str
    active: bool = True


class MeResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    organization: OrganizationSummary
    roles: list[str]
    permissions: list[str]
    stations: list[StationSummary]
    has_all_stations_access: bool
    must_change_password: bool
    last_login_at: datetime | None = None


class MessageResponse(BaseModel):
    message: str
