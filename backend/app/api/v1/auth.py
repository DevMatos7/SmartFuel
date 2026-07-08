from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_audit_context, get_current_user
from app.core.exceptions import AppError
from app.models.organization import Organization
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    MeResponse,
    MessageResponse,
    OrganizationSummary,
    StationSummary,
    TokenResponse,
    LoginUserResponse,
)
from app.services.audit_service import AuditContext
from app.services.auth_service import AuthService, AuthenticatedUser
from app.utils.password import validate_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    max_age = settings.refresh_token_expire_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        max_age=max_age,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.refresh_cookie_name, path="/api/v1/auth")


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> TokenResponse:
    auth = AuthService(db)
    tokens, user = await auth.login(
        email=str(payload.email),
        password=payload.password,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        audit_ctx=audit_ctx,
    )
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return TokenResponse(
        access_token=tokens.access_token,
        expires_in=tokens.expires_in,
        user=LoginUserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            must_change_password=user.must_change_password,
        ),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    refresh_token = request.cookies.get(settings.refresh_cookie_name)
    if not refresh_token:
        raise AppError("Sua sessão expirou. Entre novamente.", status_code=401, code="SESSION_EXPIRED")

    auth = AuthService(db)
    try:
        tokens = await auth.refresh(
            refresh_token=refresh_token,
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()
    except AppError:
        await auth.detect_reuse_and_revoke_family(refresh_token)
        await db.commit()
        raise

    _set_refresh_cookie(response, tokens.refresh_token)
    return TokenResponse(access_token=tokens.access_token, expires_in=tokens.expires_in)


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> MessageResponse:
    auth = AuthService(db)
    await auth.logout(session_id=user.session_id, audit_ctx=audit_ctx)
    await db.commit()
    _clear_refresh_cookie(response)
    return MessageResponse(message="Sessão encerrada com sucesso.")


@router.get("/me", response_model=MeResponse)
async def me(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MeResponse:
    auth = AuthService(db)
    db_user = await auth._load_user(user.id)
    org = await db.get(Organization, user.organization_id)
    stations = await auth.allowed_stations(user)
    return MeResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        organization=OrganizationSummary(id=org.id, name=org.name) if org else OrganizationSummary(id=user.organization_id, name=""),
        roles=user.role_codes,
        permissions=user.permissions,
        stations=[
            StationSummary(id=s.id, trade_name=s.trade_name, station_type=s.station_type, active=s.active)
            for s in stations
        ],
        has_all_stations_access=user.has_all_stations_access,
        must_change_password=user.must_change_password,
        last_login_at=db_user.last_login_at,
    )


@router.post("/change-password", response_model=TokenResponse)
async def change_password(
    payload: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    audit_ctx: AuditContext = Depends(get_audit_context),
) -> TokenResponse:
    if payload.new_password != payload.new_password_confirmation:
        raise AppError("A confirmação da senha não confere.", status_code=400, code="VALIDATION_ERROR")
    validate_password(payload.new_password, user.email)

    auth = AuthService(db)
    tokens = await auth.change_password(
        user=user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        audit_ctx=audit_ctx,
    )
    await db.commit()
    _set_refresh_cookie(response, tokens.refresh_token)
    return TokenResponse(access_token=tokens.access_token, expires_in=tokens.expires_in)
