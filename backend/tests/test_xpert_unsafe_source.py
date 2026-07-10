"""Testes de fonte XPERT UNSAFE — Sprint 6."""

from __future__ import annotations

import pytest

from app.core.xpert_sync_enums import ErpSecurityStatus
from app.integrations.xpert.source_security import (
    privileges_are_unsafe,
    security_status_from_test,
)


def test_sa_privileges_are_unsafe() -> None:
    priv = {"sysadmin": True, "db_owner": True, "db_datawriter": True}
    assert privileges_are_unsafe(priv) is True


def test_readonly_privileges_are_safe() -> None:
    priv = {"sysadmin": False, "db_owner": False, "db_datawriter": False, "db_insert": False}
    assert privileges_are_unsafe(priv) is False


def test_security_status_unsafe_with_sa() -> None:
    status = security_status_from_test(
        connection_status="CONNECTED",
        privileges={"sysadmin": True},
        allow_unsafe_override=True,
    )
    assert status == ErpSecurityStatus.UNSAFE


@pytest.mark.asyncio
async def test_scheduler_skips_unsafe_source(session_factory, db_engine):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.xpert_sync_enums import ErpConnectionStatus, ErpDatasetCode, ErpSyncRunStatus
    from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncRun
    from app.services.xpert_sync_service import XpertSyncService
    from tests.xpert_helpers import commit_org_context, commit_xpert_bundle

    ctx = await commit_org_context(session_factory)
    bundle = await commit_xpert_bundle(
        session_factory,
        organization_id=ctx["organization_id"],
        user_id=ctx["user_id"],
        station_id=ctx["station_id"],
    )
    async with session_factory() as session:
        async with session.begin():
            source = await session.get(ErpSource, bundle["source_id"])
            assert source is not None
            source.security_status = ErpSecurityStatus.UNSAFE
            source.connection_status = ErpConnectionStatus.CONNECTED
            dataset = (
                await session.execute(
                    select(ErpDataset).where(
                        ErpDataset.erp_source_id == source.id,
                        ErpDataset.code == ErpDatasetCode.PRODUCTS,
                    )
                )
            ).scalar_one()
            dataset.schedule_enabled = True
            dataset.enabled = True
            dataset.contract_status = "VALID"
            from datetime import UTC, datetime

            dataset.next_scheduled_at = datetime.now(UTC)

    async with db_engine.connect() as conn:
        async with conn.begin():
            session = AsyncSession(bind=conn, expire_on_commit=False)
            sync = XpertSyncService(session)
            created = await sync.create_scheduled_runs()
            assert created == 0

    async with session_factory() as session:
        async with session.begin():
            count = (
                await session.execute(
                    select(ErpSyncRun).where(
                        ErpSyncRun.erp_source_id == bundle["source_id"],
                        ErpSyncRun.trigger_type == "SCHEDULED",
                    )
                )
            ).scalars().all()
            assert len(count) == 0
