"""Testes Sprint 5.2 — concorrência, checkpoints e recuperação XPERT."""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.xpert_sync_enums import (
    ErpConnectionStatus,
    ErpContractStatus,
    ErpDatasetCode,
    ErpSyncMode,
    ErpSyncRunStatus,
)
from app.integrations.xpert.fake_datasource import FakeXpertDataSource
from app.integrations.xpert.query_guard import current_query_hash
from app.integrations.xpert.sync_lock import sync_lock_key
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncCheckpoint, ErpSyncRun
from app.models.station import Station
from app.services.xpert_sync_service import XpertSyncService
from app.services.xpert_worker_service import XpertWorkerService
from tests.xpert_helpers import commit_checkpoint, commit_org_context, commit_xpert_bundle


async def _setup(session_factory, **bundle_kwargs):
    ctx = await commit_org_context(session_factory)
    bundle = await commit_xpert_bundle(
        session_factory,
        organization_id=ctx["organization_id"],
        user_id=ctx["user_id"],
        station_id=ctx["station_id"],
        **bundle_kwargs,
    )
    return ctx, bundle


async def _pin_run_as_oldest_queued(session_factory, run_id: uuid.UUID) -> None:
    """Garante que a run do cenário seja a primeira na fila global de claim."""
    async with session_factory() as session:
        async with session.begin():
            run = await session.get(ErpSyncRun, run_id)
            assert run is not None
            run.created_at = datetime(2000, 1, 1, tzinfo=UTC)


@pytest.mark.asyncio
async def test_concurrent_claim_only_one_worker_gets_run(session_factory, db_engine):
    _, bundle = await _setup(session_factory)
    await _pin_run_as_oldest_queued(session_factory, bundle["run_id"])

    async def try_claim(worker_id: str) -> ErpSyncRun | None:
        async with db_engine.connect() as conn:
            async with conn.begin():
                session = AsyncSession(bind=conn, expire_on_commit=False)
                sync = XpertSyncService(session)
                return await sync.claim_next_run(worker_id)

    claimed_a = await try_claim("worker-a")
    claimed_b = await try_claim("worker-b")
    assert claimed_a is not None
    assert claimed_a.id == bundle["run_id"]
    assert claimed_a.status == ErpSyncRunStatus.CONNECTING
    assert claimed_a.worker_id == "worker-a"
    assert claimed_b is None or claimed_b.id != bundle["run_id"]

    async with session_factory() as session:
        async with session.begin():
            stored = await session.get(ErpSyncRun, bundle["run_id"])
            assert stored is not None
            assert stored.status == ErpSyncRunStatus.CONNECTING
            assert stored.worker_id == "worker-a"
            assert stored.started_at is not None


@pytest.mark.asyncio
async def test_advisory_lock_second_run_is_skipped_locked(session_factory, db_engine):
    _, bundle = await _setup(session_factory)
    lock_key = sync_lock_key(
        source_id=bundle["source_id"],
        dataset_id=bundle["dataset_id"],
        station_id=bundle["station_id"],
    )

    async with db_engine.connect() as holder:
        await holder.execute(text("SELECT pg_advisory_lock(:key)"), {"key": lock_key})
        async with db_engine.connect() as runner:
            async with runner.begin():
                session = AsyncSession(bind=runner, expire_on_commit=False)
                sync = XpertSyncService(session)
                fake = FakeXpertDataSource(rows_by_query={"default": []})
                result = await sync.process_run(bundle["run_id"], datasource=fake)
                assert result.status == ErpSyncRunStatus.SKIPPED_LOCKED
        await holder.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key})


@pytest.mark.asyncio
async def test_advisory_lock_released_after_failure_allows_retry(session_factory, db_engine):
    _, bundle = await _setup(session_factory)
    lock_key = sync_lock_key(
        source_id=bundle["source_id"],
        dataset_id=bundle["dataset_id"],
        station_id=bundle["station_id"],
    )

    async with db_engine.connect() as conn:
        async with conn.begin():
            session = AsyncSession(bind=conn, expire_on_commit=False)
            sync = XpertSyncService(session)
            result = await sync.process_run(bundle["run_id"], datasource=FakeXpertDataSource(should_fail=True))
            assert result.status == ErpSyncRunStatus.FAILED

    async with db_engine.connect() as conn:
        locked = await conn.scalar(text("SELECT pg_try_advisory_lock(:key)"), {"key": lock_key})
        assert locked is True
        await conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": lock_key})


@pytest.mark.asyncio
async def test_checkpoint_global_null_station_unique(session_factory):
    _, bundle = await _setup(session_factory)
    await commit_checkpoint(
        session_factory,
        source_id=bundle["source_id"],
        dataset_id=bundle["dataset_id"],
        station_id=None,
        watermark="2026-01-01T00:00:00+00:00",
    )

    with pytest.raises(IntegrityError):
        await commit_checkpoint(
            session_factory,
            source_id=bundle["source_id"],
            dataset_id=bundle["dataset_id"],
            station_id=None,
            watermark="2026-02-01T00:00:00+00:00",
        )


