"""Helpers para testes de integração XPERT com commits reais."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.xpert_sync_enums import (
    ErpConnectionStatus,
    ErpContractStatus,
    ErpDatasetCode,
    ErpSyncMode,
    ErpSyncRunStatus,
)
from app.integrations.xpert.query_guard import current_query_hash
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncCheckpoint, ErpSyncRun
from app.models.station import Station
from app.services.audit_service import AuditContext
from app.services.xpert_source_service import XpertSourceService


async def commit_org_context(
    session_factory: async_sessionmaker[AsyncSession],
) -> dict[str, uuid.UUID]:
    from factories import create_organization, create_station, create_user

    suffix = uuid.uuid4().hex[:8]
    org_cnpj = f"11222333{suffix[:4]}01"
    station_cnpj = f"11222333{suffix[:4]}02"
    async with session_factory() as session:
        async with session.begin():
            org = await create_organization(session, cnpj=org_cnpj)
            user = await create_user(
                session,
                organization_id=org.id,
                email=f"xpert-{suffix}@test.com",
                role_codes=["ADMIN"],
                has_all_stations_access=True,
            )
            station = await create_station(
                session,
                organization_id=org.id,
                trade_name=f"Filial {suffix}",
                cnpj=station_cnpj,
            )
            await session.flush()
            return {
                "organization_id": org.id,
                "user_id": user.id,
                "station_id": station.id,
            }


async def commit_xpert_bundle(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    station_id: uuid.UUID,
    erp_branch_id: str = "2443",
    dataset_code: ErpDatasetCode = ErpDatasetCode.PRODUCTS,
    run_status: ErpSyncRunStatus = ErpSyncRunStatus.QUEUED,
    sync_mode: ErpSyncMode = ErpSyncMode.FULL_SNAPSHOT_HASH,
    source_code: str | None = None,
) -> dict[str, uuid.UUID]:
    code_suffix = uuid.uuid4().hex[:8]
    async with session_factory() as session:
        async with session.begin():
            station = await session.get(Station, station_id)
            if station is not None:
                station.erp_branch_id = erp_branch_id

            ctx = AuditContext(
                organization_id=organization_id,
                user_id=user_id,
                ip_address="127.0.0.1",
                request_id=None,
            )
            source = await XpertSourceService(session).create_source(
                organization_id=organization_id,
                user_id=user_id,
                data={
                    "code": source_code or f"XPERT_{code_suffix}",
                    "name": f"XPERT {code_suffix}",
                    "host": "localhost",
                    "database_name": "atxdados",
                    "secret_ref": "xpert_test",
                    "enabled": True,
                },
                audit_ctx=ctx,
            )
            source.connection_status = ErpConnectionStatus.CONNECTED

            result = await session.execute(
                select(ErpDataset).where(
                    ErpDataset.erp_source_id == source.id,
                    ErpDataset.code == dataset_code,
                )
            )
            dataset = result.scalar_one()
            dataset.contract_status = ErpContractStatus.VALID
            dataset.query_hash = current_query_hash(dataset.query_file)
            dataset.enabled = True
            dataset.sync_mode = sync_mode

            run = ErpSyncRun(
                organization_id=organization_id,
                erp_source_id=source.id,
                erp_dataset_id=dataset.id,
                station_id=station_id,
                trigger_type="MANUAL",
                sync_mode=sync_mode,
                status=run_status,
                query_hash=dataset.query_hash,
                created_at=datetime.now(UTC),
            )
            session.add(run)
            await session.flush()

            return {
                "source_id": source.id,
                "dataset_id": dataset.id,
                "run_id": run.id,
                "station_id": station_id,
                "organization_id": organization_id,
            }


async def commit_checkpoint(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    source_id: uuid.UUID,
    dataset_id: uuid.UUID,
    station_id: uuid.UUID | None,
    watermark: str | None = None,
) -> uuid.UUID:
    async with session_factory() as session:
        async with session.begin():
            checkpoint = ErpSyncCheckpoint(
                erp_source_id=source_id,
                erp_dataset_id=dataset_id,
                station_id=station_id,
                checkpoint_type="TIMESTAMP",
                watermark_value=watermark,
            )
            session.add(checkpoint)
            await session.flush()
            return checkpoint.id
