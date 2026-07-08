import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.core.permissions import Permission, has_permission, permissions_for_roles
from app.core.security import (
    TokenValidationError,
    access_token_expires_in,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    parse_access_token,
    refresh_token_expires_at,
    verify_password,
)
from app.models.auth_session import AuthSession
from app.models.organization import Organization
from app.models.role import Role, UserRole
from app.models.station import Station
from app.models.user import User, UserStation
from app.services.audit_service import AuditContext, AuditService
from app.services.rate_limit import login_rate_limiter
from app.utils.email import normalize_email
from app.utils.password import validate_password


@dataclass
class AuthTokens:
    access_token: str
    expires_in: int
    refresh_token: str
    session_id: uuid.UUID


@dataclass
class AuthenticatedUser:
    id: uuid.UUID
    organization_id: uuid.UUID
    session_id: uuid.UUID
    name: str
    email: str
    role_codes: list[str]
    permissions: list[str]
    has_all_stations_access: bool
    must_change_password: bool
    active: bool


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)

    async def _load_user(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.role_links).selectinload(UserRole.role))
            .options(selectinload(User.station_links).selectinload(UserStation.station))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise AppError("Sessão inválida.", status_code=401, code="SESSION_EXPIRED")
        return user

    async def _role_codes(self, user: User) -> list[str]:
        return [link.role.code for link in user.role_links if link.role.active]

    def _to_authenticated(self, user: User, session_id: uuid.UUID) -> AuthenticatedUser:
        role_codes = [link.role.code for link in user.role_links if link.role.active]
        return AuthenticatedUser(
            id=user.id,
            organization_id=user.organization_id,
            session_id=session_id,
            name=user.name,
            email=user.email,
            role_codes=role_codes,
            permissions=permissions_for_roles(role_codes),
            has_all_stations_access=user.has_all_stations_access,
            must_change_password=user.must_change_password,
            active=user.active,
        )

    async def login(
        self,
        *,
        email: str,
        password: str,
        ip_address: str | None,
        user_agent: str | None,
        audit_ctx: AuditContext,
    ) -> tuple[AuthTokens, User]:
        await login_rate_limiter.check(ip_address=ip_address or "unknown", identifier=normalize_email(email))

        result = await self.db.execute(
            select(User)
            .options(selectinload(User.role_links).selectinload(UserRole.role))
            .where(User.normalized_email == normalize_email(email))
        )
        user = result.scalar_one_or_none()

        invalid = AppError(
            "E-mail ou senha inválidos.",
            status_code=401,
            code="INVALID_CREDENTIALS",
        )
        if user is None or not verify_password(password, user.password_hash):
            raise invalid
        if not user.active:
            raise invalid

        org = await self.db.get(Organization, user.organization_id)
        if org is None or not org.active:
            raise invalid

        now = datetime.now(UTC)
        user.last_login_at = now

        refresh_token = generate_refresh_token()
        family_id = uuid.uuid4()
        session = AuthSession(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            token_family_id=family_id,
            created_at=now,
            last_used_at=now,
            expires_at=refresh_token_expires_at(),
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(session)
        await self.db.flush()

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="auth_session",
            entity_id=session.id,
            action="login",
            after_data={"user_id": str(user.id)},
        )

        tokens = AuthTokens(
            access_token=create_access_token(
                user_id=user.id,
                organization_id=user.organization_id,
                session_id=session.id,
            ),
            expires_in=access_token_expires_in(),
            refresh_token=refresh_token,
            session_id=session.id,
        )
        return tokens, user

    async def refresh(self, *, refresh_token: str, ip_address: str | None) -> AuthTokens:
        token_hash = hash_refresh_token(refresh_token)
        result = await self.db.execute(
            select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        now = datetime.now(UTC)

        if session is None:
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        if session.revoked_at is not None:
            if session.revoked_reason == "rotated":
                await self._revoke_family(session.token_family_id, "token_reuse_detected")
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        if session.expires_at < now:
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        user = await self._load_user(session.user_id)
        if not user.active:
            session.revoked_at = now
            session.revoked_reason = "user_inactive"
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        org = await self.db.get(Organization, user.organization_id)
        if org is None or not org.active:
            session.revoked_at = now
            session.revoked_reason = "organization_inactive"
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        session.revoked_at = now
        session.revoked_reason = "rotated"

        new_refresh = generate_refresh_token()
        new_session = AuthSession(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(new_refresh),
            token_family_id=session.token_family_id,
            created_at=now,
            last_used_at=now,
            expires_at=refresh_token_expires_at(),
            ip_address=ip_address or session.ip_address,
            user_agent=session.user_agent,
        )
        self.db.add(new_session)
        await self.db.flush()

        return AuthTokens(
            access_token=create_access_token(
                user_id=user.id,
                organization_id=user.organization_id,
                session_id=new_session.id,
            ),
            expires_in=access_token_expires_in(),
            refresh_token=new_refresh,
            session_id=new_session.id,
        )

    async def _revoke_family(self, family_id: uuid.UUID, reason: str) -> None:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(AuthSession).where(
                AuthSession.token_family_id == family_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        for s in result.scalars().all():
            s.revoked_at = now
            s.revoked_reason = reason

    async def detect_reuse_and_revoke_family(self, refresh_token: str) -> None:
        token_hash = hash_refresh_token(refresh_token)
        result = await self.db.execute(
            select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        )
        session = result.scalar_one_or_none()
        if session is None:
            return
        now = datetime.now(UTC)
        family_sessions = await self.db.execute(
            select(AuthSession).where(
                AuthSession.token_family_id == session.token_family_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        for s in family_sessions.scalars().all():
            s.revoked_at = now
            s.revoked_reason = "token_reuse_detected"

    async def logout(self, *, session_id: uuid.UUID, audit_ctx: AuditContext) -> None:
        session = await self.db.get(AuthSession, session_id)
        if session and session.revoked_at is None:
            session.revoked_at = datetime.now(UTC)
            session.revoked_reason = "logout"
            await self.audit.log(
                ctx=audit_ctx,
                entity_type="auth_session",
                entity_id=session.id,
                action="logout",
            )

    async def revoke_all_user_sessions(self, user_id: uuid.UUID, reason: str) -> None:
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(AuthSession).where(
                AuthSession.user_id == user_id,
                AuthSession.revoked_at.is_(None),
            )
        )
        for session in result.scalars().all():
            session.revoked_at = now
            session.revoked_reason = reason

    async def get_current_user_from_token(self, token: str) -> AuthenticatedUser:
        try:
            user_id, org_id, session_id = parse_access_token(token)
        except TokenValidationError as exc:
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED") from exc

        session = await self.db.get(AuthSession, session_id)
        now = datetime.now(UTC)
        if session is None or session.revoked_at is not None or session.expires_at < now:
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        user = await self._load_user(user_id)
        if not user.active or user.organization_id != org_id:
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        org = await self.db.get(Organization, user.organization_id)
        if org is None or not org.active:
            raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

        return self._to_authenticated(user, session_id)

    async def change_password(
        self,
        *,
        user: AuthenticatedUser,
        current_password: str,
        new_password: str,
        audit_ctx: AuditContext,
        keep_session_id: uuid.UUID | None = None,
    ) -> AuthTokens:
        db_user = await self._load_user(user.id)
        if not verify_password(current_password, db_user.password_hash):
            raise AppError(
                "Senha atual inválida.",
                status_code=400,
                code="INVALID_CREDENTIALS",
            )

        validate_password(new_password, db_user.email)
        now = datetime.now(UTC)
        db_user.password_hash = hash_password(new_password)
        db_user.must_change_password = False
        db_user.password_changed_at = now

        await self.revoke_all_user_sessions(db_user.id, "password_changed")

        refresh_token = generate_refresh_token()
        session = AuthSession(
            user_id=db_user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            token_family_id=uuid.uuid4(),
            created_at=now,
            last_used_at=now,
            expires_at=refresh_token_expires_at(),
            ip_address=audit_ctx.ip_address,
        )
        self.db.add(session)
        await self.db.flush()

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=db_user.id,
            action="password_changed",
        )

        return AuthTokens(
            access_token=create_access_token(
                user_id=db_user.id,
                organization_id=db_user.organization_id,
                session_id=session.id,
            ),
            expires_in=access_token_expires_in(),
            refresh_token=refresh_token,
            session_id=session.id,
        )

    async def allowed_stations(self, user: AuthenticatedUser, *, include_inactive: bool = False) -> list[Station]:
        query = select(Station).where(Station.organization_id == user.organization_id)
        if not include_inactive:
            query = query.where(Station.active.is_(True))

        if user.has_all_stations_access:
            result = await self.db.execute(query.order_by(Station.trade_name))
            return list(result.scalars().all())

        station_ids = [link.station_id for link in (await self._load_user(user.id)).station_links]
        if not station_ids:
            return []
        query = query.where(Station.id.in_(station_ids)).order_by(Station.trade_name)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def ensure_station_access(self, user: AuthenticatedUser, station_id: uuid.UUID) -> Station:
        station = await self.db.get(Station, station_id)
        if station is None or station.organization_id != user.organization_id or not station.active:
            raise AppError(
                "Você não possui acesso ao posto selecionado.",
                status_code=403,
                code="STATION_ACCESS_DENIED",
            )
        if user.has_all_stations_access:
            return station

        result = await self.db.execute(
            select(UserStation).where(
                UserStation.user_id == user.id,
                UserStation.station_id == station_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise AppError(
                "Você não possui acesso ao posto selecionado.",
                status_code=403,
                code="STATION_ACCESS_DENIED",
            )
        return station

    async def count_active_admins(self, organization_id: uuid.UUID) -> int:
        admin_role = await self.db.execute(select(Role).where(Role.code == "ADMIN"))
        role = admin_role.scalar_one()
        result = await self.db.execute(
            select(func.count())
            .select_from(User)
            .join(UserRole, UserRole.user_id == User.id)
            .where(
                User.organization_id == organization_id,
                User.active.is_(True),
                UserRole.role_id == role.id,
            )
        )
        return int(result.scalar_one())

    def require_permission(self, user: AuthenticatedUser, permission: Permission) -> None:
        if not has_permission(user.role_codes, permission):
            raise AppError(
                "Você não possui permissão para executar esta ação.",
                status_code=403,
                code="FORBIDDEN",
            )