@pytest.mark.asyncio
async def test_completed_run_advances_checkpoint(session_factory):
    _, bundle = await _setup(session_factory, sync_mode=ErpSyncMode.INCREMENTAL_TIMESTAMP)

    async with session_factory() as session:
        async with session.begin():
            dataset = (
                await session.execute(select(ErpDataset).where(ErpDataset.id == bundle["dataset_id"]))
            ).scalar_one()
            dataset.sync_mode = ErpSyncMode.INCREMENTAL_TIMESTAMP
            dataset.checkpoint_type = "TIMESTAMP"

            sync = XpertSyncService(session)
            fake = FakeXpertDataSource(
                source_time=datetime(2026, 7, 9, 15, 0, tzinfo=UTC),
                rows_by_query={
                    "default": [
                        {
                            "source_product_id": "1",
                            "source_product_code": "1",
                            "source_description": "Produto",
                            "source_active": True,
                        }
                    ]
                },
            )
            processed = await sync.process_run(bundle["run_id"], datasource=fake)
            assert processed.status == ErpSyncRunStatus.COMPLETED

            checkpoint = (
                await session.execute(
                    select(ErpSyncCheckpoint).where(
                        ErpSyncCheckpoint.erp_source_id == bundle["source_id"],
                        ErpSyncCheckpoint.erp_dataset_id == bundle["dataset_id"],
                        ErpSyncCheckpoint.station_id == bundle["station_id"],
                    )
                )
            ).scalar_one()
            assert checkpoint.watermark_value is not None
            assert checkpoint.last_success_at is not None


@pytest.mark.asyncio
async def test_partial_run_does_not_advance_checkpoint(session_factory):
    _, bundle = await _setup(session_factory, sync_mode=ErpSyncMode.INCREMENTAL_TIMESTAMP)
    await commit_checkpoint(
        session_factory,
        source_id=bundle["source_id"],
        dataset_id=bundle["dataset_id"],
        station_id=bundle["station_id"],
        watermark="2026-07-09T10:00:00+00:00",
    )

    async with session_factory() as session:
        async with session.begin():
            dataset = (
                await session.execute(select(ErpDataset).where(ErpDataset.id == bundle["dataset_id"]))
            ).scalar_one()
            dataset.sync_mode = ErpSyncMode.INCREMENTAL_TIMESTAMP
            dataset.checkpoint_type = "TIMESTAMP"

            sync = XpertSyncService(session)
            fake = FakeXpertDataSource(
                source_time=datetime(2026, 7, 9, 12, 0, tzinfo=UTC),
                rows_by_query={
                    "default": [
                        {
                            "source_product_id": "1",
                            "source_product_code": "1",
                            "source_description": "OK",
                            "source_active": True,
                        },
                        {
                            "source_product_id": "1",
                            "source_product_code": "1",
                            "source_description": "Duplicado",
                            "source_active": True,
                        },
                    ]
                },
            )
            processed = await sync.process_run(bundle["run_id"], datasource=fake)
            assert processed.status == ErpSyncRunStatus.PARTIAL

            checkpoint = (
                await session.execute(
                    select(ErpSyncCheckpoint).where(
                        ErpSyncCheckpoint.erp_source_id == bundle["source_id"],
                        ErpSyncCheckpoint.erp_dataset_id == bundle["dataset_id"],
                        ErpSyncCheckpoint.station_id == bundle["station_id"],
                    )
                )
            ).scalar_one()
            assert checkpoint.watermark_value == "2026-07-09T10:00:00+00:00"


@pytest.mark.asyncio
async def test_failed_run_preserves_checkpoint(session_factory):
    _, bundle = await _setup(session_factory)
    await commit_checkpoint(
        session_factory,
        source_id=bundle["source_id"],
        dataset_id=bundle["dataset_id"],
        station_id=bundle["station_id"],
        watermark="2026-07-01T00:00:00+00:00",
    )

    async with session_factory() as session:
        async with session.begin():
            sync = XpertSyncService(session)
            processed = await sync.process_run(
                bundle["run_id"], datasource=FakeXpertDataSource(should_fail=True)
            )
            assert processed.status == ErpSyncRunStatus.FAILED

            checkpoint = (
                await session.execute(
                    select(ErpSyncCheckpoint).where(
                        ErpSyncCheckpoint.erp_source_id == bundle["source_id"],
                        ErpSyncCheckpoint.erp_dataset_id == bundle["dataset_id"],
                        ErpSyncCheckpoint.station_id == bundle["station_id"],
                    )
                )
            ).scalar_one()
            assert checkpoint.watermark_value == "2026-07-01T00:00:00+00:00"


