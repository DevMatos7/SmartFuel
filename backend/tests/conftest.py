import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.main import app
from app.models.organization import Organization
from app.models.station import Station
from app.models.user import User
from db_guard import run_alembic_upgrade, validate_test_database_config
from factories import create_organization, create_station, create_user, login, seed_master_data

_TEST_ASYNC_URL: str | None = None
_TEST_SYNC_URL: str | None = None
_migrations_applied = False


def _ensure_test_urls() -> tuple[str, str]:
    global _TEST_ASYNC_URL, _TEST_SYNC_URL
    if _TEST_ASYNC_URL is None:
        _TEST_ASYNC_URL, _TEST_SYNC_URL = validate_test_database_config()
    return _TEST_ASYNC_URL, _TEST_SYNC_URL


@pytest.fixture(scope="session", autouse=True)
def apply_test_migrations() -> None:
    global _migrations_applied
    _, sync_url = _ensure_test_urls()
    if not _migrations_applied:
        run_alembic_upgrade(sync_url)
        _migrations_applied = True


@pytest.fixture(autouse=True)
def reset_login_rate_limit(monkeypatch) -> None:
    from app.core.config import settings
    from app.services.rate_limit import login_rate_limiter

    monkeypatch.setattr(settings, "login_rate_limit", 1000)
    monkeypatch.setattr(settings, "login_rate_allow_memory_fallback", True)
    login_rate_limiter._memory.clear()


@pytest_asyncio.fixture
async def db_engine():
    async_url, _ = _ensure_test_urls()
    engine = create_async_engine(async_url, pool_pre_ping=True)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def session_factory(db_engine):
    return async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_connection(db_engine):
    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        yield connection
        await transaction.rollback()


@pytest_asyncio.fixture
async def db_session(db_connection) -> AsyncGenerator[AsyncSession, None]:
    session = AsyncSession(
        bind=db_connection,
        join_transaction_mode="create_savepoint",
        expire_on_commit=False,
    )
    yield session
    await session.close()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def org(db_session: AsyncSession) -> Organization:
    organization = await create_organization(db_session)
    await db_session.flush()
    return organization


@pytest_asyncio.fixture
async def headquarters(db_session: AsyncSession, org: Organization) -> Station:
    station = await create_station(
        db_session,
        organization_id=org.id,
        trade_name="Matriz",
        station_type="HEADQUARTERS",
        cnpj="11222333000262",
    )
    await db_session.flush()
    return station


@pytest_asyncio.fixture
async def branch_station(db_session: AsyncSession, org: Organization) -> Station:
    station = await create_station(
        db_session,
        organization_id=org.id,
        trade_name="Filial 1",
        cnpj="11222333000343",
    )
    await db_session.flush()
    return station


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession, org: Organization) -> User:
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="admin@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def consulta_user(db_session: AsyncSession, org: Organization, branch_station: Station) -> User:
    user = await create_user(
        db_session,
        organization_id=org.id,
        email="consulta@test.com",
        role_codes=["CONSULTA"],
        station_ids=[branch_station.id],
    )
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    token, _ = await login(client, "admin@test.com", "SenhaSegura123")
    return token


@pytest_asyncio.fixture
async def auth_headers(admin_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest_asyncio.fixture
async def seeded_org(db_session: AsyncSession, org: Organization) -> Organization:
    await seed_master_data(db_session, org.id)
    await db_session.flush()
    return org
