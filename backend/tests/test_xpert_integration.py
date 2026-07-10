"""Testes Sprint 5 — integração XPERT."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.core.master_data_enums import MappingSource, MappingStatus
from app.core.xpert_sync_enums import ErpDatasetCode, ErpStagingStatus, ErpSyncRunStatus
from app.integrations.xpert.fake_datasource import FakeXpertDataSource
from app.integrations.xpert.query_validator import validate_parameters, validate_read_only_query
from app.integrations.xpert.canonical_hash import canonical_record_hash
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.services.xpert_apply_service import XpertApplyService
from app.services.xpert_source_service import XpertSourceService
from app.services.xpert_sync_service import XpertSyncService


def test_validate_select_query_ok():
    result = validate_read_only_query("SELECT 1 AS source_product_id, 'x' AS source_description")
    assert result.valid is True


def test_validate_update_query_blocked():
    result = validate_read_only_query("UPDATE PRODUTOS SET NOMEPRODUTO = 'x'")
    assert result.valid is False
    assert any("UPDATE" in e or "Somente SELECT" in e for e in result.errors)


def test_validate_exec_blocked():
    result = validate_read_only_query("EXEC sp_help")
    assert result.valid is False


def test_validate_parameters_allowed():
    sql = "SELECT * FROM t WHERE id = @station_erp_id AND dt >= @window_start"
    assert validate_parameters(sql) == []


def test_validate_parameters_unknown():
    sql = "SELECT * FROM t WHERE id = @evil_param"
    errors = validate_parameters(sql)
    assert errors
    assert "evil_param" in errors[0]


def test_canonical_hash_stable():
    payload = {"erp_product_id": "1", "erp_description": "Gasolina", "source_active": True}
    h1 = canonical_record_hash(payload)
    h2 = canonical_record_hash({"source_active": True, "erp_description": "Gasolina", "erp_product_id": "1"})
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_create_source_bootstraps_datasets(db_session, org, admin_user):
    from app.services.audit_service import AuditContext

    service = XpertSourceService(db_session)
    ctx = AuditContext(organization_id=org.id, user_id=admin_user.id, ip_address="127.0.0.1", request_id=None)
    source = await service.create_source(
        organization_id=org.id,
        user_id=admin_user.id,
        data={
            "code": "XPERT_TEST",
            "name": "XPERT Test",
            "host": "localhost",
            "port": 1433,
            "database_name": "atxdados",
            "secret_ref": "xpert_test",
        },
        audit_ctx=ctx,
    )
    result = await db_session.execute(select(ErpDataset).where(ErpDataset.erp_source_id == source.id))
    datasets = list(result.scalars().all())
    codes = {d.code for d in datasets}
    assert ErpDatasetCode.PRODUCTS in codes
    assert ErpDatasetCode.SUPPLIERS in codes
    assert ErpDatasetCode.STATIONS in codes


@pytest.mark.asyncio
async def test_test_connection_fake(db_session, org, admin_user):
    from app.services.audit_service import AuditContext

    service = XpertSourceService(db_session)
    ctx = AuditContext(organization_id=org.id, user_id=admin_user.id, ip_address="127.0.0.1", request_id=None)
    source = await service.create_source(
        organization_id=org.id,
        user_id=admin_user.id,
        data={
            "code": "XPERT_CONN",
            "name": "XPERT Conn",
            "host": "localhost",
            "database_name": "atxdados",
            "secret_ref": "xpert_test",
        },
        audit_ctx=ctx,
    )
    fake = FakeXpertDataSource()
    result = await service.test_connection(source=source, audit_ctx=ctx, datasource=fake)
    assert result["status"] == "CONNECTED"
    assert result["privileges"]["sysadmin"] is False


@pytest.mark.asyncio
async def test_sync_products_with_fake_datasource(db_session, org, branch_station, admin_user):
    from app.services.audit_service import AuditContext

    source_service = XpertSourceService(db_session)
    ctx = AuditContext(organization_id=org.id, user_id=admin_user.id, ip_address="127.0.0.1", request_id=None)
    source = await source_service.create_source(
        organization_id=org.id,
        user_id=admin_user.id,
        data={
            "code": "XPERT_SYNC",
            "name": "Sync",
            "host": "localhost",
            "database_name": "atxdados",
            "secret_ref": "xpert_test",
        },
        audit_ctx=ctx,
    )
    branch_station.erp_branch_id = "1"
    await db_session.flush()

    result = await db_session.execute(
        select(ErpDataset).where(ErpDataset.erp_source_id == source.id, ErpDataset.code == ErpDatasetCode.PRODUCTS)
    )
    dataset = result.scalar_one()
    from app.integrations.xpert.query_guard import current_query_hash

    dataset.contract_status = "VALID"
    dataset.query_hash = current_query_hash(dataset.query_file)
    dataset.enabled = True

    run = ErpSyncRun(
        organization_id=org.id,
        erp_source_id=source.id,
        erp_dataset_id=dataset.id,
        station_id=branch_station.id,
        trigger_type="MANUAL",
        sync_mode="FULL_SNAPSHOT_HASH",
        status=ErpSyncRunStatus.QUEUED,
        created_at=datetime.now(UTC),
    )
    db_session.add(run)
    await db_session.flush()

    fake = FakeXpertDataSource(
        rows_by_query={
            "default": [
                {
                    "source_product_id": "100",
                    "source_product_code": "100",
                    "source_description": "Gasolina Comum",
                    "source_active": True,
                }
            ]
        }
    )
    sync = XpertSyncService(db_session)
    processed = await sync.process_run(run.id, datasource=fake)
    assert processed.status in (ErpSyncRunStatus.COMPLETED, ErpSyncRunStatus.PARTIAL)
    assert processed.rows_read >= 1

    product_result = await db_session.execute(
        select(ErpProduct).where(ErpProduct.station_id == branch_station.id, ErpProduct.erp_product_id == "100")
    )
    product = product_result.scalar_one_or_none()
    assert product is not None
    assert product.mapping_status == MappingStatus.PENDING
    assert product.mapping_source == MappingSource.ERP_SYNC


@pytest.mark.asyncio
async def test_apply_idempotent_unchanged(db_session, org, branch_station, admin_user):
    from app.services.audit_service import AuditContext
    from app.models.erp_integration import ErpStagingRecord

    source_service = XpertSourceService(db_session)
    ctx = AuditContext(organization_id=org.id, user_id=admin_user.id, ip_address="127.0.0.1", request_id=None)
    source = await source_service.create_source(
        organization_id=org.id,
        user_id=admin_user.id,
        data={
            "code": "XPERT_APPLY",
            "name": "Apply",
            "host": "localhost",
            "database_name": "atxdados",
            "secret_ref": "xpert_test",
        },
        audit_ctx=ctx,
    )
    result = await db_session.execute(
        select(ErpDataset).where(ErpDataset.erp_source_id == source.id, ErpDataset.code == ErpDatasetCode.PRODUCTS)
    )
    dataset = result.scalar_one()

    apply = XpertApplyService(db_session)
    now = datetime.now(UTC)
    run = ErpSyncRun(
        organization_id=org.id,
        erp_source_id=source.id,
        erp_dataset_id=dataset.id,
        station_id=branch_station.id,
        trigger_type="MANUAL",
        sync_mode="FULL_SNAPSHOT_HASH",
        status=ErpSyncRunStatus.APPLYING,
        created_at=now,
    )
    normalized = {
        "erp_product_id": "200",
        "erp_description": "Diesel",
        "source_active": True,
    }
    from app.integrations.xpert.normalizers import hash_payload_for_dataset

    record_hash = canonical_record_hash(hash_payload_for_dataset(ErpDatasetCode.PRODUCTS, normalized))
    db_session.add(
        ErpProduct(
            organization_id=org.id,
            station_id=branch_station.id,
            erp_product_id="200",
            erp_description="Diesel",
            mapping_status=MappingStatus.PENDING,
            mapping_source=MappingSource.ERP_SYNC,
            source_system="XPERT",
            source_record_hash=record_hash,
            source_active=True,
        )
    )
    db_session.add(run)
    await db_session.flush()
    staging = ErpStagingRecord(
        sync_run_id=run.id,
        organization_id=org.id,
        station_id=branch_station.id,
        dataset_code=ErpDatasetCode.PRODUCTS,
        source_key="200",
        raw_payload=normalized,
        normalized_payload=normalized,
        record_hash=record_hash,
        processing_status=ErpStagingStatus.VALIDATED,
        created_at=now,
    )
    db_session.add(staging)
    await db_session.flush()
    outcome = await apply.apply_staging_record(run=run, staging=staging, now=now)
    assert outcome == "unchanged"
    assert staging.processing_status == ErpStagingStatus.SKIPPED_UNCHANGED