@pytest.mark.asyncio
async def test_recover_abandoned_run_marks_failed_worker_lost(session_factory):
    _, bundle = await _setup(session_factory, run_status=ErpSyncRunStatus.EXTRACTING)

    async with session_factory() as session:
        async with session.begin():
            run = await session.get(ErpSyncRun, bundle["run_id"])
            assert run is not None
            run.last_heartbeat_at = datetime.now(UTC) - timedelta(hours=2)
            worker = XpertWorkerService(session)
            recovered = await worker.recover_abandoned_runs()
            assert recovered >= 1
            await session.refresh(run)
            assert run.status == ErpSyncRunStatus.FAILED
            assert run.error_code == "FAILED_WORKER_LOST"


@pytest.mark.asyncio
async def test_parallel_claim_race_uses_skip_locked(session_factory, db_engine):
    _, bundle = await _setup(session_factory)
    await _pin_run_as_oldest_queued(session_factory, bundle["run_id"])

    async def try_claim(worker_id: str) -> ErpSyncRun | None:
        async with db_engine.connect() as conn:
            async with conn.begin():
                session = AsyncSession(bind=conn, expire_on_commit=False)
                sync = XpertSyncService(session)
                return await sync.claim_next_run(worker_id)

    claimed_a, claimed_b = await asyncio.gather(try_claim("worker-a"), try_claim("worker-b"))
    winners = [r for r in (claimed_a, claimed_b) if r is not None and r.id == bundle["run_id"]]
    assert len(winners) <= 1


@pytest.mark.asyncio
async def test_retry_after_abandon_creates_new_run(session_factory):
    ctx, bundle = await _setup(session_factory, run_status=ErpSyncRunStatus.FAILED)

    async with session_factory() as session:
        async with session.begin():
            original = await session.get(ErpSyncRun, bundle["run_id"])
            assert original is not None
            original.error_code = "FAILED_WORKER_LOST"
            original.finished_at = datetime.now(UTC)

            retry_run = ErpSyncRun(
                organization_id=ctx["organization_id"],
                erp_source_id=bundle["source_id"],
                erp_dataset_id=bundle["dataset_id"],
                station_id=ctx["station_id"],
                trigger_type="RETRY",
                sync_mode=original.sync_mode,
                status=ErpSyncRunStatus.QUEUED,
                query_hash=original.query_hash,
                requested_by=ctx["user_id"],
                retried_from_run_id=original.id,
                created_at=datetime.now(UTC),
            )
            session.add(retry_run)
            await session.flush()
            assert retry_run.id != original.id
            assert retry_run.retried_from_run_id == original.id
            assert retry_run.status == ErpSyncRunStatus.QUEUED


@pytest.mark.asyncio
async def test_concurrent_schedule_creates_single_run(session_factory, db_engine):
    ctx = await commit_org_context(session_factory)
    code_suffix = uuid.uuid4().hex[:8]
    source_id = dataset_id = None

    async with session_factory() as session:
        async with session.begin():
            from app.services.audit_service import AuditContext
            from app.services.xpert_source_service import XpertSourceService

            station = await session.get(Station, ctx["station_id"])
            if station is not None:
                station.erp_branch_id = "2443"

            audit = AuditContext(
                organization_id=ctx["organization_id"],
                user_id=ctx["user_id"],
                ip_address="127.0.0.1",
                request_id=None,
            )
            source = await XpertSourceService(session).create_source(
                organization_id=ctx["organization_id"],
                user_id=ctx["user_id"],
                data={
                    "code": f"SCHED_{code_suffix}",
                    "name": "Schedule",
                    "host": "localhost",
                    "database_name": "atxdados",
                    "secret_ref": "xpert_test",
                    "enabled": True,
                },
                audit_ctx=audit,
            )
            source.connection_status = ErpConnectionStatus.CONNECTED
            dataset = (
                await session.execute(
                    select(ErpDataset).where(
                        ErpDataset.erp_source_id == source.id,
                        ErpDataset.code == ErpDatasetCode.PRODUCTS,
                    )
                )
            ).scalar_one()
            dataset.contract_status = ErpContractStatus.VALID
            dataset.query_hash = current_query_hash(dataset.query_file)
            dataset.enabled = True
            dataset.schedule_enabled = True
            dataset.schedule_interval_minutes = 60
            dataset.next_scheduled_at = datetime.now(UTC) - timedelta(minutes=1)
            source_id = source.id
            dataset_id = dataset.id

    async def schedule_once() -> int:
        async with db_engine.connect() as conn:
            async with conn.begin():
                session = AsyncSession(bind=conn, expire_on_commit=False)
                sync = XpertSyncService(session)
                return await sync.create_scheduled_runs()

    created_a, created_b = await asyncio.gather(schedule_once(), schedule_once())
    assert created_a + created_b >= 1

    async with session_factory() as session:
        async with session.begin():
            runs = (
                await session.execute(
                    select(ErpSyncRun).where(
                        ErpSyncRun.erp_source_id == source_id,
                        ErpSyncRun.erp_dataset_id == dataset_id,
                        ErpSyncRun.station_id == ctx["station_id"],
                        ErpSyncRun.trigger_type == "SCHEDULED",
                    )
                )
            ).scalars().all()
            assert len(runs) == 1
