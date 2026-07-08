import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(*, user_id: uuid.UUID, organization_id: uuid.UUID, session_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "session_id": str(session_id),
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def access_token_expires_in() -> int:
    return settings.access_token_expire_minutes * 60


def refresh_token_expires_at() -> datetime:
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)


class TokenValidationError(Exception):
    pass


def parse_access_token(token: str) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    try:
        payload = decode_access_token(token)
        if payload.get("type") != "access":
            raise TokenValidationError("invalid token type")
        return (
            uuid.UUID(payload["sub"]),
            uuid.UUID(payload["org_id"]),
            uuid.UUID(payload["session_id"]),
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise TokenValidationError("invalid token") from exc
