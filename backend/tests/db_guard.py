"""Validação do banco de testes — impede uso acidental do banco de desenvolvimento."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from app.core.config import settings


class DatabaseGuardError(RuntimeError):
    pass


def _database_name(url: str) -> str:
    parsed = urlparse(url.replace("+asyncpg", "").replace("+psycopg", ""))
    path = parsed.path.lstrip("/")
    return path.split("?")[0]


def _to_sync_url(async_url: str) -> str:
    return async_url.replace("postgresql+asyncpg://", "postgresql+psycopg://")


def validate_test_database_config() -> tuple[str, str]:
    test_url = os.environ.get("TEST_DATABASE_URL") or settings.test_database_url
    if not test_url:
        raise DatabaseGuardError(
            "TEST_DATABASE_URL é obrigatória para executar testes. "
            "Configure um banco PostgreSQL exclusivo para testes."
        )

    app_url = settings.database_url
    if test_url == app_url:
        raise DatabaseGuardError(
            "O banco de testes não pode ser o mesmo que DATABASE_URL da aplicação."
        )

    test_db = _database_name(test_url)
    app_db = _database_name(app_url)
    if test_db == app_db:
        raise DatabaseGuardError(
            "O nome do banco de testes não pode ser igual ao banco da aplicação."
        )

    allow_unsafe = os.environ.get("TEST_DATABASE_ALLOW_UNSAFE", "").lower() in {"1", "true", "yes"}
    if "_test" not in test_db.lower() and not allow_unsafe:
        raise DatabaseGuardError(
            f"O banco '{test_db}' não parece ser de testes. "
            "Use um nome contendo '_test' ou defina TEST_DATABASE_ALLOW_UNSAFE=true "
            "somente se souber o risco."
        )

    sync_url = os.environ.get("TEST_DATABASE_URL_SYNC") or settings.test_database_url_sync
    if not sync_url:
        sync_url = _to_sync_url(test_url)

    return test_url, sync_url


def run_alembic_upgrade(sync_url: str) -> None:
    from alembic import command
    from alembic.config import Config

    os.environ["DATABASE_URL_SYNC"] = sync_url
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")
