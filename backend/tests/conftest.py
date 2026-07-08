import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base, get_db
from app.main import app
from app.models.organization import Organization
from app.models.role import Role, UserRole
from app.models.station import Station
from app.models.user import User
from factories import create_organization, create_station, create_user, login


@pytest.fixture(autouse=True)
def reset_login_rate_limit(monkeypatch) -> None:
    from app.services.rate_limit import login_rate_limiter

    monkeypatch.setattr(settings, "login_rate_limit", 1000)
    monkeypatch.setattr(settings, "login_rate_allow_memory_fallback", True)
    login_rate_limiter._memory.clear()


@pytest.fixture
async def db_engine():
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture
async def client(session_factory) -> AsyncGenerator[AsyncClient, None]:
    async with session_factory() as session:
        for code, name in [
            ("ADMIN", "Administrador"),
            ("GESTOR", "Gestor"),
            ("COMPRADOR", "Comprador"),
            ("FINANCEIRO", "Financeiro"),
            ("CONSULTA", "Consulta"),
        ]:
            session.add(Role(code=code, name=name, active=True))
        await session.commit()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def org(session_factory) -> Organization:
    async with session_factory() as session:
        organization = await create_organization(session)
        await session.commit()
        return organization


@pytest.fixture
async def headquarters(session_factory, org: Organization) -> Station:
    async with session_factory() as session:
        station = await create_station(
            session,
            organization_id=org.id,
            trade_name="Matriz",
            station_type="HEADQUARTERS",
            cnpj="11222333000262",
        )
        await session.commit()
        return station


@pytest.fixture
async def branch_station(session_factory, org: Organization) -> Station:
    async with session_factory() as session:
        station = await create_station(
            session,
            organization_id=org.id,
            trade_name="Filial 1",
            cnpj="11222333000343",
        )
        await session.commit()
        return station


@pytest.fixture
async def admin_user(session_factory, org: Organization) -> User:
    async with session_factory() as session:
        user = await create_user(
            session,
            organization_id=org.id,
            email="admin@test.com",
            role_codes=["ADMIN"],
            has_all_stations_access=True,
        )
        await session.commit()
        return user


@pytest.fixture
async def consulta_user(session_factory, org: Organization, branch_station: Station) -> User:
    async with session_factory() as session:
        user = await create_user(
            session,
            organization_id=org.id,
            email="consulta@test.com",
            role_codes=["CONSULTA"],
            station_ids=[branch_station.id],
        )
        await session.commit()
        return user


@pytest.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    token, _ = await login(client, "admin@test.com", "SenhaSegura123")
    return token


@pytest.fixture
async def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}
