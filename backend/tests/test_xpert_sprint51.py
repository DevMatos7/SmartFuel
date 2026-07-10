"""Testes Sprint 5.1 — estabilização XPERT."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.core.xpert_sync_enums import ErpContractStatus, ErpDatasetCode, ErpSyncMode, ErpSyncRunStatus
from app.integrations.xpert.query_guard import QueryChangedError, current_query_hash, ensure_dataset_query_unchanged
from app.integrations.xpert.query_validator import validate_read_only_query
from app.models.erp_integration import ErpDataset, ErpSyncCheckpoint
from app.services.xpert_checkpoint_service import XpertCheckpointService


def test_validator_blocks_select_into():
    result = validate_read_only_query("SELECT * INTO tmp FROM produtos")
    assert result.valid is False
    assert any("INTO" in e or "Insert" in e or "proibido" in e for e in result.errors)


def test_validator_blocks_with_delete():
    result = validate_read_only_query("WITH cte AS (SELECT 1 AS x) DELETE FROM t")
    assert result.valid is False


def test_validator_allows_cte_select():
    result = validate_read_only_query(
        "WITH cte AS (SELECT 1 AS source_product_id, 'x' AS source_description) SELECT * FROM cte"
    )
    assert result.valid is True


def test_query_hash_change_invalidates_dataset():
    dataset = ErpDataset(
        erp_source_id=__import__("uuid").uuid4(),
        code=ErpDatasetCode.PRODUCTS,
        name="Produtos",
        query_file="products.sql",
        query_hash="stale-hash",
        sync_mode=ErpSyncMode.FULL_SNAPSHOT_HASH,
        checkpoint_type="NONE",
        overlap_seconds=300,
        batch_size=1000,
        contract_status=ErpContractStatus.VALID,
        enabled=True,
        schedule_enabled=True,
    )
    with pytest.raises(QueryChangedError):
        ensure_dataset_query_unchanged(dataset)
    assert dataset.contract_status == ErpContractStatus.PENDING_VALIDATION
    assert dataset.schedule_enabled is False
    assert dataset.enabled is False


def test_json_safe_serializes_datetime():
    from datetime import UTC, datetime

    from app.integrations.xpert.normalizers import json_safe

    dt = datetime(2018, 1, 19, tzinfo=UTC)
    payload = json_safe({"source_updated_at": dt})
    assert payload["source_updated_at"] == dt.isoformat()


def test_prepare_sql_ignores_parameters_in_comments():
    from app.integrations.xpert.direct_sqlserver import _prepare_sql

    sql = "-- Parameters: @station_erp_id\nSELECT 1 WHERE x = @station_erp_id"
    prepared, values = _prepare_sql(sql, {"station_erp_id": 2443})
    assert prepared.count("?") == 1
    assert values == [2443]


def test_checkpoint_window_uses_source_upper_bound():
    service = XpertCheckpointService(db=None)  # type: ignore[arg-type]
    dataset = ErpDataset(
        erp_source_id=__import__("uuid").uuid4(),
        code=ErpDatasetCode.PRODUCTS,
        name="Produtos",
        query_file="products.sql",
        sync_mode=ErpSyncMode.INCREMENTAL_TIMESTAMP,
        checkpoint_type="TIMESTAMP",
        overlap_seconds=300,
        batch_size=1000,
        contract_status=ErpContractStatus.VALID,
        enabled=True,
    )
    checkpoint = ErpSyncCheckpoint(
        erp_source_id=dataset.erp_source_id,
        erp_dataset_id=__import__("uuid").uuid4(),
        station_id=__import__("uuid").uuid4(),
        checkpoint_type="TIMESTAMP",
        watermark_value="2026-07-09T10:00:00+00:00",
    )
    upper = datetime(2026, 7, 9, 12, 0, tzinfo=UTC)
    start, end = service.compute_window(dataset=dataset, checkpoint=checkpoint, source_upper_bound=upper)
    assert end == upper
    assert start == datetime(2026, 7, 9, 9, 55, tzinfo=UTC)


def test_checkpoint_should_not_advance_on_partial():
    service = XpertCheckpointService(db=None)  # type: ignore[arg-type]
    dataset = ErpDataset(
        erp_source_id=__import__("uuid").uuid4(),
        code=ErpDatasetCode.PRODUCTS,
        name="Produtos",
        query_file="products.sql",
        sync_mode=ErpSyncMode.FULL_SNAPSHOT_HASH,
        checkpoint_type="NONE",
        overlap_seconds=300,
        batch_size=1000,
        allow_partial_checkpoint=False,
        contract_status=ErpContractStatus.VALID,
        enabled=True,
    )
    from app.models.erp_integration import ErpSyncRun

    run = ErpSyncRun(
        organization_id=__import__("uuid").uuid4(),
        erp_source_id=dataset.erp_source_id,
        erp_dataset_id=__import__("uuid").uuid4(),
        trigger_type="MANUAL",
        sync_mode=ErpSyncMode.FULL_SNAPSHOT_HASH,
        status=ErpSyncRunStatus.PARTIAL,
        rows_quarantined=1,
        created_at=datetime.now(UTC),
    )
    assert service.should_advance(run, dataset) is False


def test_products_query_hash_stable():
    h1 = current_query_hash("products.sql")
    h2 = current_query_hash("products.sql")
    assert h1 == h2
    assert len(h1) == 64


def test_stations_query_is_misconfigured_placeholder():
    result = validate_read_only_query(
        "SELECT CAST(NULL AS VARCHAR(100)) AS source_branch_id WHERE 1 = 0"
    )
    assert result.valid is True
