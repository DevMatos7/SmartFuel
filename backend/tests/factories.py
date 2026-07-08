import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.organization import Organization
from app.models.role import Role, UserRole
from app.models.station import Station
from app.models.user import User, UserStation
from app.utils.email import normalize_email


async def get_role(session: AsyncSession, code: str) -> Role:
    from sqlalchemy import select

    result = await session.execute(select(Role).where(Role.code == code))
    return result.scalar_one()


async def create_organization(session: AsyncSession, *, cnpj: str = "11222333000181") -> Organization:
    org = Organization(
        name="Org Teste",
        corporate_name="Org Teste LTDA",
        cnpj=cnpj,
        timezone="America/Cuiaba",
        active=True,
    )
    session.add(org)
    await session.flush()
    return org


async def create_station(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    trade_name: str,
    station_type: str = "BRANCH",
    cnpj: str,
    active: bool = True,
) -> Station:
    station = Station(
        organization_id=organization_id,
        station_type=station_type,
        corporate_name=f"{trade_name} LTDA",
        trade_name=trade_name,
        cnpj=cnpj,
        brand_type="WHITE_LABEL",
        timezone="America/Cuiaba",
        active=active,
    )
    session.add(station)
    await session.flush()
    return station


async def create_user(
    session: AsyncSession,
    *,
    organization_id: uuid.UUID,
    email: str,
    password: str = "SenhaSegura123",
    role_codes: list[str],
    station_ids: list[uuid.UUID] | None = None,
    has_all_stations_access: bool = False,
    must_change_password: bool = False,
    active: bool = True,
    name: str | None = None,
) -> User:
    user = User(
        organization_id=organization_id,
        name=name or email.split("@")[0],
        email=email,
        normalized_email=normalize_email(email),
        password_hash=hash_password(password),
        active=active,
        must_change_password=must_change_password,
        has_all_stations_access=has_all_stations_access,
    )
    session.add(user)
    await session.flush()

    for code in role_codes:
        role = await get_role(session, code)
        session.add(UserRole(user_id=user.id, role_id=role.id, created_at=datetime.now(UTC)))

    if station_ids:
        for station_id in station_ids:
            session.add(
                UserStation(
                    user_id=user.id,
                    station_id=station_id,
                    created_at=datetime.now(UTC),
                )
            )

    await session.flush()
    return user


async def login(client, email: str, password: str) -> tuple[str, dict]:
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    data = response.json()
    return data["access_token"], data


async def seed_master_data(session: AsyncSession, org_id: uuid.UUID) -> dict[str, int | str]:
    from app.services.master_data_bootstrap_service import MasterDataBootstrapService

    bootstrap = MasterDataBootstrapService(session)
    return await bootstrap.bootstrap_organization(organization_id=org_id)
