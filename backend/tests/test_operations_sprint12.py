"""Testes sintéticos Sprint 12 — alertas, dashboard, readiness, correlation."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.middleware.request_id import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
from app.core.operations_enums import AlertCode, AlertStatus
from app.main import app
from app.services.alert_engine_service import AlertEngineService, evaluate_condition
from app.services.executive_metrics_service import ExecutiveMetricsService
from app.services.operations_service import OperationsService
from factories import create_organization, create_station, create_user


def test_evaluate_condition_operators():
    assert evaluate_condition("LT", Decimal("0.1"), Decimal("0.2")) is True
    assert evaluate_condition("GT", Decimal("0.3"), Decimal("0.2")) is True
    assert evaluate_condition("MISSING", None, None) is True
    assert evaluate_condition("MISSING", Decimal("1"), None) is False
    assert evaluate_condition("STALE", None, None, status_value="STALE") is True


@pytest.mark.asyncio
async def test_alert_deduplication_and_unsafe_not_resolvable(db_session):
    org = await create_organization(db_session, cnpj="77888999000101")
    svc = AlertEngineService(db_session)
    a1 = await svc.upsert_alert(
        organization_id=org.id,
        alert_code=AlertCode.SYNC_FAILED,
        title="Sync falhou",
        summary="Run FAILED",
        severity="HIGH",
        source_module="xpert",
        source_entity_type="erp_sync_run",
        source_entity_id=uuid4(),
    )
    a2 = await svc.upsert_alert(
        organization_id=org.id,
        alert_code=AlertCode.SYNC_FAILED,
        title="Sync falhou",
        summary="Run FAILED novamente",
        severity="HIGH",
        source_module="xpert",
        source_entity_type="erp_sync_run",
        source_entity_id=a1.source_entity_id,
    )
    assert a1.id == a2.id
    assert a2.occurrence_count == 2

    unsafe = await svc.ensure_unsafe_xpert_alert(org.id)
    assert unsafe.dismissible is False
    with pytest.raises(Exception):
        await svc.resolve_alert(
            unsafe.id, org.id, user_id=None, resolution_code="ACCEPTED_RISK", note="nope"
        )


@pytest.mark.asyncio
async def test_alert_lifecycle(db_session):
    org = await create_organization(db_session, cnpj="77888999000102")
    user = await create_user(
        db_session,
        organization_id=org.id,
        email=f"ops-{uuid4().hex[:8]}@test.com",
        role_codes=["ADMIN"],
        has_all_stations_access=True,
    )
    svc = AlertEngineService(db_session)
    alert = await svc.upsert_alert(
        organization_id=org.id,
        alert_code=AlertCode.MISSING_MAPPING,
        title="Sem mapeamento",
        summary="Produto ERP sem canônico",
        severity="WARNING",
    )
    alert = await svc.acknowledge(alert.id, org.id, user.id)
    assert alert.status == AlertStatus.ACKNOWLEDGED
    alert = await svc.assign(alert.id, org.id, assigned_user_id=user.id, user_id=user.id)
    assert alert.status == AlertStatus.ASSIGNED
    alert = await svc.snooze(alert.id, org.id, minutes=30, user_id=user.id)
    assert alert.status == AlertStatus.SNOOZED
    alert = await svc.resolve_alert(alert.id, org.id, user_id=user.id, resolution_code="FIXED")
    assert alert.status == AlertStatus.RESOLVED
    alert = await svc.reopen(alert.id, org.id, user.id)
    assert alert.status == AlertStatus.OPEN


@pytest.mark.asyncio
async def test_executive_synthetic_no_zero_for_missing(db_session):
    org = await create_organization(db_session, cnpj="77888999000103")
    stations = []
    for i in range(4):
        stations.append(
            await create_station(
                db_session,
                organization_id=org.id,
                trade_name=f"Posto Exec {i}",
                cnpj=f"77888999000{i+10}",
            )
        )
    svc = ExecutiveMetricsService(db_session)
    data = await svc.build_synthetic_dashboard(org.id, [s.id for s in stations])
    purchase = next(c for c in data["cards"] if c["metric_code"] == "PURCHASE_VOLUME_LITERS")
    assert purchase["value"] is None
    assert purchase["empty_reason"] == "NOT_SYNCED"
    assert purchase["value"] != "0"
    assert len(data["by_station"]) == 4
    assert data["synthetic"] is True


@pytest.mark.asyncio
async def test_readiness_not_ready_while_unsafe(db_session):
    org = await create_organization(db_session, cnpj="77888999000104")
    # seed unsafe alert path + readiness
    await AlertEngineService(db_session).ensure_unsafe_xpert_alert(org.id)
    ops = OperationsService(db_session)
    readiness = await ops.readiness(org.id)
    # Without ErpSource UNSAFE in DB, xpert may be UNKNOWN — still scheduler blocked
    assert readiness["scheduler_blocked"] is True
    assert readiness["production_with_sa_blocked"] is True
    assert readiness["xpert_write_enabled"] is False


@pytest.mark.asyncio
async def test_feature_flags_defaults(db_session):
    org = await create_organization(db_session, cnpj="77888999000105")
    ops = OperationsService(db_session)
    flags = await ops.get_or_seed_flags(org.id)
    codes = {f.flag_code for f in flags}
    assert "executive_dashboard_enabled" in codes
    assert "email_notifications_enabled" in codes
    email = next(f for f in flags if f.flag_code == "email_notifications_enabled")
    assert email.enabled is False


@pytest.mark.asyncio
async def test_outbox_process(db_session):
    org = await create_organization(db_session, cnpj="77888999000106")
    svc = AlertEngineService(db_session)
    await svc.upsert_alert(
        organization_id=org.id,
        alert_code=AlertCode.STALE_DATASET,
        title="Dataset stale",
        summary="Freshness STALE",
        severity="WARNING",
    )
    ops = OperationsService(db_session)
    result = await ops.process_outbox_batch()
    assert result["processed"] >= 1


@pytest.mark.asyncio
async def test_rule_evaluation(db_session):
    org = await create_organization(db_session, cnpj="77888999000107")
    svc = AlertEngineService(db_session)
    rule = await svc.create_rule(
        organization_id=org.id,
        user_id=None,
        data={
            "code": "MARGIN_BELOW_FLOOR",
            "name": "Margem abaixo do piso",
            "metric_code": "margin_per_liter",
            "operator": "LT",
            "threshold_value": "0.20",
            "severity": "HIGH",
            "alert_type": "FINANCIAL",
        },
    )
    alert = await svc.evaluate_rule(rule=rule, observed_value=Decimal("0.10"))
    assert alert is not None
    none_alert = await svc.evaluate_rule(rule=rule, observed_value=Decimal("0.50"))
    # auto-resolve may clear previous
    assert none_alert is None


@pytest.mark.asyncio
async def test_correlation_id_header():
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health/live", headers={CORRELATION_ID_HEADER: "corr-test-123"})
        assert resp.status_code == 200
        assert resp.headers.get(CORRELATION_ID_HEADER) == "corr-test-123"
        assert resp.headers.get(REQUEST_ID_HEADER)


@pytest.mark.asyncio
async def test_multi_tenant_alerts_isolated(db_session):
    org_a = await create_organization(db_session, cnpj="77888999000108")
    org_b = await create_organization(db_session, cnpj="77888999000109")
    svc = AlertEngineService(db_session)
    await svc.upsert_alert(
        organization_id=org_a.id,
        alert_code=AlertCode.COVERAGE_DROP,
        title="Cobertura A",
        summary="Org A",
        severity="HIGH",
    )
    alerts_b = await svc.list_alerts(org_b.id)
    assert all(a.organization_id == org_b.id for a in alerts_b)
    assert not any(a.title == "Cobertura A" for a in alerts_b)
