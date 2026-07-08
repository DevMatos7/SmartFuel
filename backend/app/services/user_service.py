import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.core.security import hash_password
from app.models.role import Role, UserRole
from app.models.station import Station
from app.models.user import User, UserStation
from app.services.audit_service import AuditContext, AuditService
from app.services.auth_service import AuthService, AuthenticatedUser
from app.utils.email import is_valid_email_format, normalize_email
from app.utils.password import validate_password


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.audit = AuditService(db)
        self.auth = AuthService(db)

    async def _get_roles_by_codes(self, codes: list[str]) -> list[Role]:
        result = await self.db.execute(select(Role).where(Role.code.in_(codes), Role.active.is_(True)))
        roles = list(result.scalars().all())
        if len(roles) != len(set(codes)):
            raise AppError("Perfil inválido.", status_code=400, code="VALIDATION_ERROR")
        return roles

    async def _load_user(self, user_id: uuid.UUID) -> User:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.role_links).selectinload(UserRole.role))
            .options(selectinload(User.station_links))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise AppError("Usuário não encontrado.", status_code=404, code="NOT_FOUND")
        return user

    async def list_users(
        self,
        *,
        organization_id: uuid.UUID,
        search: str | None = None,
        role: str | None = None,
        station_id: uuid.UUID | None = None,
        active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[User], int]:
        query = (
            select(User)
            .options(selectinload(User.role_links).selectinload(UserRole.role))
            .options(selectinload(User.station_links))
            .where(User.organization_id == organization_id)
        )
        if search:
            term = f"%{search}%"
            query = query.where(or_(User.name.ilike(term), User.email.ilike(term)))
        if active is not None:
            query = query.where(User.active.is_(active))
        if role:
            query = query.join(UserRole).join(Role).where(Role.code == role)
        if station_id:
            query = query.join(UserStation).where(UserStation.station_id == station_id)

        count_q = select(func.count()).select_from(query.distinct().subquery())
        total = int((await self.db.execute(count_q)).scalar_one())

        query = query.distinct().order_by(User.name).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def create_user(
        self,
        *,
        organization_id: uuid.UUID,
        data: dict,
        actor: AuthenticatedUser,
        audit_ctx: AuditContext,
    ) -> User:
        email = data["email"].strip()
        if not is_valid_email_format(email):
            raise AppError("E-mail inválido.", status_code=400, code="VALIDATION_ERROR")
        normalized = normalize_email(email)
        dup = await self.db.execute(select(User).where(User.normalized_email == normalized))
        if dup.scalar_one_or_none():
            raise AppError("E-mail já cadastrado.", status_code=409, code="EMAIL_ALREADY_EXISTS")

        role_codes = data.get("role_codes", [])
        if not role_codes:
            raise AppError("Usuário deve possuir ao menos um perfil.", status_code=400, code="VALIDATION_ERROR")

        has_all = data.get("has_all_stations_access", False)
        if has_all and "ADMIN" not in role_codes:
            raise AppError(
                "Acesso total aos postos é permitido apenas para ADMIN.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        station_ids = data.get("station_ids", [])
        if not has_all and not station_ids:
            raise AppError(
                "Usuário deve possuir ao menos um posto ou acesso total.",
                status_code=400,
                code="VALIDATION_ERROR",
            )

        password = data.get("temporary_password") or secrets.token_urlsafe(10)
        validate_password(password, email)

        user = User(
            organization_id=organization_id,
            name=data["name"],
            email=email,
            normalized_email=normalized,
            password_hash=hash_password(password),
            active=data.get("active", True),
            must_change_password=data.get("must_change_password", True),
            has_all_stations_access=has_all,
        )
        self.db.add(user)
        await self.db.flush()

        roles = await self._get_roles_by_codes(role_codes)
        for role in roles:
            self.db.add(UserRole(user_id=user.id, role_id=role.id, created_by=actor.id, created_at=datetime.now(UTC)))

        if not has_all:
            for sid in station_ids:
                self.db.add(
                    UserStation(
                        user_id=user.id,
                        station_id=uuid.UUID(str(sid)),
                        created_by=actor.id,
                        created_at=datetime.now(UTC),
                    )
                )

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=user.id,
            action="create",
            after_data=self._serialize(user, role_codes, station_ids, has_all),
        )
        return user

    async def update_user(
        self,
        *,
        user: User,
        data: dict,
        actor: AuthenticatedUser,
        audit_ctx: AuditContext,
    ) -> User:
        before = self._serialize_user(user)
        if user.id == actor.id and data.get("active") is False:
            raise AppError("Você não pode inativar a si próprio.", status_code=400, code="VALIDATION_ERROR")

        if "name" in data:
            user.name = data["name"]
        if "email" in data:
            email = data["email"].strip()
            normalized = normalize_email(email)
            dup = await self.db.execute(
                select(User).where(User.normalized_email == normalized, User.id != user.id)
            )
            if dup.scalar_one_or_none():
                raise AppError("E-mail já cadastrado.", status_code=409, code="EMAIL_ALREADY_EXISTS")
            user.email = email
            user.normalized_email = normalized

        if "active" in data and data["active"] is False:
            await self._ensure_not_last_admin(user)
            user.active = False
            await self.auth.revoke_all_user_sessions(user.id, "user_deactivated")

        if "active" in data and data["active"] is True:
            user.active = True

        if "has_all_stations_access" in data:
            has_all = data["has_all_stations_access"]
            role_codes = [link.role.code for link in user.role_links]
            if has_all and "ADMIN" not in role_codes:
                raise AppError(
                    "Acesso total aos postos é permitido apenas para ADMIN.",
                    status_code=400,
                    code="VALIDATION_ERROR",
                )
            user.has_all_stations_access = has_all

        user.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=user.id,
            action="update",
            before_data=before,
            after_data=self._serialize_user(user),
        )
        return user

    async def set_roles(
        self,
        *,
        user: User,
        role_codes: list[str],
        actor: AuthenticatedUser,
        audit_ctx: AuditContext,
    ) -> User:
        if not role_codes:
            raise AppError("Usuário deve possuir ao menos um perfil.", status_code=400, code="VALIDATION_ERROR")

        current_codes = [link.role.code for link in user.role_links]
        removing_admin = "ADMIN" in current_codes and "ADMIN" not in role_codes
        if removing_admin:
            await self._ensure_not_last_admin(user)

        before = {"role_codes": current_codes}
        for link in list(user.role_links):
            await self.db.delete(link)
        await self.db.flush()

        roles = await self._get_roles_by_codes(role_codes)
        for role in roles:
            self.db.add(UserRole(user_id=user.id, role_id=role.id, created_by=actor.id, created_at=datetime.now(UTC)))

        if user.has_all_stations_access and "ADMIN" not in role_codes:
            user.has_all_stations_access = False

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=user.id,
            action="roles_updated",
            before_data=before,
            after_data={"role_codes": role_codes},
        )
        return user

    async def set_stations(
        self,
        *,
        user: User,
        station_ids: list[uuid.UUID],
        has_all_stations_access: bool,
        actor: AuthenticatedUser,
        audit_ctx: AuditContext,
    ) -> User:
        role_codes = [link.role.code for link in user.role_links]
        if has_all_stations_access and "ADMIN" not in role_codes:
            raise AppError(
                "Acesso total aos postos é permitido apenas para ADMIN.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        if not has_all_stations_access and not station_ids:
            raise AppError(
                "Usuário deve possuir ao menos um posto ou acesso total.",
                status_code=400,
                code="VALIDATION_ERROR",
            )
        if user.id == actor.id and not has_all_stations_access and not station_ids:
            raise AppError("Você não pode remover todos os seus postos.", status_code=400, code="VALIDATION_ERROR")

        before = {
            "station_ids": [str(link.station_id) for link in user.station_links],
            "has_all_stations_access": user.has_all_stations_access,
        }

        for link in list(user.station_links):
            await self.db.delete(link)
        await self.db.flush()

        user.has_all_stations_access = has_all_stations_access
        if not has_all_stations_access:
            for sid in station_ids:
                station = await self.db.get(Station, sid)
                if station is None or station.organization_id != user.organization_id:
                    raise AppError("Posto inválido.", status_code=400, code="VALIDATION_ERROR")
                self.db.add(
                    UserStation(
                        user_id=user.id,
                        station_id=sid,
                        created_by=actor.id,
                        created_at=datetime.now(UTC),
                    )
                )

        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=user.id,
            action="stations_updated",
            before_data=before,
            after_data={
                "station_ids": [str(s) for s in station_ids],
                "has_all_stations_access": has_all_stations_access,
            },
        )
        return user

    async def reset_password(
        self,
        *,
        user: User,
        temporary_password: str | None,
        must_change_password: bool,
        audit_ctx: AuditContext,
    ) -> str:
        password = temporary_password or secrets.token_urlsafe(10)
        validate_password(password, user.email)
        user.password_hash = hash_password(password)
        user.must_change_password = must_change_password
        user.password_changed_at = datetime.now(UTC)
        await self.auth.revoke_all_user_sessions(user.id, "password_reset")
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=user.id,
            action="password_reset",
        )
        return password

    async def deactivate(self, *, user: User, reason: str, actor: AuthenticatedUser, audit_ctx: AuditContext) -> User:
        if user.id == actor.id:
            raise AppError("Você não pode inativar a si próprio.", status_code=400, code="VALIDATION_ERROR")
        await self._ensure_not_last_admin(user)
        before = self._serialize_user(user)
        user.active = False
        user.updated_at = datetime.now(UTC)
        await self.auth.revoke_all_user_sessions(user.id, "user_deactivated")
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=user.id,
            action="deactivate",
            before_data=before,
            after_data=self._serialize_user(user),
            metadata={"reason": reason},
        )
        return user

    async def reactivate(self, *, user: User, audit_ctx: AuditContext) -> User:
        before = self._serialize_user(user)
        user.active = True
        user.updated_at = datetime.now(UTC)
        await self.audit.log(
            ctx=audit_ctx,
            entity_type="user",
            entity_id=user.id,
            action="reactivate",
            before_data=before,
            after_data=self._serialize_user(user),
        )
        return user

    async def _ensure_not_last_admin(self, user: User) -> None:
        codes = [link.role.code for link in user.role_links]
        if "ADMIN" not in codes:
            return
        count = await self.auth.count_active_admins(user.organization_id)
        if count <= 1 and user.active:
            raise AppError(
                "A operação não pode remover o último administrador ativo.",
                status_code=409,
                code="LAST_ADMIN_PROTECTION",
            )

    def _serialize_user(self, user: User) -> dict:
        return {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "active": user.active,
            "has_all_stations_access": user.has_all_stations_access,
            "must_change_password": user.must_change_password,
            "role_codes": [link.role.code for link in user.role_links],
            "station_ids": [str(link.station_id) for link in user.station_links],
        }

    def _serialize(
        self,
        user: User,
        role_codes: list[str],
        station_ids: list,
        has_all: bool,
    ) -> dict:
        return {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "active": user.active,
            "role_codes": role_codes,
            "station_ids": [str(s) for s in station_ids],
            "has_all_stations_access": has_all,
        }
