"""Testes de sync FUEL_SALES_ITEMS com datasource fake."""

from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.exceptions import AppError
from app.core.master_data_enums import MappingSource, MappingStatus
from app.core.xpert_sync_enums import ErpDatasetCode, ErpSyncRunStatus
from app.integrations.xpert.fake_datasource import FakeXpertDataSource
from app.integrations.xpert.query_guard import current_query_hash
from app.models.erp_integration import ErpDataset, ErpSource, ErpSyncRun
from app.models.erp_product import ErpProduct
from app.models.fuel_sales import FuelSalesFact
from app.services.audit_service import AuditContext
from app.services.xpert_source_service import XpertSourceService
from app.services.xpert_sync_service import XpertSyncService


async def _load_source_with_datasets(db_session, source_id) -> ErpSource:
    result = await db_session.execute(
        select(ErpSource).where(ErpSource.id == source_id).options(selectinload(ErpSource.datasets))
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_fuel_sales_incremental_requires_history_window(db_session, org, branch_station, admin_user):
    service = XpertSourceService(db_session)
    ctx = AuditContext(organization_id=org.id, user_id=admin_user.id, ip_address="127.0.0.1", request_id=None)
    source = await service.create_source(
        organization_id=org.id,
        user_id=admin_user.id,
        data={
            "code": "XPERT_FUEL",
            "name": "Fuel",
            "host": "localhost",
            "database_name": "atxdados",
            "secret_ref": "xpert_test",
        },
        audit_ctx=ctx,
    )
    branch_station.erp_branch_id = "2443"
    await db_session.flush()

    result = await db_session.execute(
        select(ErpDataset).where(
            ErpDataset.erp_source_id == source.id,
            ErpDataset.code == ErpDatasetCode.FUEL_SALES_ITEMS,
        )
    )
    dataset = result.scalar_one()
    dataset.contract_status = "VALID"
    dataset.query_hash = current_query_hash(dataset.query_file)
    dataset.enabled = True
    source.connection_status = "CONNECTED"
    await db_session.flush()
    source = await _load_source_with_datasets(db_session, source.id)

    with pytest.raises(AppError) as exc:
        await service.enqueue_sync_runs(
            organization_id=org.id,
            source=source,
            dataset_codes=[ErpDatasetCode.FUEL_SALES_ITEMS],
            station_ids=[branch_station.id],
            sync_mode="INCREMENTAL_TIMESTAMP",
            trigger_type="MANUAL",
            requested_by=admin_user.id,
        )
    assert exc.value.code == "FUEL_SALES_HISTORY_WINDOW_REQUIRED"


@pytest.mark.asyncio
async def test_fuel_sales_sync_applies_fact_with_fake_datasource(db_session, org, branch_station, admin_user):
    service = XpertSourceService(db_session)
    ctx = AuditContext(organization_id=org.id, user_id=admin_user.id, ip_address="127.0.0.1", request_id=None)
    source = await service.create_source(
        organization_id=org.id,
        user_id=admin_user.id,
        data={
            "code": "XPERT_FUEL_SYNC",
            "name": "Fuel Sync",
            "host": "localhost",
            "database_name": "atxdados",
            "secret_ref": "xpert_test",
        },
        audit_ctx=ctx,
    )
    source = await _load_source_with_datasets(db_session, source.id)
    branch_station.erp_branch_id = "2443"
    product = ErpProduct(
        organization_id=org.id,
        station_id=branch_station.id,
        erp_product_id="501",
        erp_description="Gasolina Comum",
        mapping_status=MappingStatus.PENDING,
        mapping_source=MappingSource.ERP_SYNC,
        raw_payload={},
        last_synced_at=datetime.now(UTC),
        active=True,
        source_system="XPERT",
    )
    db_session.add(product)
    await db_session.flush()

    result = await db_session.execute(
        select(ErpDataset).where(
            ErpDataset.erp_source_id == source.id,
            ErpDataset.code == ErpDatasetCode.FUEL_SALES_ITEMS,
        )
    )
    dataset = result.scalar_one()
    dataset.contract_status = "VALID"
    dataset.query_hash = current_query_hash(dataset.query_file)
    dataset.enabled = True
    source.connection_status = "CONNECTED"
    await db_session.flush()
    source = await _load_source_with_datasets(db_session, source.id)

    history_end = date.today()
    history_start = history_end - timedelta(days=30)
    runs = await service.enqueue_sync_runs(
        organization_id=org.id,
        source=source,
        dataset_codes=[ErpDatasetCode.FUEL_SALES_ITEMS],
        station_ids=[branch_station.id],
        sync_mode="INCREMENTAL_TIMESTAMP",
        trigger_type="MANUAL",
        requested_by=admin_user.id,
        history_start_date=history_start,
        history_end_date=history_end,
    )
    run = runs[0]
    assert run.window_start == datetime.combine(history_start, time.min, tzinfo=UTC)
    await db_session.flush()

    sale_row = {
        "source_sale_id": "9001",
        "source_sale_item_id": "9001-1",
        "source_branch_id": "2443",
        "source_sale_datetime": datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        "source_business_date": date(2026, 6, 15),
        "source_product_id": "501",
        "source_quantity": "100.000000",
        "source_net_amount": "599.9000",
        "source_updated_at": datetime(2026, 6, 15, 10, 0, tzinfo=UTC),
        "source_cancelled": False,
        "source_document_number": "12345",
        "source_unit": None,
        "source_unit_price": "5.99900000",
        "source_gross_amount": "599.9000",
        "source_discount_amount": "0.0000",
        "source_surcharge_amount": None,
        "source_cost_per_unit": "4.50000000",
        "source_total_cost": "450.0000",
        "source_payment_method_id": "0",
        "source_operation_type": "SALE",
    }
    fake = FakeXpertDataSource(rows_by_query={"ITENSMOVPRODUTOS": [sale_row]})
    sync = XpertSyncService(db_session)
    finished = await sync.process_run(run.id, datasource=fake)
    assert finished.status == ErpSyncRunStatus.COMPLETED
    assert finished.rows_applied == 1

    facts = await db_session.execute(select(FuelSalesFact).where(FuelSalesFact.station_id == branch_station.id))
    items = list(facts.scalars().all())
    assert len(items) == 1
    assert float(items[0].net_amount) == pytest.approx(599.9)
    assert float(items[0].volume_liters) == pytest.approx(100)
